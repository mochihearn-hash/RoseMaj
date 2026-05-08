from __future__ import annotations

import random

from .cards import Card
from .player import Player


class SimpleAI:
    """Minimal strategy: riichi if possible, win if possible, otherwise random discard."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def wants_riichi(self, player: Player) -> bool:
        return not player.riichi

    def choose_riichi_discard_index(self, options: dict[int, set[Card]]) -> int:
        return self.rng.choice(list(options))

    def choose_discard_index(self, player: Player) -> int:
        if player.riichi:
            return len(player.hand) - 1
        return self.rng.randrange(len(player.hand))
