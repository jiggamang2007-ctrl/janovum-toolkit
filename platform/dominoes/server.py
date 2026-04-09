#!/usr/bin/env python3
"""Cuban Dominoes Online - WebSocket Game Server"""

import asyncio
import json
import random
import string
import time
import os
from collections import defaultdict
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import websockets

# ─── Game Constants ───
TILES_PER_PLAYER = 10
TARGET_SCORE = 100
NUM_PLAYERS = 4

def generate_all_tiles():
    """Generate all 55 double-9 domino tiles."""
    tiles = []
    for i in range(10):
        for j in range(i, 10):
            tiles.append([i, j])
    return tiles

def generate_room_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

# ─── Game Room ───
class GameRoom:
    def __init__(self, code):
        self.code = code
        self.players = {}  # ws -> {name, team, seat, hand, connected}
        self.spectators = set()
        self.seats = [None, None, None, None]  # 4 seats
        self.state = "lobby"  # lobby, selecting, playing, round_over, game_over
        self.board = []  # list of played tiles: {tile, player, seat}
        self.left_end = None
        self.right_end = None
        self.current_turn = 0  # seat index
        self.pass_count = 0
        self.scores = [0, 0]  # team 0, team 1
        self.round_number = 0
        self.table_tiles = []  # tiles on table during selection phase
        self.selected_counts = {}  # seat -> count of tiles selected
        self.selection_order = []  # order of seat indices for picking
        self.selection_current = 0  # current picker index in selection_order
        self.round_starter = 0
        self.created_at = time.time()
        self.last_activity = time.time()
        self.animations = []

    def get_player_by_seat(self, seat):
        for ws, p in self.players.items():
            if p["seat"] == seat:
                return ws, p
        return None, None

    def all_seats_filled(self):
        return all(s is not None for s in self.seats)

    def deal_tiles(self):
        """Shuffle and lay tiles on table for selection."""
        all_tiles = generate_all_tiles()
        random.shuffle(all_tiles)
        self.table_tiles = all_tiles  # All 55 face-down on table, 15 will remain
        self.selected_counts = {i: 0 for i in range(4)}
        # Clear hands
        for ws, p in self.players.items():
            if p["seat"] is not None:
                p["hand"] = []
        self.state = "selecting"

    def current_selector(self):
        # Everyone picks freely — no turns
        return None

    def select_tile(self, seat, tile_index):
        """Player selects a tile from the table. First come first served."""
        if tile_index < 0 or tile_index >= len(self.table_tiles):
            return False, "Invalid tile"
        if self.table_tiles[tile_index] is None:
            return False, "Tile already taken"
        if self.selected_counts[seat] >= TILES_PER_PLAYER:
            return False, "You already have 10 tiles"

        tile = self.table_tiles[tile_index]
        self.table_tiles[tile_index] = None
        ws, player = self.get_player_by_seat(seat)
        if player:
            player["hand"].append(tile)
        self.selected_counts[seat] += 1

        # Check if selection is complete (all 4 players have 10)
        total_selected = sum(self.selected_counts.values())
        if total_selected >= 40:
            self.state = "playing"
            self.current_turn = self.round_starter
            self.pass_count = 0
            self.board = []
            self.left_end = None
            self.right_end = None
            return True, "selection_complete"

        return True, "ok"

    def can_play(self, seat):
        """Check if a player has any playable tile."""
        ws, player = self.get_player_by_seat(seat)
        if not player:
            return False
        if not self.board:
            return True  # first play, anything goes
        for tile in player["hand"]:
            if self.left_end in tile or self.right_end in tile:
                return True
        return False

    def play_tile(self, seat, tile, side):
        """Play a tile on the board. side = 'left' or 'right'."""
        ws, player = self.get_player_by_seat(seat)
        if not player or tile not in player["hand"]:
            return False, "Invalid tile"

        if not self.board:
            # First tile
            player["hand"].remove(tile)
            self.board.append({"tile": tile, "seat": seat, "side": "first"})
            self.left_end = tile[0]
            self.right_end = tile[1]
            self.pass_count = 0
            self._advance_turn()
            return True, "ok"

        a, b = tile
        if side == "left":
            if a == self.left_end:
                self.left_end = b
            elif b == self.left_end:
                self.left_end = a
            else:
                return False, "Tile doesn't match left end"
        elif side == "right":
            if a == self.right_end:
                self.right_end = b
            elif b == self.right_end:
                self.right_end = a
            else:
                return False, "Tile doesn't match right end"
        else:
            return False, "Invalid side"

        player["hand"].remove(tile)
        self.board.append({"tile": tile, "seat": seat, "side": side})
        self.pass_count = 0
        self._advance_turn()

        # Check if player went out
        if len(player["hand"]) == 0:
            return True, "domino"

        return True, "ok"

    def pass_turn(self, seat):
        """Player passes their turn."""
        self.pass_count += 1
        self._advance_turn()
        if self.pass_count >= 4:
            return True, "blocked"
        return True, "ok"

    def _advance_turn(self):
        """Move to next player counter-clockwise."""
        self.current_turn = (self.current_turn - 1) % 4

    def end_round(self, reason, winner_seat=None):
        """End the round and calculate scores."""
        self.state = "round_over"
        self.round_number += 1

        if reason == "domino":
            winner_team = 0 if winner_seat in [0, 2] else 1
            loser_team = 1 - winner_team
        elif reason == "blocked":
            # Count pips for each player
            team_pips = [0, 0]
            individual_pips = {}
            for ws, p in self.players.items():
                if p["seat"] is not None:
                    pips = sum(a + b for a, b in p["hand"])
                    team = 0 if p["seat"] in [0, 2] else 1
                    team_pips[team] += pips
                    individual_pips[p["seat"]] = pips

            if team_pips[0] < team_pips[1]:
                winner_team = 0
                loser_team = 1
            elif team_pips[1] < team_pips[0]:
                winner_team = 1
                loser_team = 0
            else:
                # Draw
                return {"winner_team": None, "points": 0, "reason": "draw",
                        "individual_pips": individual_pips}
        else:
            return None

        # Calculate points (losers' remaining pips)
        loser_pips = 0
        individual_pips = {}
        for ws, p in self.players.items():
            if p["seat"] is not None:
                pips = sum(a + b for a, b in p["hand"])
                individual_pips[p["seat"]] = pips
                team = 0 if p["seat"] in [0, 2] else 1
                if team == loser_team:
                    loser_pips += pips

        self.scores[winner_team] += loser_pips

        # Find who starts next round
        if reason == "domino":
            self.round_starter = winner_seat
        else:
            # Lowest individual pips starts
            min_pips = float('inf')
            for seat, pips in individual_pips.items():
                if pips < min_pips:
                    min_pips = pips
                    self.round_starter = seat

        result = {
            "winner_team": winner_team,
            "points": loser_pips,
            "reason": reason,
            "scores": list(self.scores),
            "individual_pips": individual_pips,
            "round_number": self.round_number
        }

        # Check for game over
        if self.scores[winner_team] >= TARGET_SCORE:
            self.state = "game_over"
            result["game_over"] = True

        return result

    def get_state_for_seat(self, seat):
        """Get game state visible to a specific seat."""
        other_hands = {}
        for ws, p in self.players.items():
            if p["seat"] is not None and p["seat"] != seat:
                other_hands[p["seat"]] = len(p["hand"])

        my_ws, my_player = self.get_player_by_seat(seat)
        my_hand = my_player["hand"] if my_player else []

        # Get playable tiles for current player
        playable = []
        if self.state == "playing" and self.current_turn == seat:
            for i, tile in enumerate(my_hand):
                sides = []
                if not self.board:
                    sides = ["left"]  # first tile
                else:
                    if self.left_end in tile:
                        sides.append("left")
                    if self.right_end in tile:
                        sides.append("right")
                if sides:
                    playable.append({"index": i, "tile": tile, "sides": sides})

        players_info = []
        for s in range(4):
            ws, p = self.get_player_by_seat(s)
            if p:
                players_info.append({
                    "seat": s,
                    "name": p["name"],
                    "team": p["team"],
                    "tile_count": len(p["hand"]),
                    "connected": p["connected"]
                })
            else:
                players_info.append({"seat": s, "name": None, "team": s % 2})

        return {
            "room": self.code,
            "state": self.state,
            "seat": seat,
            "my_hand": my_hand,
            "other_hands": other_hands,
            "board": self.board,
            "left_end": self.left_end,
            "right_end": self.right_end,
            "current_turn": self.current_turn,
            "scores": list(self.scores),
            "players": players_info,
            "playable": playable,
            "round_number": self.round_number,
            "table_tiles_count": len(self.table_tiles) if self.state == "selecting" else 0,
            "table_tiles_taken": [i for i, t in enumerate(self.table_tiles) if t is None] if self.state == "selecting" else [],
            "current_selector": self.current_selector() if self.state == "selecting" else None,
            "pass_count": self.pass_count,
            "target_score": TARGET_SCORE
        }


# ─── Server ───
rooms = {}
player_rooms = {}  # ws -> room_code

async def handle_message(ws, message):
    try:
        data = json.loads(message)
        action = data.get("action")

        if action == "create_room":
            code = generate_room_code()
            while code in rooms:
                code = generate_room_code()
            room = GameRoom(code)
            rooms[code] = room
            name = data.get("name", "Player")
            seat = 0
            room.seats[seat] = ws
            room.players[ws] = {
                "name": name, "team": 0, "seat": seat,
                "hand": [], "connected": True
            }
            player_rooms[ws] = code
            await ws.send(json.dumps({
                "type": "room_created",
                "room": code,
                "seat": seat,
                **room.get_state_for_seat(seat)
            }))

        elif action == "join_room":
            code = data.get("room", "").upper()
            name = data.get("name", "Player")
            if code not in rooms:
                await ws.send(json.dumps({"type": "error", "message": "Room not found"}))
                return
            room = rooms[code]
            if room.state != "lobby":
                # Check if reconnecting
                reconnected = False
                for old_ws, p in list(room.players.items()):
                    if p["name"] == name and not p["connected"]:
                        # Reconnect
                        seat = p["seat"]
                        room.players[ws] = p
                        p["connected"] = True
                        del room.players[old_ws]
                        room.seats[seat] = ws
                        player_rooms[ws] = code
                        reconnected = True
                        await ws.send(json.dumps({
                            "type": "reconnected",
                            **room.get_state_for_seat(seat)
                        }))
                        await broadcast_state(room)
                        break
                if not reconnected:
                    await ws.send(json.dumps({"type": "error", "message": "Game already in progress"}))
                return

            # Find open seat
            seat = None
            for i in range(4):
                if room.seats[i] is None:
                    seat = i
                    break
            if seat is None:
                await ws.send(json.dumps({"type": "error", "message": "Room is full"}))
                return

            room.seats[seat] = ws
            team = seat % 2  # 0,2 = team 0; 1,3 = team 1
            room.players[ws] = {
                "name": name, "team": team, "seat": seat,
                "hand": [], "connected": True
            }
            player_rooms[ws] = code
            await ws.send(json.dumps({
                "type": "joined",
                "seat": seat,
                **room.get_state_for_seat(seat)
            }))
            await broadcast_state(room)

            # Auto-start when full
            if room.all_seats_filled():
                await start_round(room)

        elif action == "add_bot":
            code = player_rooms.get(ws)
            if not code or code not in rooms:
                return
            room = rooms[code]
            if room.state != "lobby":
                return
            seat = None
            for i in range(4):
                if room.seats[i] is None:
                    seat = i
                    break
            if seat is None:
                return
            bot_names = ["Bot Carlos", "Bot Maria", "Bot Pedro"]
            bot_name = bot_names[seat - 1] if seat <= 3 else f"Bot {seat}"
            bot_ws = f"bot_{code}_{seat}"
            room.seats[seat] = bot_ws
            team = seat % 2
            room.players[bot_ws] = {
                "name": bot_name, "team": team, "seat": seat,
                "hand": [], "connected": True, "is_bot": True
            }
            await broadcast_state(room)
            if room.all_seats_filled():
                await start_round(room)

        elif action == "select_tile":
            code = player_rooms.get(ws)
            if not code or code not in rooms:
                return
            room = rooms[code]
            if room.state != "selecting":
                return
            seat = room.players[ws]["seat"]
            tile_index = data.get("tile_index")
            ok, msg = room.select_tile(seat, tile_index)
            if ok:
                if msg == "selection_complete":
                    room.state = "playing"
                    await broadcast_state(room)
                else:
                    await broadcast_state(room)
                    # Handle bot selection
                    await handle_bot_selections(room)
            else:
                await ws.send(json.dumps({"type": "error", "message": msg}))

        elif action == "play_tile":
            code = player_rooms.get(ws)
            if not code or code not in rooms:
                return
            room = rooms[code]
            if room.state != "playing" or room.current_turn != room.players[ws]["seat"]:
                await ws.send(json.dumps({"type": "error", "message": "Not your turn"}))
                return
            tile = data.get("tile")
            side = data.get("side")
            seat = room.players[ws]["seat"]
            ok, msg = room.play_tile(seat, tile, side)
            if ok:
                if msg == "domino":
                    result = room.end_round("domino", seat)
                    await broadcast_state(room)
                    await broadcast_round_result(room, result)
                else:
                    await broadcast_state(room)
                    await handle_bot_turn(room)
            else:
                await ws.send(json.dumps({"type": "error", "message": msg}))

        elif action == "pass":
            code = player_rooms.get(ws)
            if not code or code not in rooms:
                return
            room = rooms[code]
            if room.state != "playing" or room.current_turn != room.players[ws]["seat"]:
                return
            seat = room.players[ws]["seat"]
            ok, msg = room.pass_turn(seat)
            if msg == "blocked":
                result = room.end_round("blocked")
                await broadcast_state(room)
                await broadcast_round_result(room, result)
            else:
                await broadcast_state(room)
                await handle_bot_turn(room)

        elif action == "new_round":
            code = player_rooms.get(ws)
            if not code or code not in rooms:
                return
            room = rooms[code]
            if room.state in ["round_over"]:
                await start_round(room)

        elif action == "new_game":
            code = player_rooms.get(ws)
            if not code or code not in rooms:
                return
            room = rooms[code]
            room.scores = [0, 0]
            room.round_number = 0
            room.round_starter = 0
            room.state = "lobby"
            if room.all_seats_filled():
                await start_round(room)

        elif action == "ping":
            await ws.send(json.dumps({"type": "pong"}))

    except Exception as e:
        print(f"Error handling message: {e}")
        import traceback
        traceback.print_exc()
        try:
            await ws.send(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass


async def start_round(room):
    """Start a new round with tile selection."""
    room.deal_tiles()
    await broadcast_state(room)
    # If first selector is a bot, handle it
    await handle_bot_selections(room)


async def handle_bot_selections(room):
    """Bots pick tiles naturally — about 2 per second like a real person."""
    if room.state != "selecting":
        return
    # All bots pick concurrently, each grabbing one tile every 0.5s
    bot_seats = []
    for seat in range(4):
        ws, player = room.get_player_by_seat(seat)
        if player and player.get("is_bot"):
            bot_seats.append(seat)
    if not bot_seats:
        return

    while room.state == "selecting":
        picked_any = False
        for seat in bot_seats:
            if room.selected_counts.get(seat, 0) >= TILES_PER_PLAYER:
                continue
            available = [i for i, t in enumerate(room.table_tiles) if t is not None]
            if not available:
                break
            pick = random.choice(available)
            ok, msg = room.select_tile(seat, pick)
            picked_any = True
            if msg == "selection_complete":
                await broadcast_state(room)
                await handle_bot_turn(room)
                return
        if not picked_any:
            break
        await broadcast_state(room)
        await asyncio.sleep(0.5)


async def handle_bot_turn(room):
    """Handle bot playing."""
    while room.state == "playing":
        seat = room.current_turn
        ws, player = room.get_player_by_seat(seat)
        if not player or not player.get("is_bot"):
            break

        await asyncio.sleep(0.8)

        # Bot AI: find playable tiles
        if not room.board:
            # Play highest double or highest tile
            best = max(player["hand"], key=lambda t: t[0] + t[1])
            ok, msg = room.play_tile(seat, best, "left")
        else:
            playable = []
            for tile in player["hand"]:
                if room.left_end in tile:
                    playable.append((tile, "left"))
                if room.right_end in tile:
                    playable.append((tile, "right"))

            if not playable:
                ok, msg = room.pass_turn(seat)
                if msg == "blocked":
                    result = room.end_round("blocked")
                    await broadcast_state(room)
                    await broadcast_round_result(room, result)
                    return
                await broadcast_state(room)
                continue
            else:
                # Pick highest value playable tile
                best_play = max(playable, key=lambda x: x[0][0] + x[0][1])
                tile, side = best_play
                ok, msg = room.play_tile(seat, tile, side)

        if msg == "domino":
            result = room.end_round("domino", seat)
            await broadcast_state(room)
            await broadcast_round_result(room, result)
            return
        await broadcast_state(room)


async def broadcast_state(room):
    """Send updated state to all players."""
    for ws, p in list(room.players.items()):
        if isinstance(ws, str):  # bot
            continue
        if p["connected"]:
            try:
                state = room.get_state_for_seat(p["seat"])
                await ws.send(json.dumps({"type": "state", **state}))
            except:
                p["connected"] = False


async def broadcast_round_result(room, result):
    """Send round result to all players."""
    for ws, p in list(room.players.items()):
        if isinstance(ws, str):  # bot
            continue
        if p["connected"]:
            try:
                await ws.send(json.dumps({"type": "round_result", **result}))
            except:
                pass


async def handler(ws):
    """WebSocket connection handler."""
    try:
        async for message in ws:
            await handle_message(ws, message)
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        # Handle disconnect
        code = player_rooms.pop(ws, None)
        if code and code in rooms:
            room = rooms[code]
            if ws in room.players:
                room.players[ws]["connected"] = False
                await broadcast_state(room)
            # Clean up empty rooms after 30 min
            all_disconnected = all(
                not p["connected"]
                for p in room.players.values()
                if not isinstance(p.get("is_bot"), bool) or not p.get("is_bot")
            )
            if all_disconnected:
                # Schedule cleanup
                asyncio.get_event_loop().call_later(1800, lambda c=code: rooms.pop(c, None))


# ─── HTTP Server for static files ───
class DominoHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(os.path.dirname(__file__), 'static'), **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress logs

    def do_GET(self):
        if self.path == '/' or self.path == '':
            self.path = '/index.html'
        return super().do_GET()


def run_http(port=5052):
    server = HTTPServer(('0.0.0.0', port), DominoHTTPHandler)
    print(f"HTTP server on port {port}")
    server.serve_forever()


async def main():
    # Start HTTP server in thread
    http_thread = threading.Thread(target=run_http, args=(5052,), daemon=True)
    http_thread.start()

    # Start WebSocket server
    print("WebSocket server on port 5053")
    async with websockets.serve(handler, "0.0.0.0", 5053):
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())
