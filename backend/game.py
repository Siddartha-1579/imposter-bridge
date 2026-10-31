import asyncio
import random
import secrets
import time
import uuid
from typing import Optional
from fastapi import WebSocket

from backend.words import WORDS_DATABASE
from backend.models import (
    PersonalizedState,
    PlayerSnapshot,
    ClueEntry,
    StateMessage,
    ErrorMessage,
    ToastMessage,
)

ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # Uppercase letters, no I or O


def _cancel(task: Optional[asyncio.Task]):
    """Safely cancels an asyncio task without self-cancelling the current task."""
    if task and not task.done() and task is not asyncio.current_task():
        task.cancel()


class Player:
    def __init__(self, nickname: str, is_host: bool = False, is_spectator: bool = False):
        self.id: str = uuid.uuid4().hex[:8]
        self.reconnect_token: str = secrets.token_urlsafe(24)
        self.nickname: str = nickname.strip()
        self.score: int = 0
        self.is_host: bool = is_host
        self.is_connected: bool = True
        self.is_spectator: bool = is_spectator
        self.joined_at: float = time.time()
        self.disconnected_at: Optional[float] = None
        self.imposter_count: int = 0
        self.ws: Optional[WebSocket] = None

    def to_snapshot(self, is_turn: bool, has_voted: bool, reveal_imposter: bool, imposter_id: Optional[str]) -> PlayerSnapshot:
        return PlayerSnapshot(
            id=self.id,
            nickname=self.nickname,
            score=self.score,
            is_host=self.is_host,
            is_connected=self.is_connected,
            is_turn=is_turn,
            has_voted=has_voted,
            is_imposter=(self.id == imposter_id) if reveal_imposter else None,
            is_spectator=self.is_spectator,
        )


class Room:
    def __init__(self, room_code: str):
        self.room_code: str = room_code
        self.players: dict[str, Player] = {}  # player_id -> Player
        self.token_to_id: dict[str, str] = {}  # reconnect_token -> player_id
        self.phase: str = "LOBBY"  # LOBBY, CLUE, VOTE, REVEAL, SCOREBOARD, GAME_OVER
        self.round_num: int = 0
        self.total_rounds: int = 5
        self.category: Optional[str] = None
        self.secret_word: Optional[str] = None
        self.imposter_id: Optional[str] = None

        self.turn_order: list[str] = []
        self.turn_index: int = 0
        self.clues: list[ClueEntry] = []
        self.votes: dict[str, str] = {}  # voter_id -> target_id

        self.imposter_caught: Optional[bool] = None
        self.imposter_guess: Optional[str] = None
        self.guess_result: Optional[bool] = None
        self.round_points: dict[str, int] = {}

        self.is_paused: bool = False
        self.deadline_ms: Optional[int] = None
        self.remaining_timer_s: Optional[float] = None
        self.active_timer_phase: Optional[str] = None
        self.timer_task: Optional[asyncio.Task] = None
        self.host_transfer_task: Optional[asyncio.Task] = None

        self.last_activity: float = time.time()
        self.lock = asyncio.Lock()

    def get_connected_count(self) -> int:
        return sum(1 for p in self.players.values() if p.is_connected)

    def get_active_players(self) -> list[Player]:
        return [p for p in self.players.values() if not p.is_spectator]

    def reset_timer(self):
        """Resets the phase countdown timer. Does NOT cancel host_transfer_task."""
        _cancel(self.timer_task)
        self.timer_task = None
        self.deadline_ms = None
        self.remaining_timer_s = None
        self.active_timer_phase = None

    async def broadcast_state(self):
        """Sends a personalized state snapshot to every connected player."""
        now_ms = int(time.time() * 1000)
        reveal_info = self.phase in ["REVEAL", "SCOREBOARD", "GAME_OVER"]

        # Imposter must NOT receive secret_word while awaiting their guess
        awaiting_guess = (
            self.phase == "REVEAL"
            and self.imposter_caught
            and self.imposter_guess is None
        )

        current_turn_id = (
            self.turn_order[self.turn_index]
            if self.phase == "CLUE" and 0 <= self.turn_index < len(self.turn_order)
            else None
        )

        for player in list(self.players.values()):
            if not player.is_connected or not player.ws:
                continue

            # Role determination
            if player.is_spectator:
                role = "spectator"
            elif player.id == self.imposter_id:
                role = "imposter"
            else:
                role = "crew"

            # Secret word and imposter privacy
            if reveal_info:
                imposter_id = self.imposter_id
                if role == "imposter" and awaiting_guess:
                    secret_word = None
                else:
                    secret_word = self.secret_word
            else:
                imposter_id = None
                if role == "crew":
                    secret_word = self.secret_word
                else:
                    secret_word = None

            # Votes map privacy: hidden until reveal
            votes_snapshot = self.votes if reveal_info else None

            # Player snapshots
            snapshots = [
                p.to_snapshot(
                    is_turn=(p.id == current_turn_id),
                    has_voted=(p.id in self.votes),
                    reveal_imposter=reveal_info,
                    imposter_id=self.imposter_id,
                )
                for p in self.players.values()
            ]

            state = PersonalizedState(
                room_code=self.room_code,
                phase=self.phase,
                round_num=self.round_num,
                total_rounds=self.total_rounds,
                server_time_ms=now_ms,
                deadline_ms=self.deadline_ms,
                is_paused=self.is_paused,
                my_id=player.id,
                is_host=player.is_host,
                my_role=role,
                category=self.category,
                secret_word=secret_word,
                players=snapshots,
                turn_order=self.turn_order,
                current_turn_player_id=current_turn_id,
                clues=self.clues,
                votes=votes_snapshot,
                imposter_id=imposter_id,
                imposter_caught=self.imposter_caught if reveal_info else None,
                imposter_guess=self.imposter_guess if reveal_info else None,
                guess_result=self.guess_result if reveal_info else None,
                round_points=self.round_points if reveal_info else None,
            )

            try:
                await player.ws.send_text(StateMessage(payload=state).model_dump_json())
            except Exception:
                pass

    async def broadcast_toast(self, message: str, level: str = "info"):
        toast = ToastMessage(message=message, level=level).model_dump_json()
        for p in list(self.players.values()):
            if p.is_connected and p.ws:
                try:
                    await p.ws.send_text(toast)
                except Exception:
                    pass

    async def send_error(self, player: Player, message: str):
        if player.is_connected and player.ws:
            try:
                await player.ws.send_text(ErrorMessage(message=message).model_dump_json())
            except Exception:
                pass

    # --- Phase Transitions & Logic ---

    async def check_pause_or_resume(self):
        """Cancels timers and pauses if connected players < 3 mid-game; resumes when 3+."""
        if self.phase in ["LOBBY", "GAME_OVER"]:
            self.is_paused = False
            return

        connected = self.get_connected_count()
        if connected < 3 and not self.is_paused:
            self.is_paused = True
            if self.deadline_ms:
                remaining_ms = max(1000, self.deadline_ms - int(time.time() * 1000))
                self.remaining_timer_s = remaining_ms / 1000.0
            else:
                self.remaining_timer_s = None

            _cancel(self.timer_task)
            self.timer_task = None
            self.deadline_ms = None
            await self.broadcast_toast("Game paused: Waiting for players to reconnect...", "warning")
            await self.broadcast_state()

        elif connected >= 3 and self.is_paused:
            self.is_paused = False
            duration = self.remaining_timer_s or 15.0
            self.remaining_timer_s = None
            await self.broadcast_toast("Players returned! Resuming game.", "success")
            self.start_timer(duration, self.active_timer_phase)
            await self.broadcast_state()

    def start_timer(self, duration_s: float, phase_name: Optional[str] = None):
        _cancel(self.timer_task)
        self.active_timer_phase = phase_name or self.phase
        self.deadline_ms = int(time.time() * 1000) + int(duration_s * 1000)

        async def timer_coro():
            try:
                await asyncio.sleep(duration_s)
                async with self.lock:
                    await self.on_timer_expired()
            except asyncio.CancelledError:
                pass

        self.timer_task = asyncio.create_task(timer_coro())

    async def on_timer_expired(self):
        if self.is_paused:
            return

        if self.phase == "CLUE":
            # Auto-skip current turn with '(no clue)'
            if 0 <= self.turn_index < len(self.turn_order):
                pid = self.turn_order[self.turn_index]
                player = self.players.get(pid)
                nickname = player.nickname if player else "Unknown"
                self.clues.append(ClueEntry(player_id=pid, nickname=nickname, clue="(no clue)"))
            await self.advance_clue_turn()

        elif self.phase == "VOTE":
            # Voting deadline expired -> tally votes and transition to reveal
            await self.finish_voting()

        elif self.phase == "REVEAL":
            # Imposter guess deadline expired -> wrong guess
            if self.imposter_caught and self.imposter_guess is None:
                self.imposter_guess = "(timed out)"
                self.guess_result = False
                await self.apply_scoring()
            await self.transition_to_scoreboard()

        elif self.phase == "SCOREBOARD":
            # 5s timer expired -> advance to next round
            await self.advance_round()

    # --- Start Game & Round Assignment ---

    async def start_game(self, player: Player):
        if self.phase != "LOBBY":
            await self.send_error(player, "Game has already started.")
            return
        if not player.is_host:
            await self.send_error(player, "Only the host can start the game.")
            return
        connected_count = self.get_connected_count()
        if connected_count < 3:
            await self.send_error(player, "Need at least 3 connected players to start.")
            return
        if len(self.players) > 8:
            await self.send_error(player, "Maximum 8 players allowed.")
            return

        # Reset scores and status
        for p in self.players.values():
            p.score = 0
            p.is_spectator = False
            p.imposter_count = 0

        self.round_num = 0
        await self.start_new_round()

    async def start_new_round(self):
        self.round_num += 1
        self.phase = "CLUE"
        self.clues = []
        self.votes = {}
        self.imposter_caught = None
        self.imposter_guess = None
        self.guess_result = None
        self.round_points = {}

        # Spectators from previous rounds become regular players
        for p in self.players.values():
            p.is_spectator = False

        active_players = self.get_active_players()

        # Category and word selection
        self.category = random.choice(list(WORDS_DATABASE.keys()))
        self.secret_word = random.choice(WORDS_DATABASE[self.category])

        # Imposter rotation: pick randomly among players with lowest imposter count
        min_count = min(p.imposter_count for p in active_players)
        candidates = [p for p in active_players if p.imposter_count == min_count]
        imposter = random.choice(candidates)
        self.imposter_id = imposter.id
        imposter.imposter_count += 1

        # Turn order: random shuffle of all active players
        self.turn_order = [p.id for p in active_players]
        random.shuffle(self.turn_order)
        self.turn_index = 0

        await self.setup_current_turn_timer()
        await self.broadcast_state()

    async def setup_current_turn_timer(self):
        if not (0 <= self.turn_index < len(self.turn_order)):
            return
        current_pid = self.turn_order[self.turn_index]
        player = self.players.get(current_pid)

        # 5 seconds if disconnected, 30 seconds if connected
        duration = 5.0 if (not player or not player.is_connected) else 30.0
        self.start_timer(duration, "CLUE")

    async def submit_clue(self, player: Player, clue: str):
        if self.phase != "CLUE":
            await self.send_error(player, "Not in clue phase.")
            return
        if self.is_paused:
            await self.send_error(player, "Game is currently paused.")
            return
        if self.turn_order[self.turn_index] != player.id:
            await self.send_error(player, "It is not your turn.")
            return

        clue_cleaned = clue.strip()
        # Validation: single word, max 20 chars
        if not clue_cleaned or len(clue_cleaned.split()) > 1 or len(clue_cleaned) > 20:
            await self.send_error(player, "Clue must be a single word (max 20 characters).")
            return

        # Crew only: cannot be secret word. Imposter can say anything.
        if player.id != self.imposter_id:
            if clue_cleaned.lower() == (self.secret_word or "").lower():
                await self.send_error(player, "Clue cannot be the secret word!")
                return

        self.clues.append(ClueEntry(player_id=player.id, nickname=player.nickname, clue=clue_cleaned))
        await self.advance_clue_turn()

    async def advance_clue_turn(self):
        self.turn_index += 1
        if self.turn_index < len(self.turn_order):
            await self.setup_current_turn_timer()
            await self.broadcast_state()
        else:
            # Clues finished -> transition to VOTE phase
            await self.start_voting()

    # --- Voting Phase ---

    async def start_voting(self):
        self.phase = "VOTE"
        self.votes = {}
        # 45s timer for voting
        self.start_timer(45.0, "VOTE")
        await self.broadcast_state()

    async def submit_vote(self, voter: Player, target_id: str):
        if self.phase != "VOTE":
            await self.send_error(voter, "Not in vote phase.")
            return
        if self.is_paused:
            await self.send_error(voter, "Game is paused.")
            return
        if voter.is_spectator:
            await self.send_error(voter, "Spectators cannot vote.")
            return
        if voter.id == target_id:
            await self.send_error(voter, "You cannot vote for yourself.")
            return
        if target_id not in self.players or self.players[target_id].is_spectator:
            await self.send_error(voter, "Invalid player selected.")
            return

        self.votes[voter.id] = target_id

        # Check if all connected non-spectator players have voted
        active_connected = [p for p in self.get_active_players() if p.is_connected]
        all_voted = all(p.id in self.votes for p in active_connected)

        if all_voted:
            await self.finish_voting()
        else:
            await self.broadcast_state()

    async def finish_voting(self):
        self.phase = "REVEAL"
        self.reset_timer()

        # Vote tallying:
        # Disconnected active players count as abstain (no vote entry).
        tally: dict[str, int] = {p.id: 0 for p in self.get_active_players()}
        for voter_id, target_id in self.votes.items():
            if target_id in tally:
                tally[target_id] += 1

        max_votes = max(tally.values()) if tally else 0
        top_candidates = [pid for pid, count in tally.items() if count == max_votes]

        # Tie in votes = Imposter NOT caught
        if max_votes > 0 and len(top_candidates) == 1 and top_candidates[0] == self.imposter_id:
            self.imposter_caught = True
        else:
            self.imposter_caught = False

        imposter_player = self.players.get(self.imposter_id)

        # If imposter is caught:
        # If imposter is disconnected at reveal -> skip their guess.
        if self.imposter_caught:
            if not imposter_player or not imposter_player.is_connected:
                self.imposter_guess = "(disconnected - skipped)"
                self.guess_result = False
                await self.apply_scoring()
                self.start_timer(5.0, "REVEAL")
                await self.broadcast_state()
            else:
                # 20 seconds for Imposter to guess
                self.start_timer(20.0, "REVEAL")
                await self.broadcast_state()
        else:
            # Imposter not caught -> immediate scoring and 5s reveal display
            await self.apply_scoring()
            self.start_timer(5.0, "REVEAL")
            await self.broadcast_state()

    async def submit_guess(self, player: Player, guess: str):
        if self.phase != "REVEAL" or not self.imposter_caught:
            await self.send_error(player, "Not in guess phase.")
            return
        if player.id != self.imposter_id:
            await self.send_error(player, "Only the Imposter can guess.")
            return
        if self.imposter_guess is not None:
            await self.send_error(player, "Guess already submitted.")
            return

        guess_clean = guess.strip()
        self.imposter_guess = guess_clean
        # Case-insensitive match
        self.guess_result = (guess_clean.lower() == (self.secret_word or "").lower())

        self.reset_timer()
        await self.apply_scoring()
        await self.transition_to_scoreboard()

    async def apply_scoring(self):
        """
        Scoring Rules:
        - Imposter not caught: Imposter +3.
        - Imposter caught but guesses the word correctly: Imposter +2.
        - Imposter caught and guesses wrong: every crew member who voted for the Imposter +2, other crew +1.
        """
        self.round_points = {p.id: 0 for p in self.players.values()}

        if not self.imposter_caught:
            # Imposter escaped
            if self.imposter_id in self.round_points:
                self.round_points[self.imposter_id] = 3
        else:
            # Imposter caught
            if self.guess_result is True:
                # Guessed correctly
                if self.imposter_id in self.round_points:
                    self.round_points[self.imposter_id] = 2
            else:
                # Guessed wrong / timed out / skipped
                if self.imposter_id in self.round_points:
                    self.round_points[self.imposter_id] = 0
                for p in self.get_active_players():
                    if p.id != self.imposter_id:
                        if self.votes.get(p.id) == self.imposter_id:
                            self.round_points[p.id] = 2
                        else:
                            self.round_points[p.id] = 1

        # Apply points to player scores
        for pid, pts in self.round_points.items():
            if pid in self.players:
                self.players[pid].score += pts

    async def transition_to_scoreboard(self):
        self.phase = "SCOREBOARD"
        # 5-second timer or host taps 'Next'
        self.start_timer(5.0, "SCOREBOARD")
        await self.broadcast_state()

    async def advance_round(self):
        self.reset_timer()
        if self.round_num >= self.total_rounds:
            self.phase = "GAME_OVER"
            await self.broadcast_state()
        else:
            await self.start_new_round()

    async def play_again(self, player: Player):
        if self.phase != "GAME_OVER":
            await self.send_error(player, "Game is not over yet.")
            return
        if not player.is_host:
            await self.send_error(player, "Only the host can restart the game.")
            return
        # Reset scores, retain room and players
        for p in self.players.values():
            p.score = 0
            p.imposter_count = 0
            p.is_spectator = False
        self.phase = "LOBBY"
        self.round_num = 0
        self.reset_timer()
        await self.broadcast_toast("Game reset! Ready for a new game in Lobby.", "info")
        await self.broadcast_state()

    # --- Connection & Host Management ---

    async def handle_disconnect(self, player: Player, ws: Optional[WebSocket] = None):
        # Stale socket check: if ws is provided and does not match player's current ws, return immediately
        if ws is not None and player.ws is not ws:
            return

        player.is_connected = False
        player.disconnected_at = time.time()
        player.ws = None

        # In LOBBY phase: completely remove player and free nickname/token
        if self.phase == "LOBBY":
            self.players.pop(player.id, None)
            self.token_to_id.pop(player.reconnect_token, None)
            await self.broadcast_toast(f"{player.nickname} left the room.", "info")

            # Transfer host immediately if host left during lobby
            if player.is_host:
                remaining = sorted(
                    [p for p in self.players.values() if p.is_connected],
                    key=lambda p: p.joined_at
                )
                if remaining:
                    remaining[0].is_host = True
                    await self.broadcast_toast(f"Host transferred to {remaining[0].nickname}.", "info")

            await self.broadcast_state()
            return

        # Mid-game disconnect handling:
        await self.broadcast_toast(f"{player.nickname} disconnected.", "warning")

        # If it was their turn in clue phase, skip after 5 seconds if still disconnected
        if self.phase == "CLUE" and 0 <= self.turn_index < len(self.turn_order):
            if self.turn_order[self.turn_index] == player.id:
                self.start_timer(5.0, "CLUE")

        # Check pause if connected players < 3
        await self.check_pause_or_resume()

        # If host disconnected mid-game, schedule transfer in 15 seconds
        if player.is_host:
            _cancel(self.host_transfer_task)

            async def transfer_coro():
                try:
                    await asyncio.sleep(15.0)
                    async with self.lock:
                        await self.check_host_transfer(player.id)
                except asyncio.CancelledError:
                    pass

            self.host_transfer_task = asyncio.create_task(transfer_coro())

        await self.broadcast_state()

    async def check_host_transfer(self, disconnected_host_id: str):
        host = self.players.get(disconnected_host_id)
        if host and not host.is_connected:
            # Transfer to oldest connected player
            connected_players = sorted(
                [p for p in self.players.values() if p.is_connected],
                key=lambda p: p.joined_at
            )
            if connected_players:
                new_host = connected_players[0]
                host.is_host = False
                new_host.is_host = True
                await self.broadcast_toast(f"Host transferred to {new_host.nickname}.", "info")
                await self.broadcast_state()

    async def handle_reconnect(self, player: Player, ws: WebSocket):
        player.is_connected = True
        player.disconnected_at = None
        player.ws = ws

        # Cancel host transfer if this player was the host
        if player.is_host:
            _cancel(self.host_transfer_task)
            self.host_transfer_task = None

        await self.broadcast_toast(f"{player.nickname} reconnected!", "success")
        await self.check_pause_or_resume()
        await self.broadcast_state()


class GameManager:
    def __init__(self):
        self.rooms: dict[str, Room] = {}
        self.lock = asyncio.Lock()

    def generate_room_code(self) -> str:
        for _ in range(1000):
            code = "".join(random.choices(ROOM_CODE_CHARS, k=4))
            if code not in self.rooms:
                return code
        raise RuntimeError("Failed to generate unique room code")

    async def create_room(self, nickname: str, ws: WebSocket) -> tuple[Room, Player]:
        async with self.lock:
            code = self.generate_room_code()
            room = Room(code)
            player = Player(nickname=nickname, is_host=True)
            player.ws = ws
            room.players[player.id] = player
            room.token_to_id[player.reconnect_token] = player.id
            self.rooms[code] = room
            return room, player

    async def join_room(self, room_code: str, nickname: str, ws: WebSocket) -> tuple[Optional[Room], Optional[Player], Optional[str]]:
        async with self.lock:
            code = room_code.upper().strip()
            room = self.rooms.get(code)
            if not room:
                return None, None, "Room code not found."

            async with room.lock:
                if len(room.players) >= 8:
                    return None, None, "Room is full (maximum 8 players)."

                nickname_clean = nickname.strip()
                if not (1 <= len(nickname_clean) <= 12):
                    return None, None, "Nickname must be between 1 and 12 characters."

                # Unique nickname check
                for p in room.players.values():
                    if p.nickname.lower() == nickname_clean.lower():
                        return None, None, "Nickname already taken in this room."

                # Late joiners become spectators until next round
                is_spectator = (room.phase != "LOBBY")
                player = Player(nickname=nickname_clean, is_host=False, is_spectator=is_spectator)
                player.ws = ws
                room.players[player.id] = player
                room.token_to_id[player.reconnect_token] = player.id
                room.last_activity = time.time()

                if is_spectator:
                    await room.broadcast_toast(f"{player.nickname} joined as a spectator for next round.", "info")
                else:
                    await room.broadcast_toast(f"{player.nickname} joined the game!", "info")

                return room, player, None

    async def rejoin(self, room_code: str, reconnect_token: str, ws: WebSocket) -> tuple[Optional[Room], Optional[Player], Optional[str]]:
        async with self.lock:
            code = room_code.upper().strip()
            room = self.rooms.get(code)
            if not room:
                return None, None, "Room not found. (Rooms reset when the server restarts — please create or join a new room.)"

            async with room.lock:
                player_id = room.token_to_id.get(reconnect_token)
                if not player_id or player_id not in room.players:
                    return None, None, "Invalid reconnect session. (Rooms reset when the server restarts — please create or join a new room.)"

                player = room.players[player_id]
                room.last_activity = time.time()
                await room.handle_reconnect(player, ws)
                return room, player, None

    async def cleanup_inactive_rooms(self):
        """Removes rooms with 0 connected players that have been inactive for > 10 minutes."""
        now = time.time()
        async with self.lock:
            expired_codes = []
            for code, room in self.rooms.items():
                if room.get_connected_count() == 0 and (now - room.last_activity > 600):
                    _cancel(room.timer_task)
                    _cancel(room.host_transfer_task)
                    expired_codes.append(code)

            for code in expired_codes:
                del self.rooms[code]
