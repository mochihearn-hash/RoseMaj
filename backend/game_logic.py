from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Optional

from roselia_mahjong.cards import Card
from roselia_mahjong.deck import build_full_deck
from roselia_mahjong.rules import (
    describe_waits,
    evaluate_hand,
    format_win_types,
    riichi_discard_options,
)

from .models import PlayerSeat, card_to_dict


class GameError(RuntimeError):
    """Raised when an online player requests an illegal action."""


@dataclass(frozen=True)
class LastDiscard:
    player_id: str
    card: Card


@dataclass
class WinRecord:
    method: str
    winner_id: str
    winning_card: Card
    win_types: tuple[Any, ...]
    discarder_id: Optional[str] = None


class OnlineGame:
    """Server-authoritative game state for one room."""

    def __init__(self, players: list[PlayerSeat], seed: Optional[int] = None) -> None:
        if not 2 <= len(players) <= 4:
            raise GameError("A game requires 2 to 4 players.")
        self.players = players
        # Online games should not use a client-controllable seed. Tests may pass
        # a seed for reproducibility; production rooms use OS-backed randomness.
        self.rng = random.Random(seed) if seed is not None else random.SystemRandom()
        self.deck: list[Card] = []
        self.current_player_index = 0
        self.dealer_index = 0
        self.phase = "waiting"
        self.last_discard: Optional[LastDiscard] = None
        self.winner: Optional[WinRecord] = None
        self.draw_reason = ""

    def start(self) -> None:
        self.deck = build_full_deck()
        self.rng.shuffle(self.deck)
        self.dealer_index = self.rng.randrange(len(self.players))
        self.current_player_index = self.dealer_index
        self.phase = "need_draw"
        self.last_discard = None
        self.winner = None
        self.draw_reason = ""
        for player in self.players:
            player.reset_for_game()
            player.ready = True
        for _ in range(4):
            for player in self.players:
                player.hand.append(self._draw_from_deck())

    @property
    def is_finished(self) -> bool:
        return self.phase == "finished"

    @property
    def current_player(self) -> PlayerSeat:
        return self.players[self.current_player_index]

    @property
    def dealer(self) -> PlayerSeat:
        return self.players[self.dealer_index]

    def draw_tile(self, player_id: str) -> Card:
        player = self._require_current_player(player_id)
        if self.phase != "need_draw":
            raise GameError("You cannot draw right now.")
        self.last_discard = None
        card = self._draw_from_deck()
        player.hand.append(card)
        self.phase = "after_draw"
        return card

    def discard_tile(self, player_id: str, card_index: int) -> Card:
        player = self._require_current_player(player_id)
        if self.phase != "after_draw":
            raise GameError("You must draw before discarding.")
        if not 0 <= card_index < len(player.hand):
            raise GameError("Discard index is out of range.")
        if player.riichi and card_index != len(player.hand) - 1:
            raise GameError("Riichi hand is locked; discard the drawn card.")
        return self._discard_and_advance(player, card_index)

    def riichi_options(self, player_id: str) -> dict[int, set[Card]]:
        player = self._get_player(player_id)
        if self.phase != "after_draw" or self.current_player.id != player_id or player.riichi:
            return {}
        return riichi_discard_options(player.hand)

    def declare_riichi(self, player_id: str, card_index: int) -> tuple[Card, set[Card]]:
        player = self._require_current_player(player_id)
        if self.phase != "after_draw":
            raise GameError("Riichi can only be declared after drawing.")
        if player.riichi:
            raise GameError("You have already declared riichi.")

        options = self.riichi_options(player_id)
        if card_index not in options:
            raise GameError("That discard does not leave a tenpai hand.")

        waits = options[card_index]
        discarded = player.hand.pop(card_index)
        player.discards.append(discarded)
        player.riichi = True
        player.riichi_waits = set(waits)
        player.locked_hand = tuple(player.hand)
        self.last_discard = LastDiscard(player.id, discarded)
        self.phase = "need_draw"
        self._advance_turn()
        return discarded, waits

    def can_tsumo(self, player_id: str) -> bool:
        player = self._get_player(player_id)
        if self.phase != "after_draw" or self.current_player.id != player_id:
            return False
        if not player.riichi or len(player.hand) != 5:
            return False
        drawn_card = player.hand[-1]
        return drawn_card in player.riichi_waits and evaluate_hand(player.hand).is_win

    def claim_tsumo(self, player_id: str) -> WinRecord:
        player = self._require_current_player(player_id)
        if not self.can_tsumo(player_id):
            raise GameError("Tsumo requires a winning hand after riichi.")
        result = evaluate_hand(player.hand)
        self.winner = WinRecord(
            method="Tsumo",
            winner_id=player.id,
            winning_card=player.hand[-1],
            win_types=result.types,
        )
        self.phase = "finished"
        return self.winner

    def can_ron(self, player_id: str) -> bool:
        if self.last_discard is None:
            return False
        if self.last_discard.player_id == player_id:
            return False
        player = self._get_player(player_id)
        if not player.riichi:
            return False
        test_hand = [*player.hand, self.last_discard.card]
        return (
            self.last_discard.card in player.riichi_waits
            and evaluate_hand(test_hand).is_win
        )

    def ron_candidates(self) -> list[str]:
        if self.last_discard is None:
            return []
        discarder_index = self._player_index(self.last_discard.player_id)
        candidates: list[str] = []
        for offset in range(1, len(self.players)):
            index = (discarder_index + offset) % len(self.players)
            player = self.players[index]
            if self.can_ron(player.id):
                candidates.append(player.id)
        return candidates

    def claim_ron(self, player_id: str) -> WinRecord:
        if not self.can_ron(player_id):
            raise GameError("Ron requires a winning discard after riichi.")
        assert self.last_discard is not None
        player = self._get_player(player_id)
        result = evaluate_hand([*player.hand, self.last_discard.card])
        self.winner = WinRecord(
            method="Ron",
            winner_id=player.id,
            discarder_id=self.last_discard.player_id,
            winning_card=self.last_discard.card,
            win_types=result.types,
        )
        self.phase = "finished"
        return self.winner

    def pass_ron(self, player_id: str) -> None:
        if not self.can_ron(player_id):
            raise GameError("You do not have a Ron option to pass.")
        # MVP behavior: passing simply clears this player's opportunity by
        # clearing the shared last discard if no other human acts immediately.
        self.last_discard = None

    def public_state(self, viewer_id: str) -> dict[str, Any]:
        viewer = self._get_player(viewer_id)
        available_actions = {
            "can_draw": (
                self.phase == "need_draw"
                and not self.is_finished
                and self.current_player.id == viewer_id
                and not viewer.is_ai
            ),
            "can_discard": (
                self.phase == "after_draw"
                and not self.is_finished
                and self.current_player.id == viewer_id
                and not viewer.is_ai
            ),
            "can_riichi": bool(self.riichi_options(viewer_id)),
            "can_tsumo": self.can_tsumo(viewer_id),
            "can_ron": self.can_ron(viewer_id),
        }

        riichi_options = [
            {
                "index": index,
                "discard": card_to_dict(viewer.hand[index]),
                "waits": [card_to_dict(card) for card in sorted(waits, key=lambda c: c.label())],
                "waits_text": describe_waits(waits),
            }
            for index, waits in self.riichi_options(viewer_id).items()
        ]

        return {
            "phase": self.phase,
            "deck_remaining": len(self.deck),
            "current_player_id": self.current_player.id,
            "current_player_nickname": self.current_player.nickname,
            "dealer_player_id": self.dealer.id,
            "dealer_nickname": self.dealer.nickname,
            "players": [player.public_view() for player in self.players],
            "you": {
                "id": viewer.id,
                "nickname": viewer.nickname,
                "hand": [card_to_dict(card) for card in viewer.hand],
                "riichi": viewer.riichi,
                "riichi_waits": [card_to_dict(card) for card in sorted(viewer.riichi_waits, key=lambda c: c.label())],
            },
            "last_discard": (
                {
                    "player_id": self.last_discard.player_id,
                    "card": card_to_dict(self.last_discard.card),
                }
                if self.last_discard
                else None
            ),
            "available_actions": available_actions,
            "riichi_options": riichi_options,
            "winner": self._winner_state(),
            "draw_reason": self.draw_reason,
        }

    def winner_summary(self) -> dict[str, Any]:
        if self.winner is None:
            return {}
        winner = self._get_player(self.winner.winner_id)
        discarder = (
            self._get_player(self.winner.discarder_id)
            if self.winner.discarder_id is not None
            else None
        )
        return {
            "method": self.winner.method,
            "winner_id": winner.id,
            "winner_nickname": winner.nickname,
            "discarder_id": discarder.id if discarder else None,
            "discarder_nickname": discarder.nickname if discarder else None,
            "winning_card": card_to_dict(self.winner.winning_card),
            "win_types": [win_type.value for win_type in self.winner.win_types],
            "win_types_text": format_win_types(self.winner.win_types),
        }

    def _winner_state(self) -> Optional[dict[str, Any]]:
        return self.winner_summary() if self.winner else None

    def _discard_and_advance(self, player: PlayerSeat, card_index: int) -> Card:
        discarded = player.hand.pop(card_index)
        player.discards.append(discarded)
        self.last_discard = LastDiscard(player.id, discarded)
        self.phase = "need_draw"
        self._advance_turn()
        return discarded

    def _draw_from_deck(self) -> Card:
        if not self.deck:
            self.phase = "finished"
            self.draw_reason = "The deck is empty."
            raise GameError("The deck is empty.")
        return self.deck.pop()

    def _advance_turn(self) -> None:
        self.current_player_index = (self.current_player_index + 1) % len(self.players)

    def _require_current_player(self, player_id: str) -> PlayerSeat:
        player = self._get_player(player_id)
        if self.current_player.id != player_id:
            raise GameError("It is not your turn.")
        if self.is_finished:
            raise GameError("The game is already finished.")
        return player

    def _get_player(self, player_id: Optional[str]) -> PlayerSeat:
        for player in self.players:
            if player.id == player_id:
                return player
        raise GameError("Unknown player.")

    def _player_index(self, player_id: str) -> int:
        for index, player in enumerate(self.players):
            if player.id == player_id:
                return index
        raise GameError("Unknown player.")
