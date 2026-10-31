from typing import Optional, Literal
from pydantic import BaseModel, Field

# Action models
class CreateRoomPayload(BaseModel):
    nickname: str

class JoinRoomPayload(BaseModel):
    room_code: str
    nickname: str

class RejoinPayload(BaseModel):
    room_code: str
    reconnect_token: str

class SubmitCluePayload(BaseModel):
    clue: str

class SubmitVotePayload(BaseModel):
    target_id: str

class SubmitGuessPayload(BaseModel):
    guess: str

class ClientAction(BaseModel):
    type: str
    payload: dict = Field(default_factory=dict)

# Snapshot models
class ClueEntry(BaseModel):
    player_id: str
    nickname: str
    clue: str

class PlayerSnapshot(BaseModel):
    id: str
    nickname: str
    score: int
    is_host: bool
    is_connected: bool
    is_turn: bool
    has_voted: bool
    is_imposter: Optional[bool] = None
    is_spectator: bool

class PersonalizedState(BaseModel):
    room_code: str
    phase: Literal["LOBBY", "CLUE", "VOTE", "REVEAL", "SCOREBOARD", "GAME_OVER"]
    round_num: int
    total_rounds: int
    server_time_ms: int
    deadline_ms: Optional[int] = None
    is_paused: bool
    my_id: str
    is_host: bool
    my_role: Literal["crew", "imposter", "spectator"]
    category: Optional[str] = None
    secret_word: Optional[str] = None
    players: list[PlayerSnapshot]
    turn_order: list[str]
    current_turn_player_id: Optional[str] = None
    clues: list[ClueEntry]
    votes: Optional[dict[str, str]] = None
    imposter_id: Optional[str] = None
    imposter_caught: Optional[bool] = None
    imposter_guess: Optional[str] = None
    guess_result: Optional[bool] = None
    round_points: Optional[dict[str, int]] = None

class AuthSuccessMessage(BaseModel):
    type: Literal["auth_success"] = "auth_success"
    player_id: str
    reconnect_token: str
    room_code: str

class StateMessage(BaseModel):
    type: Literal["state"] = "state"
    payload: PersonalizedState

class ErrorMessage(BaseModel):
    type: Literal["error"] = "error"
    message: str

class ToastMessage(BaseModel):
    type: Literal["toast"] = "toast"
    message: str
    level: Literal["info", "warning", "success"] = "info"
