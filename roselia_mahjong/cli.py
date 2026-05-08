from __future__ import annotations

import argparse
from typing import Iterable, List, Optional, Sequence

from .ai import SimpleAI
from .cards import Card
from .deck import DeckEmptyError
from .game import Game, GameResult, InvalidAction
from .rules import describe_waits, evaluate_hand, format_win_types


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Roselia Mahjong CLI prototype")
    parser.add_argument("--players", type=int, default=4, help="Number of players: 2 to 4")
    parser.add_argument("--human-name", default="You", help="Human player name")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducible games")
    parser.add_argument("--ai-only", action="store_true", help="Run all seats as simple AI")
    parser.add_argument("--max-turns", type=int, default=None, help="Optional safety limit")
    args = parser.parse_args(argv)

    if not 2 <= args.players <= 4:
        print("Player count must be between 2 and 4.")
        return 2

    names = _build_player_names(args.players, args.human_name, args.ai_only)
    human_index = None if args.ai_only else 0
    game = Game(names, human_index=human_index, seed=args.seed)
    game.setup()
    ai = SimpleAI(game.rng)

    print("Roselia Mahjong Prototype")
    print(f"Players: {', '.join(player.name for player in game.players)}")
    print(f"Deck remaining after deal: {game.deck.remaining()}")
    print()

    turn_count = 0
    while not game.is_over:
        if args.max_turns is not None and turn_count >= args.max_turns:
            game.result = GameResult(method="Draw", reason="Reached max turn limit.")
            break

        player_index = game.current_player_index
        player = game.current_player
        print(f"Turn {turn_count + 1}: {player.name}")

        if player.is_human:
            print(f"Your hand: {_format_cards(player.hand, indexed=True)}")

        try:
            drawn_card = game.draw_for_current_player()
        except DeckEmptyError:
            break

        if player.is_human:
            print(f"You draw: {drawn_card.label()}")

        if game.can_tsumo(player_index):
            if not player.is_human or _ask_yes_no("Tsumo? [Y/n] ", default=True):
                result = game.finish_tsumo(player_index)
                _print_result(game, result)
                return 0

        discarded_card = None
        if not player.riichi:
            options = game.riichi_options(player_index)
            if options:
                if player.is_human:
                    print("You can declare riichi after discarding one of these cards:")
                    print(_format_riichi_options(player.hand, options))
                    if _ask_yes_no("Declare riichi? [y/N] "):
                        discard_index = _choose_riichi_discard(player.hand, options)
                        discarded_card, waits = game.declare_riichi_and_discard(
                            player_index,
                            discard_index,
                        )
                        print(f"Riichi declared. Waits: {describe_waits(waits)}")
                elif ai.wants_riichi(player):
                    discard_index = ai.choose_riichi_discard_index(options)
                    discarded_card, waits = game.declare_riichi_and_discard(
                        player_index,
                        discard_index,
                    )
                    print(f"{player.name} declares riichi. Waits: {describe_waits(waits)}")

        if discarded_card is None:
            discard_index = _choose_discard(game, ai, drawn_card)
            try:
                discarded_card = game.discard_current_player(discard_index)
            except InvalidAction as exc:
                print(f"Invalid discard: {exc}")
                continue

        print(f"{player.name} discards: {discarded_card.label()}")

        ron_winner = _choose_ron_winner(game, player_index, discarded_card)
        if ron_winner is not None:
            result = game.finish_ron(ron_winner, player_index, discarded_card)
            _print_result(game, result)
            return 0

        print(f"Deck remaining: {game.deck.remaining()}")
        print()
        game.advance_turn()
        turn_count += 1

    if game.result is not None:
        _print_result(game, game.result)
    return 0


def _build_player_names(count: int, human_name: str, ai_only: bool) -> List[str]:
    ai_names = ["AI-Sayo", "AI-Lisa", "AI-Ako", "AI-Rinko"]
    if ai_only:
        return ai_names[:count]
    return [human_name, *ai_names[: count - 1]]


def _choose_discard(game: Game, ai: SimpleAI, drawn_card: Card) -> int:
    player = game.current_player
    if player.riichi:
        print(f"{player.name} is in riichi and discards the draw.")
        return len(player.hand) - 1

    if not player.is_human:
        return ai.choose_discard_index(player)

    result = evaluate_hand(player.hand)
    if result.is_win:
        print("This is a winning shape, but dama is not allowed. You must discard.")

    while True:
        print(f"Your 5-card hand: {_format_cards(player.hand, indexed=True)}")
        raw = input("Choose a discard index: ").strip()
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        index = int(raw)
        if 0 <= index < len(player.hand):
            return index
        print("Index out of range.")


def _choose_riichi_discard(hand: Sequence[Card], options: dict[int, set[Card]]) -> int:
    while True:
        raw = input("Choose a riichi discard index: ").strip()
        if not raw.isdigit():
            print("Please enter a number.")
            continue
        index = int(raw)
        if index in options:
            return index
        print("That card does not leave a tenpai hand.")


def _format_riichi_options(hand: Sequence[Card], options: dict[int, set[Card]]) -> str:
    lines = []
    for index in sorted(options):
        lines.append(f"{index}: {hand[index].label()} -> waits: {describe_waits(options[index])}")
    return "\n".join(lines)


def _choose_ron_winner(game: Game, discarder_index: int, discarded_card: Card) -> Optional[int]:
    for candidate_index in game.ron_candidates(discarder_index, discarded_card):
        player = game.players[candidate_index]
        if not player.is_human:
            print(f"{player.name} calls Ron.")
            return candidate_index
        print(f"You can Ron on {discarded_card.label()}.")
        if _ask_yes_no("Call Ron? [Y/n] ", default=True):
            return candidate_index
    return None


def _print_result(game: Game, result: GameResult) -> None:
    print()
    if result.method == "Draw":
        print(f"Game ended in draw. {result.reason}")
        return

    winner = game.players[result.winner_index] if result.winner_index is not None else None
    print(f"{result.method}! Winner: {winner.name if winner else 'Unknown'}")
    if result.discarder_index is not None:
        print(f"Discarder: {game.players[result.discarder_index].name}")
    if result.winning_card is not None:
        print(f"Winning card: {result.winning_card.label()}")
    print(f"Winning hand: {_format_cards(result.final_hand)}")
    print(f"Win type: {format_win_types(result.win_types)}")


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    raw = input(prompt).strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def _format_cards(cards: Iterable[Card], indexed: bool = False) -> str:
    if indexed:
        return " | ".join(f"{index}: {card.label()}" for index, card in enumerate(cards))
    return " | ".join(card.label() for card in cards)
