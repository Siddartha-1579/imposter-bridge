import React, { useState } from "react";
import { PersonalizedState } from "../types";
import { RoleCard } from "./RoleCard";

interface CluePhaseProps {
  state: PersonalizedState;
  secondsRemaining: number | null;
  onSubmitClue: (clue: string) => void;
}

export const CluePhase: React.FC<CluePhaseProps> = ({ state, secondsRemaining, onSubmitClue }) => {
  const [clueInput, setClueInput] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);

  const currentTurnId = state.current_turn_player_id;
  const isMyTurn = currentTurnId === state.my_id;
  const activePlayer = state.players.find((p) => p.id === currentTurnId);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInputError(null);
    const cleaned = clueInput.trim();

    if (!cleaned) {
      setInputError("Please enter a clue.");
      return;
    }
    if (cleaned.split(/\s+/).length > 1) {
      setInputError("Clue must be exactly one single word!");
      return;
    }
    if (cleaned.length > 20) {
      setInputError("Clue must be 20 characters or less.");
      return;
    }
    // Crew check against secret word
    if (state.my_role === "crew" && state.secret_word) {
      if (cleaned.toLowerCase() === state.secret_word.toLowerCase()) {
        setInputError("Clue cannot be the secret word itself!");
        return;
      }
    }

    onSubmitClue(cleaned);
    setClueInput("");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <RoleCard
        role={state.my_role}
        category={state.category}
        secretWord={state.secret_word}
      />

      <div className="phase-banner">
        <div>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: 700 }}>
            PHASE 1
          </span>
          <div className="phase-title">Give Your Clue</div>
        </div>
        {secondsRemaining !== null && (
          <div className={`timer-pill ${secondsRemaining <= 5 ? "urgent" : ""}`}>
            ⏱️ {secondsRemaining}s
          </div>
        )}
      </div>

      {isMyTurn ? (
        <form onSubmit={handleSubmit} className="card" style={{ border: "2px solid #818cf8" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <span style={{ fontSize: "1.1rem", fontWeight: 800, color: "#a5b4fc" }}>
              🎯 It's YOUR turn!
            </span>
            <span style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
              Submit a single word clue (max 20 characters).
            </span>
          </div>

          <input
            type="text"
            className="input-field"
            placeholder="Type one word..."
            value={clueInput}
            maxLength={20}
            autoFocus
            onChange={(e) => {
              setClueInput(e.target.value.replace(/\s/g, ""));
              setInputError(null);
            }}
          />

          {inputError && (
            <div style={{ color: "#f87171", fontSize: "0.85rem", fontWeight: 600 }}>
              {inputError}
            </div>
          )}

          <button type="submit" className="btn btn-primary">
            Submit Clue
          </button>
        </form>
      ) : (
        <div className="waiting-box">
          {activePlayer ? (
            <>
              Waiting for <strong>{activePlayer.nickname}</strong> to give a clue...
            </>
          ) : (
            "Waiting for next clue..."
          )}
        </div>
      )}

      <div className="card">
        <h3 style={{ fontSize: "1rem", fontWeight: 800 }}>Clues This Round</h3>
        {state.clues.length === 0 ? (
          <span style={{ color: "#64748b", fontSize: "0.9rem", fontStyle: "italic" }}>
            No clues submitted yet.
          </span>
        ) : (
          <div className="clues-log">
            {state.clues.map((c, i) => (
              <div key={i} className="clue-item">
                <span className="clue-author">{c.nickname}</span>
                <span className="clue-text">{c.clue}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
