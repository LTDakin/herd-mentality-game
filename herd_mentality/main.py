import os
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from herd_mentality.auth import (
    current_player,
    logged_in_player,
    login_response,
    register_player,
)
from herd_mentality.state import Game_State

app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


@app.get("/")
async def root(request: Request):
    if logged_in_player(request) is not None:
        return RedirectResponse("/game", status_code=303)
    return templates.TemplateResponse(request, "login.html")


@app.post("/login")
async def login(request: Request, player_name: str = Form(...)):
    status_code, error = register_player(player_name)
    if error is not None:
        return templates.TemplateResponse(
            request, "login.html", {"error": error}, status_code=status_code
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
    return templates.TemplateResponse(
        request,
        "answered.html",
        {"player_name": player_name, "answer": curr_player_answer},
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
