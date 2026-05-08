from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from .cards import Card


@dataclass
class Player:
    name: str
    is_human: bool = False
    hand: List[Card] = field(default_factory=list)
    discards: List[Card] = field(default_factory=list)
    riichi: bool = False
    riichi_waits: Set[Card] = field(default_factory=set)
    locked_hand: Optional[Tuple[Card, ...]] = None

    def draw(self, card: Card) -> None:
        self.hand.append(card)

    def discard_at(self, index: int) -> Card:
        card = self.hand.pop(index)
        self.discards.append(card)
        return card

    def declare_riichi(self, waits: Set[Card]) -> None:
        self.riichi = True
        self.riichi_waits = set(waits)
        self.locked_hand = tuple(self.hand)
