export type GamePhase = "LOBBY" | "CLUE" | "VOTE" | "REVEAL" | "SCOREBOARD" | "GAME_OVER";
export type PlayerRole = "crew" | "imposter" | "spectator";

export interface PlayerSnapshot {
  id: string;
  nickname: string;
  score: number;
  is_host: boolean;
  is_connected: boolean;
  is_turn: boolean;
  has_voted: boolean;
  is_imposter: boolean | null;
  is_spectator: boolean;
}

export interface ClueEntry {
  player_id: string;
  nickname: string;
  clue: string;
}

export interface PersonalizedState {
  room_code: string;
  phase: GamePhase;
  round_num: number;
  total_rounds: number;
  server_time_ms: number;
  deadline_ms: number | null;
  is_paused: boolean;
  my_id: string;
  is_host: boolean;
  my_role: PlayerRole;
  category: string | null;
  secret_word: string | null;
  players: PlayerSnapshot[];
  turn_order: string[];
  current_turn_player_id: string | null;
  clues: ClueEntry[];
  votes: Record<string, string> | null;
  imposter_id: string | null;
  imposter_caught: boolean | null;
  imposter_guess: string | null;
  guess_result: boolean | null;
  round_points: Record<string, number> | null;
}

export interface ToastInfo {
  id: string;
  message: string;
  level: "info" | "warning" | "success";
}
