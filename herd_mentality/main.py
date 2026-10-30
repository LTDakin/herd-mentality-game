import json
import os
import random
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Form, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from herd_mentality.auth import (
    current_player,
    is_wrangler,
    logged_in_player,
    login_response,
    register_player,
)
from herd_mentality.scoring import group_answers
from herd_mentality.questions import pick_question
from herd_mentality.rounds import (
    ROUND_SECONDS,
    round_deadline,
    round_is_over,
    round_is_running,
    seconds_left,
)
from herd_mentality.state import Game_State

QUESTIONS_PATH = Path(__file__).parent / "static" / "herd_questions.json"


def load_questions(path: Path = QUESTIONS_PATH) -> list[str]:
    """Read the prompt pool.

    Called per round rather than cached at import, so the file can be edited
    and the server reloaded without a code change.
    """
    return json.loads(path.read_text(encoding="utf-8"))["questions"]


COW_FACTS = json.loads(
    (Path(__file__).parent / "static" / "cow_facts.json").read_text(encoding="utf-8")
)["facts"]

app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static",
)


def start_round() -> None:
    """Give the current round its prompt.

    Called when a round begins, never while rendering, so every player sees
    the same prompt instead of one being drawn per page load.
    """
    Game_State["question"], Game_State["questions_left"] = pick_question(
        Game_State["questions_left"], load_questions(), Game_State["question"]
    )


def current_page(player_name: str | None) -> str:
    """The page a player should be looking at right now.

    Mirrors the redirects the routes already make, so a lost or mistyped URL
    drops the player back where they were instead of onto an error page.
    """
    if player_name is None:
        return "/"
    # The scoreboard covers everyone still in the game once the clock stops.
    if round_is_over(Game_State["round_ends_at"]):
        return "/game/scoreboard"
    if player_name in Game_State["answers"]:
        return "/game/answered"
    return "/game"


def answered_players_page() -> str:
    """Where a player who has already answered belongs right now."""
    if round_is_over(Game_State["round_ends_at"]):
        return "/game/scoreboard"
    return "/game/answered"


def current_seconds_left() -> int:
    """Seconds remaining in the round, for the pages and the status endpoint."""
    return seconds_left(Game_State["round_ends_at"])


def answers_are_open() -> bool:
    """True while an answer submitted right now would be recorded."""
    return round_is_running(Game_State["round_ends_at"])



@app.exception_handler(StarletteHTTPException)
async def unknown_route(request: Request, exc: StarletteHTTPException):
    """Send lost players to the page that matches the current game state."""
    # 404 for a missing URL, 405 for the wrong method (e.g. GETting a form
    # endpoint after a resubmitted page). Both mean "this isn't a real page".
    # `/static` is left alone: a missing asset should fail for the browser
    # rather than quietly redirect into a page of HTML.
    if exc.status_code in (404, 405) and not request.url.path.startswith("/static/"):
        return RedirectResponse(current_page(logged_in_player(request)), status_code=303)
    return await http_exception_handler(request, exc)


@app.get("/")
async def root(request: Request):
    player_name = logged_in_player(request)
    if player_name is not None:
        if player_name in Game_State["answers"]:
            return RedirectResponse(answered_players_page(), status_code=303)
        return RedirectResponse(current_page(player_name), status_code=303)
    # Only offer the wrangler checkbox while the role is unclaimed.
    return templates.TemplateResponse(
        request, "login.html", {"wrangler_taken": Game_State["wrangler"] is not None}
    )


@app.post("/login")
async def login(
    request: Request, player_name: str = Form(...), wrangler: bool = Form(False)
):
    status_code, error = register_player(player_name, wants_wrangler=wrangler)
    if error is not None:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "error": error,
                "wrangler_taken": Game_State["wrangler"] is not None,
            },
            status_code=status_code,
        )
    # The first player in picks the opening prompt, so everyone sees the same
    # question before the wrangler starts the clock.
    if Game_State["question"] is None:
        start_round()
    return login_response(player_name.strip())


@app.get("/game")
async def game(request: Request, player_name: str = Depends(current_player)):
    # Once the clock has run out the answers are public.
    if round_is_over(Game_State["round_ends_at"]):
        return RedirectResponse("/game/scoreboard", status_code=303)
    # A player who already answered and reloads this page keeps waiting on the
    # answered page rather than seeing the question again.
    if player_name in Game_State["answers"]:
        return RedirectResponse("/game/answered", status_code=303)
    # Safety net for a round that was never started.
    if Game_State["question"] is None:
        start_round()
    return templates.TemplateResponse(
        request,
        "game.html",
        {
            "player_name": player_name,
            "question": Game_State["question"],
            "is_wrangler": is_wrangler(player_name),
            "round_started": round_is_running(Game_State["round_ends_at"]),
            "seconds_left": current_seconds_left(),
            "round": Game_State["round"],
        },
    )


@app.post("/game/answer")
async def game_answer(
    player_name: str = Depends(current_player), answer: str = Form(...)
):
    # No round running (never started, or already over), so there is nothing
    # to answer yet.
    if Game_State["round_ends_at"] is None:
        return RedirectResponse(current_page(player_name), status_code=303)

    # The clock beat the player to it: answer too late to count.
    if round_is_over(Game_State["round_ends_at"]):
        return RedirectResponse("/game/scoreboard", status_code=303)

    answer = answer.strip()
    if not answer:
        return RedirectResponse("/game", status_code=303)

    if player_name in Game_State["answers"]:
        return RedirectResponse(answered_players_page(), status_code=303)

    Game_State["answers"][player_name] = answer
    return RedirectResponse("/game/answered", status_code=303)


@app.get("/game/answered")
async def answered(request: Request, player_name: str = Depends(current_player)):
    curr_player_answer = Game_State["answers"].get(player_name)
    if curr_player_answer is None:
        return RedirectResponse("/game", status_code=303)
    # Once the clock stops, the answers are public.
    if round_is_over(Game_State["round_ends_at"]):
        return RedirectResponse("/game/scoreboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "answered.html",
        {
            "player_name": player_name,
            "answer": curr_player_answer,
            "round": Game_State["round"],
            "seconds_left": current_seconds_left(),
            "round_started": round_is_running(Game_State["round_ends_at"]),
            "cow_fact": random.choice(COW_FACTS),
        },
    )


@app.post("/game/start")
async def start(player_name: str = Depends(current_player)):
    """Wrangler only: start (or restart) the round's answer clock."""
    if not is_wrangler(player_name):
        return RedirectResponse("/game", status_code=303)

    Game_State["round_ends_at"] = round_deadline()
    return RedirectResponse("/game", status_code=303)


@app.get("/game/status")
async def game_status(player_name: str = Depends(current_player)):
    """Polled by the game, answered and scoreboard pages to track the round."""
    return {
        "revealed": round_is_over(Game_State["round_ends_at"]),
        "round": Game_State["round"],
        "seconds_left": current_seconds_left(),
    }


@app.post("/game/next-round")
async def next_round(player_name: str = Depends(current_player)):
    """Wrangler only: clear the round's answers and start the next one."""
    if not is_wrangler(player_name):
        return RedirectResponse("/game/scoreboard", status_code=303)

    Game_State["answers"] = {}
    Game_State["round"] += 1
    start_round()
    # Next round begins with a fresh clock and a fresh prompt.
    Game_State["round_ends_at"] = round_deadline()
    return RedirectResponse("/game", status_code=303)


@app.get("/game/scoreboard")
async def scoreboard(request: Request, player_name: str = Depends(current_player)):
    # Answers are private until a clock has actually started and finished.
    if not round_is_over(Game_State["round_ends_at"]):
        if player_name in Game_State["answers"]:
            return RedirectResponse("/game/answered", status_code=303)
        return RedirectResponse("/game", status_code=303)
    # Answered players first, in submission order, so the first spelling wins.
    items = list(Game_State["answers"].items())
    # Then anyone who never submitted, so they appear under "did not answer".
    items += [
        (name, "")
        for name in sorted(Game_State["player_names"])
        if name not in Game_State["answers"]
    ]
    grouped = group_answers(items)
    return templates.TemplateResponse(
        request,
        "scoreboard.html",
        {
            "player_name": player_name,
            "groups": grouped["groups"],
            "no_answer": grouped["no_answer"],
            "is_wrangler": is_wrangler(player_name),
            "round": Game_State["round"],
            "question": Game_State["question"],
        },
    )


def main() -> None:
    """Start the server.

    Binds to all interfaces by default so other devices on the local network
    can reach the game. Set HOST=127.0.0.1 to keep it private to this machine.
    """
    uvicorn.run(
        "herd_mentality.main:app",
        host=os.environ.get("HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "0") == "1",
    )


if __name__ == "__main__":
    main()
