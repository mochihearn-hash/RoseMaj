from __future__ import annotations

import random

from roselia_mahjong.cards import Card

from .models import PlayerSeat


def choose_riichi_discard(options: dict[int, set[Card]], rng: random.Random) -> int:
    return rng.choice(list(options))


def choose_discard(player: PlayerSeat, rng: random.Random) -> int:
    if player.riichi:
        return len(player.hand) - 1
    return rng.randrange(len(player.hand))
