from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

try:
    from .game_logic import GameError
    from .room_manager import RoomManager
except ImportError:  # Allows running `python backend/main.py` during development.
    from backend.game_logic import GameError
    from backend.room_manager import RoomManager


app = FastAPI(title="ReseMaj_Online")
manager = RoomManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    room_code: Optional[str] = None
    player_id: Optional[str] = None

    try:
        while True:
            message: dict[str, Any] = await websocket.receive_json()
            event_type = message.get("type")
            payload = message.get("payload") or {}

            try:
                if event_type == "create_room":
                    room_code, player_id = await manager.create_room(
                        websocket,
                        payload.get("nickname", ""),
                    )
                    continue

                if event_type == "join_room":
                    room_code, player_id = await manager.join_room(
                        websocket,
                        payload.get("room_code", ""),
                        payload.get("nickname", ""),
                    )
                    continue

                if event_type == "start_ai_game":
                    room_code, player_id = await manager.start_ai_game(
                        websocket,
                        payload.get("nickname", ""),
                        int(payload.get("ai_count", 3)),
                    )
                    continue

                if event_type == "toggle_ready":
                    _require_session(room_code, player_id)
                    await manager.toggle_ready(room_code, player_id)
                    continue

                _require_session(room_code, player_id)
                await manager.handle_game_action(room_code, player_id, event_type, payload)
            except (GameError, ValueError) as exc:
                await manager.send_error(websocket, str(exc))

    except WebSocketDisconnect:
        await manager.disconnect(room_code, player_id)


def _require_session(room_code: Optional[str], player_id: Optional[str]) -> None:
    if not room_code or not player_id:
        raise GameError("Create or join a room first.")


FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
