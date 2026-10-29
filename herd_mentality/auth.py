"""Login and session helpers shared by the routes."""

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse

from herd_mentality.state import Game_State

player_name_cookie_key = "player_name"


def login_redirect():
    """Redirect to the login page, usable as `raise login_redirect()` from a dependency."""
    return HTTPException(status_code=303, headers={"Location": "/"})


def logged_in_player(request: Request):
    """Return the logged-in player's name, or None if not logged in."""
    player_name = request.cookies.get(player_name_cookie_key)
    if player_name in Game_State["player_names"]:
        return player_name
    return None


def current_player(request: Request):
    """Dependency: resolve the logged-in player, redirecting to login if absent."""
    player_name = logged_in_player(request)
    if player_name is None:
        raise login_redirect()
    return player_name


def register_player(player_name: str, wants_wrangler: bool = False):
    """Add the player's name to the game.

    If `wants_wrangler` is set and the game has no wrangler yet, this player
    becomes the wrangler (game master). The first wrangler wins, so a late
    request cannot take the role from them.

    Returns (status_code, error_message), with status_code None on success.
    """
    player_name = player_name.strip()
    if not player_name:
        return 422, "Enter a name to continue."

    # Names are unique per player, so logging in with an existing name would
    # let anyone take over someone else's identity with a forged cookie.
    if player_name in Game_State["player_names"]:
        return 409, f"{player_name} is already taken, pick another name."

    Game_State["player_names"].add(player_name)
    if wants_wrangler and Game_State["wrangler"] is None:
        Game_State["wrangler"] = player_name
    return None, None


def is_wrangler(player_name: str | None) -> bool:
    """True if this player is the game's wrangler."""
    return player_name is not None and player_name == Game_State["wrangler"]


def login_response(player_name: str) -> RedirectResponse:
    """Redirect to the game with the player's session cookie set."""
    response = RedirectResponse("/game", status_code=303)
    response.set_cookie(player_name_cookie_key, player_name)
    return response
