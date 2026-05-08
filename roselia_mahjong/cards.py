from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


CHARACTERS: Tuple[str, ...] = ("Yukina", "Sayo", "Lisa", "Ako", "Rinko")
COLORS: Tuple[str, ...] = ("Red", "Orange", "Green", "Blue")

VOICE_ACTORS = {
    "Aiba Aina": "Yukina",
    "Kudoh Haruka": "Sayo",
    "Nakashima Yuki": "Lisa",
    "Sakuragawa Megu": "Ako",
    "Shizaki Kanon": "Rinko",
}

VOICE_ACTOR_BY_CHARACTER = {character: actor for actor, character in VOICE_ACTORS.items()}


@dataclass(frozen=True)
class Card:
    """A normal character-color card or a voice actor wildcard card."""

    character: str
    color: Optional[str] = None
    voice_actor: Optional[str] = None

    def __post_init__(self) -> None:
        if self.character not in CHARACTERS:
            raise ValueError(f"Unknown character: {self.character}")

        if self.voice_actor is None:
            if self.color not in COLORS:
                raise ValueError(f"Normal cards require a valid color: {self.color}")
            return

        if self.color is not None:
            raise ValueError("Voice actor cards cannot have a fixed color.")
        if self.voice_actor not in VOICE_ACTORS:
            raise ValueError(f"Unknown voice actor: {self.voice_actor}")
        if VOICE_ACTORS[self.voice_actor] != self.character:
            raise ValueError(
                f"{self.voice_actor} maps to {VOICE_ACTORS[self.voice_actor]}, "
                f"not {self.character}"
            )

    @property
    def is_voice_actor(self) -> bool:
        return self.voice_actor is not None

    @classmethod
    def normal(cls, character: str, color: str) -> "Card":
        return cls(character=character, color=color)

    @classmethod
    def voice_actor_card(cls, voice_actor: str) -> "Card":
        return cls(character=VOICE_ACTORS[voice_actor], voice_actor=voice_actor)

    def label(self) -> str:
        if self.is_voice_actor:
            return f"{self.voice_actor} -> {self.character}"
        return f"{self.character}-{self.color}"

    def short_label(self) -> str:
        if self.is_voice_actor:
            return f"VA:{self.character}"
        return f"{self.character[0]}-{self.color[0]}"

    def __str__(self) -> str:
        return self.label()


def all_card_types() -> Tuple[Card, ...]:
    """Return each distinct card identity, ignoring physical copy count."""

    normal_cards = [Card.normal(character, color) for character in CHARACTERS for color in COLORS]
    voice_actor_cards = [Card.voice_actor_card(actor) for actor in VOICE_ACTORS]
    return tuple(normal_cards + voice_actor_cards)


def card_sort_key(card: Card) -> Tuple[int, int, int, str]:
    character_index = CHARACTERS.index(card.character)
    if card.is_voice_actor:
        return (character_index, 1, -1, card.voice_actor or "")
    color_index = COLORS.index(card.color or COLORS[0])
    return (character_index, 0, color_index, "")


def sorted_cards(cards: Iterable[Card]) -> List[Card]:
    return sorted(cards, key=card_sort_key)
