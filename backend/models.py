from __future__ import annotations

import secrets
import string
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional, Set, Tuple

from roselia_mahjong.cards import Card


ROOM_CODE_ALPHABET = string.ascii_uppercase + string.digits


def make_player_id() -> str:
    return uuid.uuid4().hex


def make_room_code(length: int = 5) -> str:
    return "".join(secrets.choice(ROOM_CODE_ALPHABET) for _ in range(length))


@dataclass
class PlayerSeat:
    id: str
    nickname: str
    is_ai: bool = False
    ready: bool = False
    connected: bool = True
    hand: list[Card] = field(default_factory=list)
    discards: list[Card] = field(default_factory=list)
    riichi: bool = False
    riichi_waits: Set[Card] = field(default_factory=set)
    locked_hand: Optional[Tuple[Card, ...]] = None

    def reset_for_game(self) -> None:
        self.hand.clear()
        self.discards.clear()
        self.riichi = False
        self.riichi_waits.clear()
        self.locked_hand = None

    def public_view(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "nickname": self.nickname,
            "is_ai": self.is_ai,
            "ready": self.ready,
            "connected": self.connected,
            "hand_count": len(self.hand),
            "discards": [card_to_dict(card) for card in self.discards],
            "riichi": self.riichi,
        }


def card_to_dict(card: Card) -> dict[str, Any]:
    return {
        "character": card.character,
        "color": card.color,
        "voice_actor": card.voice_actor,
        "is_voice_actor": card.is_voice_actor,
        "label": card.label(),
        "short_label": card.short_label(),
    }
