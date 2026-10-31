import asyncio
import json
import time
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.game import GameManager, Room, Player
from backend.models import (
    ClientAction,
    AuthSuccessMessage,
    ErrorMessage,
)

game_manager = GameManager()
FRONTEND_DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background task for periodic cleanup of inactive rooms
    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(60)
                await game_manager.cleanup_inactive_rooms()
            except asyncio.CancelledError:
                break
            except Exception:
                traceback.print_exc()

    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="Imposter Word", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "active_rooms": len(game_manager.rooms)}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    current_room: Optional[Room] = None
    current_player: Optional[Player] = None

    # Server ping task every 20 seconds to detect dead connections
    async def ping_worker():
        try:
            while True:
                await asyncio.sleep(20)
                await ws.send_text(json.dumps({"type": "ping"}))
        except asyncio.CancelledError:
            pass
        except Exception:
            traceback.print_exc()

    ping_task = asyncio.create_task(ping_worker())

    try:
        while True:
            raw_text = await ws.receive_text()
            try:
                data = json.loads(raw_text)
                action = ClientAction(**data)
            except Exception:
                traceback.print_exc()
                await ws.send_text(ErrorMessage(message="Invalid message format.").model_dump_json())
                continue

            action_type = action.type
            payload = action.payload

            # Handle client-side pong
            if action_type == "pong":
                continue

            # Initial room connection actions
            if action_type == "create_room":
                nickname = payload.get("nickname", "").strip()
                if not (1 <= len(nickname) <= 12):
                    await ws.send_text(ErrorMessage(message="Nickname must be between 1 and 12 characters.").model_dump_json())
                    continue

                current_room, current_player = await game_manager.create_room(nickname, ws)
                # Send private auth_success containing reconnect_token
                await ws.send_text(
                    AuthSuccessMessage(
                        player_id=current_player.id,
                        reconnect_token=current_player.reconnect_token,
                        room_code=current_room.room_code,
                    ).model_dump_json()
                )
                await current_room.broadcast_state()
                continue

            elif action_type == "join_room":
                room_code = payload.get("room_code", "").strip().upper()
                nickname = payload.get("nickname", "").strip()
                room, player, err = await game_manager.join_room(room_code, nickname, ws)
                if err or not room or not player:
                    await ws.send_text(ErrorMessage(message=err or "Failed to join room.").model_dump_json())
                    continue

                current_room = room
                current_player = player
                # Send private auth_success containing reconnect_token
                await ws.send_text(
                    AuthSuccessMessage(
                        player_id=current_player.id,
                        reconnect_token=current_player.reconnect_token,
                        room_code=current_room.room_code,
                    ).model_dump_json()
                )
                await current_room.broadcast_state()
                continue

            elif action_type == "rejoin":
                room_code = payload.get("room_code", "").strip().upper()
                reconnect_token = payload.get("reconnect_token", "").strip()
                room, player, err = await game_manager.rejoin(room_code, reconnect_token, ws)
                if err or not room or not player:
                    await ws.send_text(ErrorMessage(message=err or "Failed to rejoin room.").model_dump_json())
                    continue

                current_room = room
                current_player = player
                # Re-confirm auth_success
                await ws.send_text(
                    AuthSuccessMessage(
                        player_id=current_player.id,
                        reconnect_token=current_player.reconnect_token,
                        room_code=current_room.room_code,
                    ).model_dump_json()
                )
                await current_room.broadcast_state()
                continue

            # In-room actions require current_room and current_player
            if not current_room or not current_player:
                await ws.send_text(ErrorMessage(message="You are not in a room.").model_dump_json())
                continue

            async with current_room.lock:
                current_room.last_activity = time.time()

                if action_type == "start_game":
                    await current_room.start_game(current_player)

                elif action_type == "submit_clue":
                    clue = payload.get("clue", "")
                    await current_room.submit_clue(current_player, clue)

                elif action_type == "submit_vote":
                    target_id = payload.get("target_id", "")
                    await current_room.submit_vote(current_player, target_id)

                elif action_type == "submit_guess":
                    guess = payload.get("guess", "")
                    await current_room.submit_guess(current_player, guess)

                elif action_type == "next_round":
                    if current_player.is_host:
                        if current_room.phase == "REVEAL":
                            # Only allowed if imposter not caught OR imposter guess is submitted
                            if current_room.imposter_caught and current_room.imposter_guess is None:
                                await current_room.send_error(current_player, "Wait for the Imposter's guess.")
                            else:
                                await current_room.transition_to_scoreboard()
                        elif current_room.phase == "SCOREBOARD":
                            await current_room.advance_round()
                    else:
                        await current_room.send_error(current_player, "Only the host can advance the round.")

                elif action_type == "play_again":
                    await current_room.play_again(current_player)

                elif action_type == "leave":
                    await current_room.handle_disconnect(current_player, ws=ws)
                    current_room = None
                    current_player = None
                    break

                else:
                    await current_room.send_error(current_player, f"Unknown action: {action_type}")

    except WebSocketDisconnect:
        pass
    except Exception:
        traceback.print_exc()
    finally:
        ping_task.cancel()
        if current_room and current_player:
            async with current_room.lock:
                await current_room.handle_disconnect(current_player, ws=ws)


# Static file serving for React frontend
if FRONTEND_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = (FRONTEND_DIST_DIR / full_path).resolve()
        dist_resolved = FRONTEND_DIST_DIR.resolve()
        if file_path.is_relative_to(dist_resolved) and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
else:
    @app.get("/")
    async def index_placeholder():
        return HTMLResponse(
            "<html><body><h2>Imposter Word Backend is Running.</h2>"
            "<p>Frontend not yet built. Run 'npm run build' inside /frontend.</p></body></html>"
        )
