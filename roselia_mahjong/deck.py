from __future__ import annotations

import random
from typing import Iterable, List, Optional

from .cards import CHARACTERS, COLORS, VOICE_ACTORS, Card


class DeckEmptyError(RuntimeError):
    """Raised when a draw is requested from an empty deck."""


def build_full_deck() -> List[Card]:
    cards: List[Card] = []
    for character in CHARACTERS:
        for color in COLORS:
            for _ in range(4):
                cards.append(Card.normal(character, color))
    for voice_actor in VOICE_ACTORS:
        cards.append(Card.voice_actor_card(voice_actor))
    return cards


class Deck:
    """Draw pile. The end of the internal list is the top of the deck."""

    def __init__(
        self,
        rng: Optional[random.Random] = None,
        cards: Optional[Iterable[Card]] = None,
    ) -> None:
        self._rng = rng or random.Random()
        self._cards = list(cards) if cards is not None else build_full_deck()

    @classmethod
    def from_draw_order(cls, cards: Iterable[Card]) -> "Deck":
        """Create a deck where the first iterable item will be drawn first."""

        return cls(cards=reversed(list(cards)))

    def shuffle(self) -> None:
        self._rng.shuffle(self._cards)

    def draw(self) -> Card:
        if not self._cards:
            raise DeckEmptyError("The deck is empty.")
        return self._cards.pop()

    def remaining(self) -> int:
        return len(self._cards)

    def __len__(self) -> int:
        return len(self._cards)
