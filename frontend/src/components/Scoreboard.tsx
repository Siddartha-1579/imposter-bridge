import React from "react";
import { PersonalizedState } from "../types";

interface ScoreboardProps {
  state: PersonalizedState;
  secondsRemaining: number | null;
  onNextRound: () => void;
}

export const Scoreboard: React.FC<ScoreboardProps> = ({ state, secondsRemaining, onNextRound }) => {
  const sortedPlayers = [...state.players].sort((a, b) => b.score - a.score);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div className="phase-banner">
        <div>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 700 }}>
            ROUND {state.round_num} COMPLETED
          </span>
          <div className="phase-title">Leaderboard</div>
        </div>
        {secondsRemaining !== null && (
          <div className="timer-pill">
            ⏱️ {secondsRemaining}s
          </div>
        )}
      </div>

      <div className="card">
        <h3 style={{ fontSize: "1rem", fontWeight: 800 }}>Standings</h3>
        <div className="players-grid">
          {sortedPlayers.map((p, index) => {
            const roundDelta = state.round_points ? state.round_points[p.id] ?? 0 : 0;
            const isMe = p.id === state.my_id;

            return (
              <div
                key={p.id}
                className="player-chip"
                style={{
                  border: isMe ? "1px solid #818cf8" : "1px solid #334155",
                  background: isMe ? "#1e1b4b" : "#0f172a",
                }}
              >
                <div className="player-name-wrapper">
                  <span style={{ color: "#94a3b8", width: "20px" }}>#{index + 1}</span>
                  <span>{p.nickname}</span>
                  {isMe && <span style={{ fontSize: "0.75rem", color: "#818cf8" }}>(You)</span>}
                  {p.is_spectator && <span className="spectator-tag">Spectator</span>}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  {roundDelta > 0 && (
                    <span style={{ color: "#10b981", fontWeight: 800, fontSize: "0.9rem" }}>
                      +{roundDelta}
                    </span>
                  )}
                  <span style={{ fontWeight: 900, fontSize: "1.1rem" }}>
                    {p.score} pts
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {state.is_host ? (
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: "0.75rem" }}
            onClick={onNextRound}
          >
            {state.round_num >= state.total_rounds ? "See Final Results" : "Next Round"}
          </button>
        ) : (
          <div className="waiting-box" style={{ marginTop: "0.5rem" }}>
            Next round starting soon...
          </div>
        )}
      </div>
    </div>
  );
};
