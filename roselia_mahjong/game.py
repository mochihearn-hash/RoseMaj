from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .cards import Card
from .deck import Deck, DeckEmptyError
from .player import Player
from .rules import WinType, evaluate_hand, riichi_discard_options


class InvalidAction(RuntimeError):
    """Raised when a player attempts an illegal game action."""


# 人数范围与 AI 座位名在这里统一定义，其它模块一律引用这里的常量。
# 以前 2 / 4 这两个数字散落在 cli、gui 和后端里各写一遍，改一处漏一处。
MIN_PLAYERS = 2
MAX_PLAYERS = 5

# AI 座位名，按座位顺序。五个名字刚好对应 Roselia 五名成员；
# 人机混战时只用前 count-1 个，把 0 号位留给玩家。
AI_PLAYER_NAMES: Tuple[str, ...] = (
    "AI-Yukina",
    "AI-Sayo",
    "AI-Lisa",
    "AI-Ako",
    "AI-Rinko",
)


def build_player_names(
    count: int,
    human_name: str = "You",
    ai_only: bool = False,
) -> List[str]:
    """按人数生成座位名，命令行和图形界面共用，保证两边一致。"""

    if not MIN_PLAYERS <= count <= MAX_PLAYERS:
        raise ValueError(
            f"Player count must be between {MIN_PLAYERS} and {MAX_PLAYERS}, got {count}."
        )

    if ai_only:
        return list(AI_PLAYER_NAMES[:count])
    return [human_name, *AI_PLAYER_NAMES[: count - 1]]


@dataclass(frozen=True)
class GameResult:
    method: str
    winner_index: Optional[int] = None
    discarder_index: Optional[int] = None
    winning_card: Optional[Card] = None
    final_hand: Tuple[Card, ...] = tuple()
    win_types: Tuple[WinType, ...] = tuple()
    reason: str = ""


class Game:
    def __init__(
        self,
        player_names: Sequence[str],
        human_index: Optional[int] = 0,
        seed: Optional[int] = None,
        deck: Optional[Deck] = None,
    ) -> None:
        if not MIN_PLAYERS <= len(player_names) <= MAX_PLAYERS:
            raise ValueError(
                f"The game supports {MIN_PLAYERS} to {MAX_PLAYERS} players, "
                f"got {len(player_names)}."
            )

        self.rng = random.Random(seed)
        self.deck = deck or Deck(rng=self.rng)
        self.players: List[Player] = [
            Player(name=name, is_human=(human_index == index))
            for index, name in enumerate(player_names)
        ]
        self.current_player_index = 0
        self.dealer_index = 0
        self.result: Optional[GameResult] = None

    @property
    def is_over(self) -> bool:
        return self.result is not None

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    @property
    def dealer(self) -> Player:
        return self.players[self.dealer_index]

    def setup(self, shuffle: bool = True) -> None:
        if shuffle:
            self.deck.shuffle()
        # Pick the dealer at random and let them act first, as the documented
        # rules require. Always starting from seat 0 handed the first two
        # seats a large, measurable win-rate advantage.
        self.dealer_index = self.rng.randrange(len(self.players))
        self.current_player_index = self.dealer_index
        for _ in range(4):
            for player in self.players:
                player.draw(self.deck.draw())

    def riichi_options(self, player_index: int) -> dict[int, set[Card]]:
        return riichi_discard_options(self.players[player_index].hand)

    def declare_riichi_and_discard(self, player_index: int, card_index: int) -> tuple[Card, set[Card]]:
        if player_index != self.current_player_index:
            raise InvalidAction("Riichi can only be declared by the current player.")

        player = self.players[player_index]
        if player.riichi:
            raise InvalidAction(f"{player.name} has already declared riichi.")
        if len(player.hand) != 5:
            raise InvalidAction("Riichi can only be declared after drawing to 5 cards.")

        options = self.riichi_options(player_index)
        if card_index not in options:
            raise InvalidAction("That discard does not leave a tenpai hand for riichi.")

        waits = options[card_index]
        discarded_card = player.discard_at(card_index)
        player.declare_riichi(waits)
        return discarded_card, waits

    def draw_for_current_player(self) -> Card:
        if self.is_over:
            raise InvalidAction("The game is already over.")
        try:
            card = self.deck.draw()
        except DeckEmptyError:
            self.result = GameResult(method="Draw", reason="The deck is empty.")
            raise
        self.current_player.draw(card)
        return card

    def can_tsumo(self, player_index: int) -> bool:
        player = self.players[player_index]
        if not player.riichi or len(player.hand) != 5:
            return False
        drawn_card = player.hand[-1]
        return drawn_card in player.riichi_waits and evaluate_hand(player.hand).is_win

    def finish_tsumo(self, player_index: int) -> GameResult:
        player = self.players[player_index]
        result = evaluate_hand(player.hand)
        if not self.can_tsumo(player_index):
            raise InvalidAction("Tsumo requires a winning hand after riichi.")

        self.result = GameResult(
            method="Tsumo",
            winner_index=player_index,
            winning_card=player.hand[-1],
            final_hand=tuple(player.hand),
            win_types=result.types,
        )
        return self.result

    def discard_current_player(self, card_index: int) -> Card:
        player = self.current_player
        if len(player.hand) != 5:
            raise InvalidAction("A player must draw to 5 cards before discarding.")

        # Riichi locks the original 4-card shape; non-winning draws are cut.
        if player.riichi and card_index != len(player.hand) - 1:
            raise InvalidAction("Riichi hand is locked; discard the drawn card.")

        return player.discard_at(card_index)

    def ron_candidates(self, discarder_index: int, discarded_card: Card) -> List[int]:
        candidates: List[int] = []
        for offset in range(1, len(self.players)):
            index = (discarder_index + offset) % len(self.players)
            player = self.players[index]
            if not player.riichi:
                continue
            test_hand = [*player.hand, discarded_card]
            if discarded_card in player.riichi_waits and evaluate_hand(test_hand).is_win:
                candidates.append(index)
        return candidates

    def finish_ron(
        self,
        winner_index: int,
        discarder_index: int,
        discarded_card: Card,
    ) -> GameResult:
        winner = self.players[winner_index]
        test_hand = [*winner.hand, discarded_card]
        result = evaluate_hand(test_hand)
        if (
            not winner.riichi
            or discarded_card not in winner.riichi_waits
            or not result.is_win
        ):
            raise InvalidAction("Ron requires a winning hand after riichi.")

        self.result = GameResult(
            method="Ron",
            winner_index=winner_index,
            discarder_index=discarder_index,
            winning_card=discarded_card,
            final_hand=tuple(test_hand),
            win_types=result.types,
        )
        return self.result

    def advance_turn(self) -> None:
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
