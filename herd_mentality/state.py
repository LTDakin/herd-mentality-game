"""In-memory game state, shared by the routes and the auth helpers."""

Game_State = {"wrangler": None, "player_names": set(), "answers": {}, "revealed": False}
