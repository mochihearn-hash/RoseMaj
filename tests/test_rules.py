import unittest

from roselia_mahjong.cards import COLORS, Card
from roselia_mahjong.deck import build_full_deck
from roselia_mahjong.rules import WinType, evaluate_hand, riichi_discard_options, winning_waits


class RuleTests(unittest.TestCase):
    def test_full_deck_has_expected_size(self):
        deck = build_full_deck()
        self.assertEqual(len(deck), 85)

        voice_actor_cards = [card for card in deck if card.is_voice_actor]
        normal_cards = [card for card in deck if not card.is_voice_actor]
        self.assertEqual(len(voice_actor_cards), 5)
        self.assertEqual(len(normal_cards), 80)

    def test_voice_actor_counts_as_same_character(self):
        hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Yukina", "Orange"),
            Card.normal("Yukina", "Green"),
            Card.normal("Yukina", "Blue"),
            Card.voice_actor_card("Aiba Aina"),
        ]

        result = evaluate_hand(hand)
        self.assertIn(WinType.SAME_CHARACTER, result.types)

    def test_voice_actor_can_match_any_color(self):
        hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Red"),
            Card.normal("Lisa", "Red"),
            Card.normal("Ako", "Red"),
            Card.voice_actor_card("Aiba Aina"),
        ]

        result = evaluate_hand(hand)
        self.assertIn(WinType.SAME_COLOR, result.types)

    def test_roselia_complete_counts_voice_actor_as_own_character(self):
        hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.voice_actor_card("Shizaki Kanon"),
        ]

        result = evaluate_hand(hand)
        self.assertIn(WinType.ROSELIA_COMPLETE, result.types)

    def test_voice_actor_does_not_become_other_character_for_complete(self):
        hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.voice_actor_card("Aiba Aina"),
        ]

        result = evaluate_hand(hand)
        self.assertNotIn(WinType.ROSELIA_COMPLETE, result.types)

    def test_tenpai_waits_for_missing_rinko(self):
        hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
        ]

        waits = winning_waits(hand)
        for color in COLORS:
            self.assertIn(Card.normal("Rinko", color), waits)
        self.assertIn(Card.voice_actor_card("Shizaki Kanon"), waits)
        self.assertNotIn(Card.voice_actor_card("Aiba Aina"), waits)

    def test_riichi_options_are_checked_after_draw(self):
        hand = [
            Card.normal("Yukina", "Red"),
            Card.normal("Sayo", "Orange"),
            Card.normal("Lisa", "Green"),
            Card.normal("Ako", "Blue"),
            Card.normal("Yukina", "Green"),
        ]

        options = riichi_discard_options(hand)
        self.assertIn(4, options)
        self.assertIn(Card.normal("Rinko", "Red"), options[4])


if __name__ == "__main__":
    unittest.main()
