"""FastAPI dependencies shared by the routers."""

from typing import Annotated

from fastapi import Depends, Request

from app.data.loader import GameData


def _game_data(request: Request) -> GameData:
    # Loaded once at startup and never mutated: the service is stateless and
    # read-only, so every request (and every replica) sees identical data.
    data: GameData = request.app.state.game_data
    return data


GameDataDep = Annotated[GameData, Depends(_game_data)]
