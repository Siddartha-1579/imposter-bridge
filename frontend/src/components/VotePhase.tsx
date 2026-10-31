import React, { useState } from "react";
import { PersonalizedState } from "../types";

interface VotePhaseProps {
  state: PersonalizedState;
  secondsRemaining: number | null;
  onSubmitVote: (targetId: string) => void;
}

export const VotePhase: React.FC<VotePhaseProps> = ({ state, secondsRemaining, onSubmitVote }) => {
  const [selectedTarget, setSelectedTarget] = useState<string | null>(null);

  const myPlayer = state.players.find((p) => p.id === state.my_id);
  const hasVoted = myPlayer?.has_voted ?? false;
  const isSpectator = state.my_role === "spectator";

  const eligibleTargets = state.players.filter(
    (p) => p.id !== state.my_id && !p.is_spectator
  );

  const activeVoters = state.players.filter((p) => !p.is_spectator);
  const votedCount = activeVoters.filter((p) => p.has_voted).length;

  const handleVoteConfirm = () => {
    if (selectedTarget) {
      onSubmitVote(selectedTarget);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div className="phase-banner">
        <div>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 700 }}>
            PHASE 2
          </span>
          <div className="phase-title">Vote for the Imposter</div>
        </div>
        {secondsRemaining !== null && (
          <div className={`timer-pill ${secondsRemaining <= 10 ? "urgent" : ""}`}>
            ⏱️ {secondsRemaining}s
          </div>
        )}
      </div>

      {/* Clues Recap */}
      <div className="card">
        <h3 style={{ fontSize: "0.95rem", fontWeight: 800, color: "#94a3b8" }}>
          Clues Summary
        </h3>
        <div className="clues-log">
          {state.clues.map((c, i) => (
            <div key={i} className="clue-item">
              <span className="clue-author">{c.nickname}</span>
              <span className="clue-text">{c.clue}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Voting Section */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ fontSize: "1.05rem", fontWeight: 800 }}>
            {hasVoted ? "Your Vote is Locked In!" : "Who is the Imposter?"}
          </h3>
          <span style={{ fontSize: "0.85rem", color: "#94a3b8", fontWeight: 600 }}>
            {votedCount} / {activeVoters.length} voted
          </span>
        </div>

        {isSpectator ? (
          <div className="waiting-box">
            You are a spectator this round. Waiting for players to vote...
          </div>
        ) : hasVoted ? (
          <div className="waiting-box">
            ✓ Vote recorded! Waiting for others to finish voting...
          </div>
        ) : (
          <>
            <div className="vote-grid">
              {eligibleTargets.map((p) => {
                const isSelected = selectedTarget === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    className={`vote-card-btn ${isSelected ? "selected" : ""}`}
                    onClick={() => setSelectedTarget(p.id)}
                  >
                    <span>{p.nickname}</span>
                    <span style={{ fontSize: "1.2rem" }}>
                      {isSelected ? "🎯" : "⚪"}
                    </span>
                  </button>
                );
              })}
            </div>

            <button
              type="button"
              className="btn btn-danger"
              disabled={!selectedTarget}
              onClick={handleVoteConfirm}
            >
              Confirm Vote
            </button>
          </>
        )}

        {/* Voting Progress indicator */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", marginTop: "0.5rem" }}>
          {activeVoters.map((p) => (
            <span
              key={p.id}
              style={{
                fontSize: "0.75rem",
                padding: "0.25rem 0.6rem",
                borderRadius: "9999px",
                background: p.has_voted ? "#064e3b" : "#334155",
                color: p.has_voted ? "#a7f3d0" : "#94a3b8",
                fontWeight: 700,
                display: "inline-flex",
                alignItems: "center",
                gap: "0.25rem",
              }}
            >
              {p.nickname} {p.has_voted ? "✓" : "..."}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
