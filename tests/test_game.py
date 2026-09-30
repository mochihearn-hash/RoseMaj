import contextlib
import io
import unittest

from roselia_mahjong import cli
from roselia_mahjong.cards import Card
from roselia_mahjong.deck import Deck
from roselia_mahjong.game import (
    MAX_PLAYERS,
    MIN_PLAYERS,
    Game,
    InvalidAction,
    build_player_names,
)


class GameTests(unittest.TestCase):
    def test_riichi_locks_hand_and_forces_draw_discard(self):
        game = Game(["A", "B"], human_index=None, deck=Deck.from_draw_order([]))
        player = game.players[0]
        player.hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.normal("Yukina", "Green"),
        ]

        discarded, waits = game.declare_riichi_and_discard(0, 4)
        self.assertEqual(discarded, Card.normal("Yukina", "Green"))
        self.assertIn(Card.normal("Rinko", "Red"), waits)
        self.assertEqual(tuple(player.hand), player.locked_hand)

        player.draw(Card.normal("Yukina", "Green"))
        with self.assertRaises(InvalidAction):
            game.discard_current_player(0)

        discarded = game.discard_current_player(4)
        self.assertEqual(discarded, Card.normal("Yukina", "Green"))
        self.assertEqual(tuple(player.hand), player.locked_hand)

    def test_ron_candidate_after_riichi(self):
        game = Game(["A", "B"], human_index=None)
        game.players[0].hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.normal("Yukina", "Green"),
        ]
        game.declare_riichi_and_discard(0, 4)

        discarded = Card.normal("Rinko", "Blue")
        candidates = game.ron_candidates(discarder_index=1, discarded_card=discarded)
        self.assertEqual(candidates, [0])

        result = game.finish_ron(0, 1, discarded)
        self.assertEqual(result.method, "Ron")
        self.assertEqual(result.winner_index, 0)

    def test_tsumo_requires_riichi(self):
        game = Game(["A", "B"], human_index=None)
        game.players[0].hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.normal("Rinko", "Green"),
        ]

        self.assertFalse(game.can_tsumo(0))

    def test_riichi_requires_five_cards_after_draw(self):
        game = Game(["A", "B"], human_index=None)
        game.players[0].hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
        ]

        with self.assertRaises(InvalidAction):
            game.declare_riichi_and_discard(0, 0)

    def test_setup_randomizes_dealer_and_starts_from_dealer(self):
        starts = set()
        for seed in range(200):
            game = Game(["A", "B", "C", "D"], human_index=None, seed=seed)
            game.setup()
            self.assertEqual(game.dealer_index, game.current_player_index)
            self.assertIs(game.dealer, game.current_player)
            starts.add(game.dealer_index)

        # Every seat must be able to become the dealer, otherwise the first
        # seats keep acting first and win far more often than the others.
        self.assertEqual(starts, {0, 1, 2, 3})

    def test_setup_deals_four_cards_and_leaves_rest_in_deck(self):
        game = Game(["A", "B", "C", "D"], human_index=None, seed=1)
        game.setup()

        for player in game.players:
            self.assertEqual(len(player.hand), 4)
        self.assertEqual(game.deck.remaining(), 85 - 16)

    def test_supports_every_player_count_in_range(self):
        for count in range(MIN_PLAYERS, MAX_PLAYERS + 1):
            with self.subTest(players=count):
                names = [f"P{index}" for index in range(count)]
                game = Game(names, human_index=None, seed=1)
                game.setup()

                self.assertEqual(len(game.players), count)
                for player in game.players:
                    self.assertEqual(len(player.hand), 4)
                self.assertEqual(game.deck.remaining(), 85 - 4 * count)

    def test_rejects_player_counts_outside_range(self):
        with self.assertRaises(ValueError):
            Game(["only-one"], human_index=None)

        too_many = [f"P{index}" for index in range(MAX_PLAYERS + 1)]
        with self.assertRaises(ValueError):
            Game(too_many, human_index=None)

    def test_build_player_names_gives_one_name_per_seat(self):
        for count in range(MIN_PLAYERS, MAX_PLAYERS + 1):
            ai_only = build_player_names(count, ai_only=True)
            self.assertEqual(len(ai_only), count)
            self.assertEqual(len(set(ai_only)), count, "座位名不能重复")

            with_human = build_player_names(count, human_name="Alice", ai_only=False)
            self.assertEqual(len(with_human), count)
            self.assertEqual(with_human[0], "Alice")
            self.assertNotIn("Alice", with_human[1:])

    def test_build_player_names_rejects_bad_counts(self):
        with self.assertRaises(ValueError):
            build_player_names(MIN_PLAYERS - 1)
        with self.assertRaises(ValueError):
            build_player_names(MAX_PLAYERS + 1)

    def test_cli_plays_a_five_player_ai_game(self):
        """5 人局要能真的打完并产出结果，而不是崩溃或卡住。"""

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cli.main(["--players", "5", "--ai-only", "--seed", "7"])

        self.assertEqual(exit_code, 0)
        output = buffer.getvalue()
        # 第 5 个座位以前不存在（名单里只有 4 个），必须真的出现在输出里
        self.assertIn("AI-Yukina", output)
        self.assertRegex(output, r"(Tsumo|Ron)! Winner:|Game ended in draw")

    def test_cli_rejects_six_players(self):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = cli.main(["--players", "6", "--ai-only", "--seed", "7"])

        self.assertEqual(exit_code, 2)
        self.assertIn("between", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
