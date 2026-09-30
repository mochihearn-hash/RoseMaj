import unittest

from roselia_mahjong.cards import Card
from roselia_mahjong.deck import Deck
from roselia_mahjong.game import Game, InvalidAction


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


if __name__ == "__main__":
    unittest.main()
