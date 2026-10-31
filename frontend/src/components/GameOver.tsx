import React from "react";
import { PersonalizedState } from "../types";

interface GameOverProps {
  state: PersonalizedState;
  onPlayAgain: () => void;
  onLeave: () => void;
}

export const GameOver: React.FC<GameOverProps> = ({ state, onPlayAgain, onLeave }) => {
  const sorted = [...state.players].sort((a, b) => b.score - a.score);
  const winner = sorted[0];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", textAlign: "center" }}>
      <div className="card" style={{ padding: "1.75rem 1rem", border: "2px solid #f59e0b" }}>
        <div style={{ fontSize: "3rem" }}>👑</div>
        <span style={{ fontSize: "0.85rem", fontWeight: 800, color: "#f59e0b", letterSpacing: "0.1em" }}>
          GAME WINNER
        </span>
        <div style={{ fontSize: "2rem", fontWeight: 900, color: "#fef08a" }}>
          {winner?.nickname}
        </div>
        <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "#cbd5e1" }}>
          {winner?.score} Total Points
        </div>
      </div>

      <div className="card" style={{ textAlign: "left" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 800 }}>Final Standings</h3>
        <div className="players-grid">
          {sorted.map((p, index) => {
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
                  {index === 0 && <span>🏆</span>}
                  {isMe && <span style={{ fontSize: "0.75rem", color: "#818cf8" }}>(You)</span>}
                </div>
                <span style={{ fontWeight: 900, fontSize: "1.1rem" }}>
                  {p.score} pts
                </span>
              </div>
            );
          })}
        </div>

        {state.is_host ? (
          <button
            type="button"
            className="btn btn-primary"
            style={{ marginTop: "1rem" }}
            onClick={onPlayAgain}
          >
            🔄 Play Again (Same Room)
          </button>
        ) : (
          <div className="waiting-box" style={{ marginTop: "1rem" }}>
            Waiting for host to start a new game...
          </div>
        )}

        <button
          type="button"
          className="btn btn-secondary"
          style={{ marginTop: "0.5rem" }}
          onClick={onLeave}
        >
          Exit Room
        </button>
      </div>
    </div>
  );
};
