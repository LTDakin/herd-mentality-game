import os

import uvicorn
from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

player_name_cookie_key = "player_name"

Game_State = {"player_names": set(), "answers": [], "revealed": False}


def check_login(request: Request):
    player_name = request.cookies.get(player_name_cookie_key)
    if not player_name or player_name not in Game_State["player_names"]:
        return templates.TemplateResponse(request, "login.html")
    else:
        return RedirectResponse("/game", status_code=303)


@app.get("/")
async def root(request: Request):
    check_login(request)


@app.post("/login")
async def login(player_name: str = Form(...)):
    if player_name not in Game_State["player_names"]:
        Game_State["player_names"].add(player_name)
        response = RedirectResponse("/game", status_code=303)
        response.set_cookie(player_name_cookie_key, player_name)
        return response
    else:
        return


@app.get("/game")
async def game(request: Request):
    check_login(request)
    return templates.TemplateResponse(request, "game.html")


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
