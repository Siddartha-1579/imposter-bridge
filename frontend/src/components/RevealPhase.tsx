import React, { useState } from "react";
import { PersonalizedState } from "../types";

interface RevealPhaseProps {
  state: PersonalizedState;
  secondsRemaining: number | null;
  onSubmitGuess: (guess: string) => void;
}

export const RevealPhase: React.FC<RevealPhaseProps> = ({ state, secondsRemaining, onSubmitGuess }) => {
  const [guessInput, setGuessInput] = useState("");
  const isImposter = state.my_id === state.imposter_id;
  const imposterPlayer = state.players.find((p) => p.id === state.imposter_id);

  const handleGuessSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (guessInput.trim()) {
      onSubmitGuess(guessInput.trim());
    }
  };

  // Compute vote tallies
  const voteTallies: Record<string, { count: number; voters: string[] }> = {};
  for (const p of state.players) {
    if (!p.is_spectator) {
      voteTallies[p.id] = { count: 0, voters: [] };
    }
  }

  if (state.votes) {
    for (const [voterId, targetId] of Object.entries(state.votes)) {
      if (voteTallies[targetId]) {
        voteTallies[targetId].count += 1;
        const voter = state.players.find((p) => p.id === voterId);
        if (voter) {
          voteTallies[targetId].voters.push(voter.nickname);
        }
      }
    }
  }

  // Imposter must not see the secret word until the guess is resolved
  const isAwaitingGuess = isImposter && state.imposter_caught && state.imposter_guess === null;
  const displayedWord = isAwaitingGuess || !state.secret_word ? "???" : state.secret_word;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Imposter Reveal Card */}
      <div className="card" style={{ textAlign: "center", border: "2px solid #ef4444" }}>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#fca5a5" }}>
          THE IMPOSTER WAS
        </span>
        <div style={{ fontSize: "2rem", fontWeight: 900, color: "#f87171" }}>
          🕵️ {imposterPlayer?.nickname || "Unknown"}
        </div>
        <div style={{
          background: "#0f172a",
          padding: "0.75rem",
          borderRadius: "8px",
          marginTop: "0.25rem",
        }}>
          <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
            Secret Word:
          </span>{" "}
          <strong style={{ color: "#fef08a", fontSize: "1.2rem" }}>
            {displayedWord}
          </strong>{" "}
          <span style={{ color: "#94a3b8", fontSize: "0.85rem" }}>
            ({state.category})
          </span>
        </div>
      </div>

      {/* Outcome Banner */}
      {state.imposter_caught ? (
        <div style={{
          background: "#064e3b",
          border: "1px solid #10b981",
          borderRadius: "12px",
          padding: "1rem",
          textAlign: "center",
        }}>
          <div style={{ fontSize: "1.2rem", fontWeight: 900, color: "#a7f3d0" }}>
            🎯 Imposter Caught!
          </div>
          <span style={{ fontSize: "0.85rem", color: "#d1fae5" }}>
            {state.imposter_guess !== null
              ? `Guess: "${state.imposter_guess}" (${state.guess_result ? "Correct! +2 pts" : "Wrong! Crew scores"})`
              : "Imposter gets one chance to guess the secret word!"}
          </span>
        </div>
      ) : (
        <div style={{
          background: "#450a0a",
          border: "1px solid #ef4444",
          borderRadius: "12px",
          padding: "1rem",
          textAlign: "center",
        }}>
          <div style={{ fontSize: "1.2rem", fontWeight: 900, color: "#fca5a5" }}>
            🏃 Imposter Escaped! (+3 pts)
          </div>
          <span style={{ fontSize: "0.85rem", color: "#fecaca" }}>
            The crew failed to agree or had a tie vote.
          </span>
        </div>
      )}

      {/* Imposter Guess Form / Status */}
      {state.imposter_caught && state.imposter_guess === null && (
        <>
          {isImposter ? (
            <form onSubmit={handleGuessSubmit} className="card" style={{ border: "2px solid #fbbf24" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 800, color: "#fbbf24" }}>
                  💡 Guess the Secret Word!
                </span>
                {secondsRemaining !== null && (
                  <span className="timer-pill urgent" style={{ fontSize: "0.9rem" }}>
                    ⏱️ {secondsRemaining}s
                  </span>
                )}
              </div>
              <input
                type="text"
                className="input-field"
                placeholder="What was the secret word?"
                value={guessInput}
                autoFocus
                onChange={(e) => setGuessInput(e.target.value)}
              />
              <button type="submit" className="btn btn-primary">
                Submit Final Guess
              </button>
            </form>
          ) : (
            <div className="waiting-box">
              Waiting for {imposterPlayer?.nickname} to guess the secret word ({secondsRemaining ?? 20}s)...
            </div>
          )}
        </>
      )}

      {/* Vote Breakdown */}
      <div className="card">
        <h3 style={{ fontSize: "1rem", fontWeight: 800 }}>Vote Breakdown</h3>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {Object.entries(voteTallies).map(([pid, tally]) => {
            const player = state.players.find((p) => p.id === pid);
            const isImp = pid === state.imposter_id;
            return (
              <div key={pid} className="player-chip" style={{ flexDirection: "column", alignItems: "stretch", gap: "0.25rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 700, color: isImp ? "#f87171" : "inherit" }}>
                    {player?.nickname} {isImp ? "(Imposter)" : ""}
                  </span>
                  <span style={{ fontWeight: 800, color: "#fbbf24" }}>
                    {tally.count} {tally.count === 1 ? "vote" : "votes"}
                  </span>
                </div>
                {tally.voters.length > 0 && (
                  <span style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                    Voted by: {tally.voters.join(", ")}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
