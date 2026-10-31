import asyncio
import pytest
from unittest.mock import AsyncMock

from backend.game import GameManager, Room, Player


@pytest.fixture
def dummy_room():
    room = Room("TEST")
    p1 = Player("Alice", is_host=True)
    p2 = Player("Bob")
    p3 = Player("Charlie")
    p4 = Player("Dave")
    for p in [p1, p2, p3, p4]:
        p.ws = AsyncMock()
        room.players[p.id] = p
        room.token_to_id[p.reconnect_token] = p.id
    return room, p1, p2, p3, p4


@pytest.mark.asyncio
async def test_scoring_imposter_not_caught(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    room.phase = "REVEAL"
    room.imposter_id = p1.id
    room.imposter_caught = False

    await room.apply_scoring()

    assert room.round_points[p1.id] == 3
    assert room.round_points[p2.id] == 0
    assert room.round_points[p3.id] == 0
    assert room.round_points[p4.id] == 0

    assert p1.score == 3
    assert p2.score == 0


@pytest.mark.asyncio
async def test_scoring_imposter_caught_correct_guess(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    room.phase = "REVEAL"
    room.imposter_id = p1.id
    room.imposter_caught = True
    room.guess_result = True

    await room.apply_scoring()

    assert room.round_points[p1.id] == 2
    assert room.round_points[p2.id] == 0
    assert room.round_points[p3.id] == 0
    assert room.round_points[p4.id] == 0

    assert p1.score == 2


@pytest.mark.asyncio
async def test_scoring_imposter_caught_wrong_guess(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    room.phase = "REVEAL"
    room.imposter_id = p1.id
    room.imposter_caught = True
    room.guess_result = False

    # p2 voted for imposter (p1)
    # p3 voted for someone else (p4)
    # p4 voted for imposter (p1)
    room.votes = {
        p2.id: p1.id,
        p3.id: p4.id,
        p4.id: p1.id,
    }

    await room.apply_scoring()

    assert room.round_points[p1.id] == 0
    assert room.round_points[p2.id] == 2  # voted imposter
    assert room.round_points[p3.id] == 1  # did not vote imposter
    assert room.round_points[p4.id] == 2  # voted imposter


@pytest.mark.asyncio
async def test_tie_handling_in_votes(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    room.imposter_id = p1.id
    room.phase = "VOTE"

    # p1 and p2 both get 2 votes (Tie!)
    room.votes = {
        p1.id: p2.id,
        p3.id: p2.id,
        p2.id: p1.id,
        p4.id: p1.id,
    }

    await room.finish_voting()

    # Per Amendment 8: Tie in votes = Imposter NOT caught!
    assert room.imposter_caught is False
    assert room.round_points[p1.id] == 3  # Imposter gets 3 points


@pytest.mark.asyncio
async def test_imposter_fair_rotation(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    players = [p1, p2, p3, p4]

    # Run 4 rounds
    imposters = []
    for _ in range(4):
        await room.start_new_round()
        imposters.append(room.imposter_id)

    # In 4 rounds with 4 players, every single player should be imposter exactly once
    assert len(set(imposters)) == 4
    for p in players:
        assert p.imposter_count == 1


@pytest.mark.asyncio
async def test_state_personalization_privacy(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    # p1 is host, p2 is regular, p3 is imposter, p4 is spectator
    p4.is_spectator = True
    room.phase = "CLUE"
    room.category = "Food"
    room.secret_word = "Pizza"
    room.imposter_id = p3.id

    # Capture messages sent via ws.send_text
    sent_states = {}

    def mock_send(p_id, msg):
        import json
        data = json.loads(msg)
        if data["type"] == "state":
            sent_states[p_id] = data["payload"]

    p1.ws.send_text.side_effect = lambda msg: mock_send(p1.id, msg)
    p2.ws.send_text.side_effect = lambda msg: mock_send(p2.id, msg)
    p3.ws.send_text.side_effect = lambda msg: mock_send(p3.id, msg)
    p4.ws.send_text.side_effect = lambda msg: mock_send(p4.id, msg)

    await room.broadcast_state()

    # Imposter (p3): NEVER gets secret_word
    assert sent_states[p3.id]["secret_word"] is None
    assert sent_states[p3.id]["my_role"] == "imposter"

    # Crew (p1, p2): gets secret_word, but NEVER gets imposter_id
    assert sent_states[p1.id]["secret_word"] == "Pizza"
    assert sent_states[p1.id]["imposter_id"] is None
    assert sent_states[p2.id]["secret_word"] == "Pizza"
    assert sent_states[p2.id]["imposter_id"] is None

    # Spectator (p4): per Amendment 4, NEVER receives secret_word or imposter_id before REVEAL
    assert sent_states[p4.id]["secret_word"] is None
    assert sent_states[p4.id]["imposter_id"] is None

    # All snapshots: is_imposter must be None before REVEAL, and reconnect_token NEVER leaked
    for s in sent_states.values():
        assert "reconnect_token" not in s
        for player_snap in s["players"]:
            assert "reconnect_token" not in player_snap
            assert player_snap["is_imposter"] is None

    # Now transition to REVEAL with imposter caught and awaiting guess
    room.phase = "REVEAL"
    room.imposter_caught = True
    room.imposter_guess = None
    await room.broadcast_state()

    # Everyone else gets secret_word and imposter_id; Imposter STILL gets None while guessing
    assert sent_states[p1.id]["imposter_id"] == p3.id
    assert sent_states[p1.id]["secret_word"] == "Pizza"
    assert sent_states[p4.id]["secret_word"] == "Pizza"
    assert sent_states[p3.id]["secret_word"] is None

    # Now guess is resolved
    room.imposter_guess = "Pizza"
    await room.broadcast_state()
    # Now imposter gets secret_word as well
    assert sent_states[p3.id]["secret_word"] == "Pizza"


@pytest.mark.asyncio
async def test_imposter_never_gets_secret_word_while_guessing(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    room.phase = "REVEAL"
    room.category = "Food"
    room.secret_word = "Burger"
    room.imposter_id = p2.id
    room.imposter_caught = True
    room.imposter_guess = None

    sent_states = {}

    def mock_send(p_id, msg):
        import json
        data = json.loads(msg)
        if data["type"] == "state":
            sent_states[p_id] = data["payload"]

    for p in [p1, p2, p3, p4]:
        p.ws.send_text.side_effect = lambda msg, pid=p.id: mock_send(pid, msg)

    await room.broadcast_state()

    # Crew gets secret word
    assert sent_states[p1.id]["secret_word"] == "Burger"
    # Imposter awaiting guess MUST NOT get secret word
    assert sent_states[p2.id]["secret_word"] is None

    # After guess submitted, imposter gets secret word
    room.imposter_guess = "Burger"
    await room.broadcast_state()
    assert sent_states[p2.id]["secret_word"] == "Burger"


@pytest.mark.asyncio
async def test_clue_validation_crew_vs_imposter(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    room.phase = "CLUE"
    room.secret_word = "Pizza"
    room.imposter_id = p3.id
    room.turn_order = [p1.id, p3.id]
    room.turn_index = 0

    # Crew p1 tries to submit secret word "pizza" -> rejected
    await room.submit_clue(p1, "pizza")
    assert len(room.clues) == 0

    # Crew p1 submits valid clue "cheese" -> accepted
    await room.submit_clue(p1, "cheese")
    assert len(room.clues) == 1
    assert room.clues[0].clue == "cheese"

    # Now it is imposter p3's turn
    assert room.turn_index == 1
    # Per Amendment 2: Imposter CAN submit any valid single word, even "pizza", to prevent rejection leak
    await room.submit_clue(p3, "pizza")
    assert len(room.clues) == 2
    assert room.clues[1].clue == "pizza"


@pytest.mark.asyncio
async def test_host_transfer(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    assert p1.is_host is True
    assert p2.is_host is False

    # Disconnect p1
    p1.is_connected = False
    await room.check_host_transfer(p1.id)

    # Oldest connected player is p2
    assert p1.is_host is False
    assert p2.is_host is True


@pytest.mark.asyncio
async def test_reconnect_flow():
    manager = GameManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    room, player = await manager.create_room("HostBob", ws1)
    token = player.reconnect_token
    pid = player.id

    # Mid-game disconnect
    room.phase = "CLUE"
    await room.handle_disconnect(player)
    assert player.is_connected is False

    # Rejoin with token
    r_room, r_player, err = await manager.rejoin(room.room_code, token, ws2)
    assert err is None
    assert r_room.room_code == room.room_code
    assert r_player.id == pid
    assert r_player.is_connected is True
    assert r_player.ws == ws2


@pytest.mark.asyncio
async def test_reconnect_unknown_room_friendly_message():
    manager = GameManager()
    ws = AsyncMock()
    r_room, r_player, err = await manager.rejoin("NOPE", "some_token", ws)
    assert err is not None
    assert "Rooms reset when the server restarts" in err


@pytest.mark.asyncio
async def test_stale_socket_disconnect_ignored():
    manager = GameManager()
    old_ws = AsyncMock()
    new_ws = AsyncMock()

    room, player = await manager.create_room("Alice", old_ws)
    token = player.reconnect_token

    # Advance to CLUE phase so disconnect doesn't remove player
    room.phase = "CLUE"

    # Rejoin on new_ws
    r_room, r_player, err = await manager.rejoin(room.room_code, token, new_ws)
    assert err is None
    assert player.ws == new_ws
    assert player.is_connected is True

    # Now old_ws disconnect handler runs
    await room.handle_disconnect(player, ws=old_ws)

    # Player must NOT be disconnected because old_ws is stale
    assert player.is_connected is True
    assert player.ws == new_ws


@pytest.mark.asyncio
async def test_lobby_disconnect_removes_player_and_transfers_host():
    manager = GameManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws3 = AsyncMock()

    room, host = await manager.create_room("HostAlice", ws1)
    _, p2, _ = await manager.join_room(room.room_code, "Bob", ws2)
    _, p3, _ = await manager.join_room(room.room_code, "Charlie", ws3)

    assert len(room.players) == 3
    assert host.id in room.players

    # Host disconnects during LOBBY
    await room.handle_disconnect(host, ws=ws1)

    # Host is removed from room.players and token_to_id
    assert host.id not in room.players
    assert host.reconnect_token not in room.token_to_id
    assert len(room.players) == 2

    # Bob was the next oldest connected player -> promoted to host
    assert p2.is_host is True


@pytest.mark.asyncio
async def test_start_game_and_play_again_guards(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    # Non-host cannot start
    await room.start_game(p2)
    assert room.phase == "LOBBY"

    # Disconnect p2 and p3 so only 2 connected remain
    p2.is_connected = False
    p3.is_connected = False
    await room.start_game(p1)
    assert room.phase == "LOBBY"  # Rejected: < 3 connected

    # Reconnect players and start
    p2.is_connected = True
    p3.is_connected = True
    await room.start_game(p1)
    assert room.phase == "CLUE"

    # Cannot start when not in LOBBY
    await room.start_game(p1)
    assert room.phase == "CLUE"

    # Cannot play_again unless GAME_OVER
    await room.play_again(p1)
    assert room.phase == "CLUE"

    room.phase = "GAME_OVER"
    await room.play_again(p1)
    assert room.phase == "LOBBY"


@pytest.mark.asyncio
async def test_clue_and_vote_timeout_broadcasts_to_all(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    await room.start_game(p1)

    # Fast clue timer
    room.start_timer(0.05, "CLUE")

    # Reset ws mocks
    for p in [p1, p2, p3, p4]:
        p.ws.send_text.reset_mock()

    # Wait for clue timeout to fire
    await asyncio.sleep(0.12)

    # Clue recorded and state broadcast to every connected player
    assert len(room.clues) >= 1
    assert room.clues[0].clue == "(no clue)"
    for p in [p1, p2, p3, p4]:
        assert p.ws.send_text.called

    # Fast vote timer
    room.reset_timer()
    room.phase = "VOTE"
    for p in [p1, p2, p3, p4]:
        p.ws.send_text.reset_mock()

    room.start_timer(0.05, "VOTE")
    await asyncio.sleep(0.12)

    # Vote timed out -> transitioned to REVEAL and broadcast to all
    assert room.phase == "REVEAL"
    for p in [p1, p2, p3, p4]:
        assert p.ws.send_text.called

    room.reset_timer()


@pytest.mark.asyncio
async def test_pause_and_resume_on_low_connected_players(dummy_room):
    room, p1, p2, p3, p4 = dummy_room
    room.phase = "CLUE"
    room.turn_order = [p1.id, p2.id, p3.id, p4.id]
    room.turn_index = 0
    room.start_timer(30.0, "CLUE")

    assert room.is_paused is False
    assert room.timer_task is not None

    # Disconnect p3 and p4 -> only 2 connected players remain (< 3)
    p3.is_connected = False
    p4.is_connected = False
    await room.check_pause_or_resume()

    assert room.is_paused is True
    assert room.timer_task is None
    assert room.remaining_timer_s is not None

    # Reconnect p3 -> 3 connected players now
    p3.is_connected = True
    await room.check_pause_or_resume()

    assert room.is_paused is False
    assert room.timer_task is not None
    assert room.deadline_ms is not None
    room.reset_timer()
