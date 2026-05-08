import unittest

from backend.game_logic import LastDiscard, OnlineGame
from backend.models import PlayerSeat
from roselia_mahjong.cards import Card


def make_players(count=2):
    return [PlayerSeat(id=f"p{index}", nickname=f"P{index}") for index in range(count)]


class BackendGameLogicTests(unittest.TestCase):
    def test_riichi_options_after_draw(self):
        players = make_players()
        game = OnlineGame(players)
        game.phase = "after_draw"
        players[0].hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.normal("Yukina", "Green"),
        ]

        options = game.riichi_options("p0")
        self.assertIn(4, options)
        self.assertIn(Card.normal("Rinko", "Red"), options[4])

    def test_declare_riichi_discards_and_locks_remaining_hand(self):
        players = make_players()
        game = OnlineGame(players)
        game.phase = "after_draw"
        players[0].hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.normal("Yukina", "Green"),
        ]

        discarded, waits = game.declare_riichi("p0", 4)

        self.assertEqual(discarded, Card.normal("Yukina", "Green"))
        self.assertTrue(players[0].riichi)
        self.assertEqual(tuple(players[0].hand), players[0].locked_hand)
        self.assertIn(Card.normal("Rinko", "Blue"), waits)

    def test_tsumo_requires_riichi(self):
        players = make_players()
        game = OnlineGame(players)
        game.phase = "after_draw"
        players[0].hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.normal("Rinko", "Green"),
        ]

        self.assertFalse(game.can_tsumo("p0"))

        players[0].riichi = True
        players[0].riichi_waits = {Card.normal("Rinko", "Green")}
        self.assertTrue(game.can_tsumo("p0"))
        result = game.claim_tsumo("p0")
        self.assertEqual(result.method, "Tsumo")

    def test_ron_uses_last_discard(self):
        players = make_players()
        game = OnlineGame(players)
        game.phase = "need_draw"
        players[0].hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
        ]
        players[0].riichi = True
        players[0].riichi_waits = {Card.normal("Rinko", "Blue")}
        game.last_discard = LastDiscard("p1", Card.normal("Rinko", "Blue"))

        self.assertTrue(game.can_ron("p0"))
        result = game.claim_ron("p0")
        self.assertEqual(result.method, "Ron")
        self.assertEqual(result.discarder_id, "p1")


if __name__ == "__main__":
    unittest.main()
