from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional, Protocol

from roselia_mahjong.game import AI_PLAYER_NAMES, MAX_PLAYERS, MIN_PLAYERS

from .ai_player import choose_discard, choose_riichi_discard
from .game_logic import GameError, OnlineGame
from .models import PlayerSeat, card_to_dict, make_player_id, make_room_code


class WebSocketLike(Protocol):
    async def send_json(self, data: dict[str, Any]) -> None:
        ...


@dataclass
class Room:
    code: str
    owner_id: str
    is_ai_room: bool = False
    players: list[PlayerSeat] = field(default_factory=list)
    sockets: dict[str, WebSocketLike] = field(default_factory=dict)
    game: Optional[OnlineGame] = None

    @property
    def status(self) -> str:
        if self.game is None:
            return "waiting"
        return "finished" if self.game.is_finished else "playing"


class RoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def create_room(self, websocket: WebSocketLike, nickname: str) -> tuple[str, str]:
        nickname = self._clean_nickname(nickname)
        async with self._lock:
            code = self._unique_room_code()
            player = PlayerSeat(id=make_player_id(), nickname=nickname)
            room = Room(
                code=code,
                owner_id=player.id,
                players=[player],
                sockets={player.id: websocket},
            )
            self.rooms[code] = room
        await self.broadcast(room, "room_created", {"room_code": code, "player_id": player.id})
        return code, player.id

    async def join_room(self, websocket: WebSocketLike, room_code: str, nickname: str) -> tuple[str, str]:
        nickname = self._clean_nickname(nickname)
        room_code = room_code.strip().upper()
        async with self._lock:
            room = self._require_room(room_code)
            if room.game is not None:
                raise GameError("This room has already started.")
            if len(room.players) >= MAX_PLAYERS:
                raise GameError("This room is full.")
            player = PlayerSeat(id=make_player_id(), nickname=nickname)
            room.players.append(player)
            room.sockets[player.id] = websocket
        await self.broadcast(room, "player_joined", {"player_id": player.id})
        return room.code, player.id

    async def start_ai_game(
        self,
        websocket: WebSocketLike,
        nickname: str,
        ai_count: int = 3,
    ) -> tuple[str, str]:
        nickname = self._clean_nickname(nickname)
        # 1 个真人 + 最多 (MAX_PLAYERS - 1) 个 AI
        ai_count = max(1, min(MAX_PLAYERS - 1, ai_count))
        async with self._lock:
            code = self._unique_room_code()
            human = PlayerSeat(id=make_player_id(), nickname=nickname, ready=True)
            players = [human]
            for index in range(ai_count):
                players.append(
                    PlayerSeat(
                        id=make_player_id(),
                        nickname=AI_PLAYER_NAMES[index],
                        is_ai=True,
                        ready=True,
                    )
                )
            room = Room(
                code=code,
                owner_id=human.id,
                is_ai_room=True,
                players=players,
                sockets={human.id: websocket},
            )
            game = OnlineGame(room.players)
            game.start()
            room.game = game
            self.rooms[code] = room
        await self.broadcast(room, "game_started", {"room_code": code, "player_id": human.id})
        await self._advance_until_human_action(room)
        return code, human.id

    async def toggle_ready(self, room_code: str, player_id: str) -> None:
        room = self._require_room(room_code)
        if room.is_ai_room:
            raise GameError("AI rooms restart with New Game.")
        if room.game is not None and not room.game.is_finished:
            raise GameError("The game has already started.")
        player = self._require_player(room, player_id)
        player.ready = not player.ready
        await self.broadcast(room, "player_ready_changed", {"player_id": player_id})

        if room.game is None and self._can_start_ready_room(room):
            room.game = OnlineGame(room.players)
            room.game.start()
            await self.broadcast(room, "game_started", {})
            await self._advance_until_human_action(room)

    async def restart_game(self, room_code: str, player_id: str) -> None:
        room = self._require_room(room_code)
        if room.owner_id != player_id:
            raise GameError("Only the room owner can restart the game.")
        if room.game is None or not room.game.is_finished:
            raise GameError("The game is not finished yet.")
        if not room.is_ai_room and not self._can_start_ready_room(room):
            raise GameError("All players must be ready before restart.")

        room.game = OnlineGame(room.players)
        room.game.start()
        await self.broadcast(room, "game_started", {})
        await self._advance_until_human_action(room)

    async def handle_game_action(
        self,
        room_code: str,
        player_id: str,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        room = self._require_room(room_code)
        if event_type == "restart_game":
            await self.restart_game(room_code, player_id)
            return

        if room.game is None:
            raise GameError("The game has not started.")

        game = room.game
        if event_type == "draw_tile":
            try:
                game.draw_tile(player_id)
            except GameError:
                if game.is_finished and game.draw_reason:
                    self._prepare_finished_room(room)
                    await self.broadcast(room, "game_draw", {"reason": game.draw_reason})
                    return
                raise
            await self.broadcast(
                room,
                "player_drawn",
                {"player_id": player_id},
            )
            return

        if event_type == "discard_tile":
            card_index = int(payload.get("card_index", -1))
            discarded = game.discard_tile(player_id, card_index)
            await self.broadcast(
                room,
                "player_discarded",
                {"player_id": player_id, "card": card_to_dict(discarded)},
            )
            await self._resolve_after_discard(room)
            return

        if event_type == "declare_riichi":
            card_index = int(payload.get("card_index", -1))
            discarded, waits = game.declare_riichi(player_id, card_index)
            await self.broadcast(
                room,
                "riichi_declared",
                {
                    "player_id": player_id,
                    "card": card_to_dict(discarded),
                    "waits": [card_to_dict(card) for card in waits],
                },
            )
            await self._resolve_after_discard(room)
            return

        if event_type == "claim_tsumo":
            result = game.claim_tsumo(player_id)
            self._prepare_finished_room(room)
            await self.broadcast(room, "player_won", {"winner": game.winner_summary()})
            return

        if event_type == "claim_ron":
            result = game.claim_ron(player_id)
            self._prepare_finished_room(room)
            await self.broadcast(room, "player_won", {"winner": game.winner_summary()})
            return

        if event_type == "pass_ron":
            game.pass_ron(player_id)
            await self.broadcast(room, "game_state_updated", {})
            await self._advance_until_human_action(room)
            return

        raise GameError(f"Unknown game action: {event_type}")

    async def disconnect(self, room_code: Optional[str], player_id: Optional[str]) -> None:
        if not room_code or not player_id or room_code not in self.rooms:
            return
        room = self.rooms[room_code]
        room.sockets.pop(player_id, None)
        player = next((item for item in room.players if item.id == player_id), None)
        if player is None:
            return

        if room.game is None:
            room.players = [item for item in room.players if item.id != player_id]
            if not room.players:
                self.rooms.pop(room_code, None)
                return
            if room.owner_id == player_id:
                room.owner_id = room.players[0].id
        else:
            player.connected = False

        await self.broadcast(room, "game_state_updated", {})

    async def send_error(self, websocket: WebSocketLike, message: str) -> None:
        await websocket.send_json({"type": "error", "payload": {"message": message}})

    async def broadcast(
        self,
        room: Room,
        event_type: str,
        extra: Optional[dict[str, Any]] = None,
    ) -> None:
        extra = extra or {}
        for player_id, websocket in list(room.sockets.items()):
            payload = {**extra, "state": self.room_state(room, player_id)}
            try:
                await websocket.send_json({"type": event_type, "payload": payload})
            except RuntimeError:
                room.sockets.pop(player_id, None)

    def room_state(self, room: Room, viewer_id: str) -> dict[str, Any]:
        state: dict[str, Any] = {
            "room_code": room.code,
            "status": room.status,
            "owner_id": room.owner_id,
            "is_ai_room": room.is_ai_room,
            "players": [player.public_view() for player in room.players],
            "you": {
                "id": viewer_id,
                "is_owner": room.owner_id == viewer_id,
            },
            "can_toggle_ready": (
                not room.is_ai_room
                and (room.game is None or room.game.is_finished)
            ),
            "can_restart": (
                room.owner_id == viewer_id
                and room.game is not None
                and room.game.is_finished
                and (
                    room.is_ai_room
                    or self._can_start_ready_room(room)
                )
            ),
        }
        if room.game is not None:
            state["game"] = room.game.public_state(viewer_id)
        return state

    async def _resolve_after_discard(self, room: Room) -> None:
        assert room.game is not None
        game = room.game
        candidates = game.ron_candidates()
        if candidates:
            first = self._require_player(room, candidates[0])
            if first.is_ai:
                game.claim_ron(first.id)
                self._prepare_finished_room(room)
                await self.broadcast(room, "player_won", {"winner": game.winner_summary()})
                return
            await self.broadcast(room, "game_state_updated", {})
            return
        await self._advance_until_human_action(room)

    async def _advance_until_human_action(self, room: Room) -> None:
        await self._run_ai_until_human(room)
        game = room.game
        if game is None or game.is_finished:
            return
        if game.ron_candidates():
            return
        if game.current_player.is_ai or game.phase != "need_draw":
            return

        human = game.current_player
        try:
            game.draw_tile(human.id)
        except GameError:
            self._prepare_finished_room(room)
            await self.broadcast(room, "game_draw", {"reason": game.draw_reason})
            return
        await self.broadcast(room, "player_drawn", {"player_id": human.id})

    async def _run_ai_until_human(self, room: Room) -> None:
        game = room.game
        if game is None:
            return

        while not game.is_finished and game.current_player.is_ai:
            if game.ron_candidates():
                await self._resolve_after_discard(room)
                return

            ai_player = game.current_player
            try:
                drawn = game.draw_tile(ai_player.id)
            except GameError:
                self._prepare_finished_room(room)
                await self.broadcast(room, "game_draw", {"reason": game.draw_reason})
                return
            await self.broadcast(room, "player_drawn", {"player_id": ai_player.id})

            if game.can_tsumo(ai_player.id):
                game.claim_tsumo(ai_player.id)
                self._prepare_finished_room(room)
                await self.broadcast(room, "player_won", {"winner": game.winner_summary()})
                return

            options = game.riichi_options(ai_player.id)
            if options:
                discard_index = choose_riichi_discard(options, game.rng)
                discarded, waits = game.declare_riichi(ai_player.id, discard_index)
                await self.broadcast(
                    room,
                    "riichi_declared",
                    {
                        "player_id": ai_player.id,
                        "card": card_to_dict(discarded),
                        "waits": [card_to_dict(card) for card in waits],
                    },
                )
            else:
                discard_index = choose_discard(ai_player, game.rng)
                discarded = game.discard_tile(ai_player.id, discard_index)
                await self.broadcast(
                    room,
                    "player_discarded",
                    {"player_id": ai_player.id, "card": card_to_dict(discarded)},
                )

            candidates = game.ron_candidates()
            if candidates:
                first = self._require_player(room, candidates[0])
                if first.is_ai:
                    game.claim_ron(first.id)
                    self._prepare_finished_room(room)
                    await self.broadcast(room, "player_won", {"winner": game.winner_summary()})
                    return
                await self.broadcast(room, "game_state_updated", {})
                return

    def _can_start_ready_room(self, room: Room) -> bool:
        return (
            MIN_PLAYERS <= len(room.players) <= MAX_PLAYERS
            and all(player.connected for player in room.players if not player.is_ai)
            and all(player.ready for player in room.players)
        )

    def _prepare_finished_room(self, room: Room) -> None:
        if room.is_ai_room:
            return
        for player in room.players:
            player.ready = False

    def _unique_room_code(self) -> str:
        while True:
            code = make_room_code()
            if code not in self.rooms:
                return code

    def _require_room(self, room_code: str) -> Room:
        room = self.rooms.get(room_code)
        if room is None:
            raise GameError("Room not found.")
        return room

    def _require_player(self, room: Room, player_id: str) -> PlayerSeat:
        for player in room.players:
            if player.id == player_id:
                return player
        raise GameError("Player not found in room.")

    def _clean_nickname(self, nickname: str) -> str:
        nickname = nickname.strip()
        if not nickname:
            raise GameError("Nickname is required.")
        return nickname[:20]
