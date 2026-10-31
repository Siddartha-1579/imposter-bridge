import React, { useState } from "react";
import { PersonalizedState } from "../types";

interface HeaderProps {
  state: PersonalizedState | null;
  connectionStatus: "connected" | "connecting" | "disconnected";
  onLeave?: () => void;
}

export const Header: React.FC<HeaderProps> = ({ state, connectionStatus, onLeave }) => {
  const [showHelp, setShowHelp] = useState(false);

  return (
    <>
      <header className="game-header">
        <div className="header-left">
          {state ? (
            <>
              <span className="room-badge">{state.room_code}</span>
              {state.phase !== "LOBBY" && state.phase !== "GAME_OVER" && (
                <span className="round-badge">
                  R{state.round_num}/{state.total_rounds}
                </span>
              )}
            </>
          ) : (
            <span style={{ fontWeight: 800, fontSize: "1.05rem", color: "#818cf8" }}>
              🕵️ Imposter Word
            </span>
          )}
        </div>

        <div className="header-right">
          <span
            className={`connection-dot dot-${connectionStatus}`}
            title={`Status: ${connectionStatus}`}
          />
          <button
            type="button"
            className="help-btn"
            onClick={() => setShowHelp(true)}
            aria-label="How to play"
          >
            ?
          </button>
          {state && onLeave && (
            <button
              type="button"
              onClick={onLeave}
              style={{
                background: "none",
                border: "none",
                color: "#94a3b8",
                cursor: "pointer",
                fontSize: "0.8rem",
                fontWeight: 600,
                padding: "0.25rem 0.5rem",
              }}
            >
              Exit
            </button>
          )}
        </div>
      </header>

      {showHelp && (
        <div className="modal-overlay" onClick={() => setShowHelp(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ fontSize: "1.3rem", fontWeight: 800 }}>How to Play</h2>
            <ul className="modal-list">
              <li><span>1.</span><span>Everyone gets the secret word except <strong>ONE Imposter</strong>.</span></li>
              <li><span>2.</span><span>Take turns giving a <strong>1-word clue</strong> to prove you know it.</span></li>
              <li><span>3.</span><span>The Imposter tries to blend in and deduce the secret word.</span></li>
              <li><span>4.</span><span>Everyone votes on who they suspect is the Imposter.</span></li>
              <li><span>5.</span><span>If caught, the Imposter gets <strong>one guess</strong> at the secret word.</span></li>
              <li><span>6.</span><span>Score points across <strong>5 rounds</strong> to claim victory!</span></li>
            </ul>
            <button
              type="button"
              className="btn btn-primary"
              style={{ marginTop: "0.5rem" }}
              onClick={() => setShowHelp(false)}
            >
              Got it!
            </button>
          </div>
        </div>
      )}
    </>
  );
};
