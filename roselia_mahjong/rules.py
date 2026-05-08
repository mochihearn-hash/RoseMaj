from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterable, Sequence, Set, Tuple

from .cards import CHARACTERS, COLORS, Card, all_card_types, sorted_cards


class WinType(str, Enum):
    SAME_CHARACTER = "Same Character"
    SAME_COLOR = "Same Color"
    ROSELIA_COMPLETE = "Roselia Complete"


@dataclass(frozen=True)
class WinResult:
    types: Tuple[WinType, ...]

    @property
    def is_win(self) -> bool:
        return bool(self.types)


def winning_types(cards: Sequence[Card]) -> Tuple[WinType, ...]:
    if len(cards) != 5:
        return tuple()

    types = []
    if _is_same_character(cards):
        types.append(WinType.SAME_CHARACTER)
    if _is_same_color(cards):
        types.append(WinType.SAME_COLOR)
    if _is_roselia_complete(cards):
        types.append(WinType.ROSELIA_COMPLETE)
    return tuple(types)


def evaluate_hand(cards: Sequence[Card]) -> WinResult:
    return WinResult(types=winning_types(cards))


def is_winning_hand(cards: Sequence[Card]) -> bool:
    return evaluate_hand(cards).is_win


def winning_waits(hand: Sequence[Card], candidates: Iterable[Card] = all_card_types()) -> Set[Card]:
    """Return distinct card identities that complete this 4-card hand."""

    if len(hand) != 4:
        return set()

    waits = set()
    for candidate in candidates:
        if is_winning_hand([*hand, candidate]):
            waits.add(candidate)
    return waits


def riichi_discard_options(hand: Sequence[Card]) -> Dict[int, Set[Card]]:
    """Return discard indexes that leave a 4-card tenpai hand after drawing."""

    if len(hand) != 5:
        return {}

    options: Dict[int, Set[Card]] = {}
    for discard_index in range(len(hand)):
        remaining_hand = [
            card for index, card in enumerate(hand) if index != discard_index
        ]
        waits = winning_waits(remaining_hand)
        if waits:
            options[discard_index] = waits
    return options


def is_tenpai(hand: Sequence[Card]) -> bool:
    return bool(winning_waits(hand))


def format_win_types(types: Sequence[WinType]) -> str:
    return ", ".join(win_type.value for win_type in types)


def describe_waits(waits: Iterable[Card]) -> str:
    cards = sorted_cards(waits)
    return ", ".join(card.label() for card in cards)


def describe_riichi_options(hand: Sequence[Card]) -> str:
    options = riichi_discard_options(hand)
    descriptions = []
    for index in sorted(options):
        card = hand[index]
        descriptions.append(f"{index}: {card.label()} -> {describe_waits(options[index])}")
    return "\n".join(descriptions)


def _is_same_character(cards: Sequence[Card]) -> bool:
    first_character = cards[0].character
    return all(card.character == first_character for card in cards)


def _is_same_color(cards: Sequence[Card]) -> bool:
    # Voice actor cards may declare any color for their mapped character.
    for color in COLORS:
        if all(card.is_voice_actor or card.color == color for card in cards):
            return True
    return False


def _is_roselia_complete(cards: Sequence[Card]) -> bool:
    characters = {card.character for card in cards}
    return len(characters) == len(CHARACTERS) and characters == set(CHARACTERS)
