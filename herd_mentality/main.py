import json
import os
import random
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from herd_mentality.auth import (
    current_player,
    is_wrangler,
    logged_in_player,
    login_response,
    register_player,
)
from herd_mentality.scoring import group_answers
from herd_mentality.state import Game_State

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


@app.get("/")
async def root(request: Request):
    if logged_in_player(request) is not None:
        return RedirectResponse("/game", status_code=303)
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
    return login_response(player_name.strip())


@app.get("/game")
async def game(request: Request, player_name: str = Depends(current_player)):
    return templates.TemplateResponse(
        request, "game.html", {"player_name": player_name}
    )


@app.post("/game/answer")
async def game_answer(
    player_name: str = Depends(current_player), answer: str = Form(...)
):
    answer = answer.strip()
    if not answer:
        return RedirectResponse("/game", status_code=303)

    if player_name in Game_State["answers"]:
        return RedirectResponse("/game/answered", status_code=303)

    Game_State["answers"][player_name] = answer
    return RedirectResponse("/game/answered", status_code=303)


@app.get("/game/answered")
async def answered(request: Request, player_name: str = Depends(current_player)):
    curr_player_answer = Game_State["answers"].get(player_name)
    if curr_player_answer is None:
        return RedirectResponse("/game", status_code=303)
    # Once the round is revealed, the answers are public.
    if Game_State["revealed"]:
        return RedirectResponse("/game/scoreboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "answered.html",
        {
            "player_name": player_name,
            "answer": curr_player_answer,
            "is_wrangler": is_wrangler(player_name),
            "round": Game_State["round"],
            "cow_fact": random.choice(COW_FACTS),
        },
    )


@app.post("/game/reveal")
async def reveal(player_name: str = Depends(current_player)):
    """Wrangler only: end the round and reveal everyone's answers."""
    if not is_wrangler(player_name):
        return RedirectResponse("/game/answered", status_code=303)

    Game_State["revealed"] = True
    return RedirectResponse("/game/scoreboard", status_code=303)


@app.get("/game/status")
async def game_status(player_name: str = Depends(current_player)):
    """Polled by the answered and scoreboard pages to detect round changes."""
    return {"revealed": Game_State["revealed"], "round": Game_State["round"]}


@app.post("/game/next-round")
async def next_round(player_name: str = Depends(current_player)):
    """Wrangler only: clear the round's answers and start the next one."""
    if not is_wrangler(player_name):
        return RedirectResponse("/game/scoreboard", status_code=303)

    Game_State["answers"] = {}
    Game_State["revealed"] = False
    Game_State["round"] += 1
    return RedirectResponse("/game", status_code=303)


@app.get("/game/scoreboard")
async def scoreboard(request: Request, player_name: str = Depends(current_player)):
    if not Game_State["revealed"]:
        return RedirectResponse("/game/answered", status_code=303)
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
        },
    )


def main() -> None:
    """Start the development server."""
    uvicorn.run(
        "herd_mentality.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=os.environ.get("RELOAD", "1") == "1",
    )


if __name__ == "__main__":
    main()
