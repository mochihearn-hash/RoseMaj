import asyncio
import unittest

from backend.room_manager import RoomManager


class FakeWebSocket:
    def __init__(self):
        self.messages = []

    async def send_json(self, data):
        self.messages.append(data)


class BackendRoomManagerTests(unittest.TestCase):
    def test_room_create_join_and_ready_start(self):
        async def scenario():
            manager = RoomManager()
            ws1 = FakeWebSocket()
            ws2 = FakeWebSocket()

            room_code, p1 = await manager.create_room(ws1, "Alice")
            joined_code, p2 = await manager.join_room(ws2, room_code, "Bob")
            await manager.toggle_ready(room_code, p1)
            await manager.toggle_ready(room_code, p2)

            room = manager.rooms[room_code]
            self.assertEqual(joined_code, room_code)
            self.assertIsNotNone(room.game)
            self.assertEqual(room.status, "playing")
            self.assertEqual(room.game.phase, "after_draw")
            self.assertIn(room.game.dealer_index, range(len(room.players)))
            self.assertEqual(len(room.game.current_player.hand), 5)
            self.assertEqual(room.game.current_player.id, room.game.dealer.id)
            self.assertTrue(any(message["type"] == "room_created" for message in ws1.messages))
            self.assertTrue(any(message["type"] == "player_joined" for message in ws1.messages))
            self.assertTrue(any(message["type"] == "game_started" for message in ws2.messages))
            self.assertTrue(any(message["type"] == "player_drawn" for message in ws1.messages))

        asyncio.run(scenario())

    def test_ai_mode_starts_immediately(self):
        async def scenario():
            manager = RoomManager()
            ws = FakeWebSocket()

            room_code, player_id = await manager.start_ai_game(ws, "Alice", ai_count=2)

            room = manager.rooms[room_code]
            self.assertEqual(len(room.players), 3)
            self.assertIsNotNone(room.game)
            self.assertEqual(room.status, "playing")
            self.assertTrue(room.is_ai_room)
            self.assertEqual(room.owner_id, player_id)
            self.assertEqual(room.game.phase, "after_draw")
            self.assertEqual(room.game.current_player.id, player_id)
            self.assertTrue(any(message["type"] == "game_started" for message in ws.messages))

        asyncio.run(scenario())

    def test_ai_room_can_restart_after_finish(self):
        async def scenario():
            manager = RoomManager()
            ws = FakeWebSocket()

            room_code, player_id = await manager.start_ai_game(ws, "Alice", ai_count=1)
            room = manager.rooms[room_code]
            room.game.phase = "finished"

            await manager.restart_game(room_code, player_id)

            self.assertEqual(room.status, "playing")
            self.assertEqual(room.game.phase, "after_draw")
            self.assertEqual(room.game.current_player.id, player_id)
            self.assertTrue(any(message["type"] == "game_started" for message in ws.messages))

        asyncio.run(scenario())

    def test_multiplayer_restart_requires_ready_and_owner(self):
        async def scenario():
            manager = RoomManager()
            ws1 = FakeWebSocket()
            ws2 = FakeWebSocket()

            room_code, p1 = await manager.create_room(ws1, "Alice")
            _, p2 = await manager.join_room(ws2, room_code, "Bob")
            await manager.toggle_ready(room_code, p1)
            await manager.toggle_ready(room_code, p2)

            room = manager.rooms[room_code]
            room.game.phase = "finished"
            manager._prepare_finished_room(room)
            self.assertFalse(room.players[0].ready)
            self.assertFalse(room.players[1].ready)

            await manager.toggle_ready(room_code, p1)
            await manager.toggle_ready(room_code, p2)
            await manager.restart_game(room_code, p1)

            self.assertEqual(room.status, "playing")
            self.assertEqual(room.game.phase, "after_draw")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
