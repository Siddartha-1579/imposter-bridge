import asyncio
import json
import random
import socket
import uvicorn
import websockets

from backend.main import app


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


class SimulatedClient:
    def __init__(self, nickname: str, ws_url: str):
        self.nickname = nickname
        self.ws_url = ws_url
        self.ws = None
        self.player_id = None
        self.reconnect_token = None
        self.room_code = None
        self.current_state = None
        self.listen_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url)
        self.listen_task = asyncio.create_task(self._listen())

    async def _listen(self):
        try:
            async for raw in self.ws:
                data = json.loads(raw)
                msg_type = data.get("type")
                if msg_type == "auth_success":
                    self.player_id = data.get("player_id")
                    self.reconnect_token = data.get("reconnect_token")
                    self.room_code = data.get("room_code")
                elif msg_type == "state":
                    self.current_state = data.get("payload")
                elif msg_type == "ping":
                    await self.ws.send(json.dumps({"type": "pong"}))
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass

    async def send(self, action_type: str, payload: dict = None):
        msg = {"type": action_type, "payload": payload or {}}
        await self.ws.send(json.dumps(msg))

    async def disconnect(self):
        if self.listen_task:
            self.listen_task.cancel()
        if self.ws:
            await self.ws.close()
            self.ws = None

    async def wait_for_phase(self, phase: str, timeout: float = 8.0):
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            if self.current_state and self.current_state.get("phase") == phase:
                return self.current_state
            await asyncio.sleep(0.05)
        raise TimeoutError(f"{self.nickname} timed out waiting for phase {phase}. Current: {self.current_state.get('phase') if self.current_state else None}")


async def run_simulation():
    port = find_free_port()
    ws_url = f"ws://127.0.0.1:{port}/ws"

    config = uvicorn.Config(app=app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())

    # Wait for server to start
    await asyncio.sleep(0.8)

    print("==================================================")
    print("STARTING 4-CLIENT SIMULATION (5 ROUNDS + RECONNECT)")
    print("==================================================")

    # 1. Connect 4 clients
    c1 = SimulatedClient("Alice", ws_url)
    c2 = SimulatedClient("Bob", ws_url)
    c3 = SimulatedClient("Charlie", ws_url)
    c4 = SimulatedClient("Dave", ws_url)

    await c1.connect()
    await c1.send("create_room", {"nickname": c1.nickname})
    await asyncio.sleep(0.2)
    room_code = c1.room_code
    print(f"[Lobby] Alice created room: {room_code}")

    for client in [c2, c3, c4]:
        await client.connect()
        await client.send("join_room", {"room_code": room_code, "nickname": client.nickname})
        await asyncio.sleep(0.1)
        print(f"[Lobby] {client.nickname} joined room: {room_code}")

    clients = [c1, c2, c3, c4]
    await asyncio.sleep(0.3)

    assert c1.current_state["phase"] == "LOBBY"
    assert len(c1.current_state["players"]) == 4

    # 2. Host starts the game
    print("\n[Game] Alice starts the game...")
    await c1.send("start_game")

    for round_idx in range(1, 6):
        print(f"\n--- ROUND {round_idx} / 5 ---")
        await c1.wait_for_phase("CLUE")

        imposter_client = next(c for c in clients if c.current_state["my_role"] == "imposter")
        crew_clients = [c for c in clients if c.current_state["my_role"] == "crew"]

        category = c1.current_state["category"]
        secret_word = crew_clients[0].current_state["secret_word"]
        print(f"Category: {category}")
        print(f"Secret Word: {secret_word} (hidden from {imposter_client.nickname})")
        print(f"Imposter is: {imposter_client.nickname}")

        # Assert secret word privacy
        assert imposter_client.current_state["secret_word"] is None

        # Simulate disconnect and reconnect on Round 2 for Bob (c2)
        if round_idx == 2:
            print("\n[Edge Case Test] Bob is disconnecting unexpectedly...")
            bob_token = c2.reconnect_token
            await c2.disconnect()
            await asyncio.sleep(0.4)

            # Check that other clients see Bob as disconnected
            bob_snap = next(p for p in c1.current_state["players"] if p["nickname"] == "Bob")
            assert bob_snap["is_connected"] is False
            print("[Edge Case Test] Server marked Bob as disconnected.")

            print("[Edge Case Test] Bob is reconnecting via token...")
            c2 = SimulatedClient("Bob", ws_url)
            await c2.connect()
            await c2.send("rejoin", {"room_code": room_code, "reconnect_token": bob_token})
            await asyncio.sleep(0.4)

            # Check Bob re-established
            bob_snap = next(p for p in c1.current_state["players"] if p["nickname"] == "Bob")
            assert bob_snap["is_connected"] is True
            print("[Edge Case Test] Bob successfully reconnected to same seat!\n")
            clients = [c1, c2, c3, c4]

        # Clue Phase: turn by turn
        turn_order = c1.current_state["turn_order"]
        for pid in turn_order:
            curr_client = next(c for c in clients if c.player_id == pid)
            if curr_client.player_id == imposter_client.player_id:
                clue = random.choice(["Mystery", "Shadow", "Strange", "Vague", "Unknown"])
            else:
                clue = f"Hint{random.randint(10, 99)}"

            await curr_client.send("submit_clue", {"clue": clue})
            await asyncio.sleep(0.15)
            print(f"  Clue by {curr_client.nickname}: {clue}")

        # Vote Phase
        await c1.wait_for_phase("VOTE")
        print("All clues in! Voting phase started.")

        if round_idx == 2:
            # Round 2: Simulate a TIE to test tie breaking (2 votes vs 2 votes)
            # Imposter + crew[0] vote for crew[1]
            # crew[1] + crew[2] vote for imposter
            for c in clients:
                if c.player_id in [imposter_client.player_id, crew_clients[0].player_id]:
                    target = crew_clients[1].player_id
                else:
                    target = imposter_client.player_id
                await c.send("submit_vote", {"target_id": target})
                await asyncio.sleep(0.05)
        else:
            # Other rounds: All 3 crew vote for imposter -> Imposter caught!
            for c in clients:
                if c.player_id == imposter_client.player_id:
                    target = crew_clients[0].player_id
                else:
                    target = imposter_client.player_id
                await c.send("submit_vote", {"target_id": target})
                await asyncio.sleep(0.05)

        # Reveal Phase
        await c1.wait_for_phase("REVEAL")
        print("Reveal Phase: Votes revealed!")
        state = c1.current_state
        print(f"  Imposter caught: {state['imposter_caught']}")

        if state["imposter_caught"]:
            # Assert imposter client does not have secret word while awaiting guess
            assert imposter_client.current_state["secret_word"] is None

            # Round 1 & 4: Imposter guesses correctly; Round 3 & 5: Imposter guesses wrong
            guess = secret_word if round_idx in [1, 4] else "WrongGuess"
            print(f"  Imposter {imposter_client.nickname} guesses: '{guess}'")
            await imposter_client.send("submit_guess", {"guess": guess})
            await asyncio.sleep(0.2)

        # Advance from Reveal to Scoreboard
        await c1.send("next_round")
        await c1.wait_for_phase("SCOREBOARD")
        state = c1.current_state
        print(f"Scoreboard Round {round_idx} Points Awarded:")
        for p in state["players"]:
            pts = state["round_points"].get(p["id"], 0)
            print(f"  {p['nickname']}: +{pts} pts (Total: {p['score']})")

        # Advance to next round
        if round_idx < 5:
            await c1.send("next_round")
            await asyncio.sleep(0.2)

    # Game Over
    await c1.wait_for_phase("GAME_OVER")
    print("\n==================================================")
    print("GAME OVER - FINAL LEADERBOARD")
    print("==================================================")
    final_players = sorted(c1.current_state["players"], key=lambda p: p["score"], reverse=True)
    for rank, p in enumerate(final_players, 1):
        crown = " [WINNER!]" if rank == 1 else ""
        print(f"  #{rank} {p['nickname']}: {p['score']} pts{crown}")
    print("==================================================")

    # Clean up
    for c in clients:
        await c.disconnect()
    server.should_exit = True
    await server_task
    print("Simulation finished successfully!")


if __name__ == "__main__":
    asyncio.run(run_simulation())
