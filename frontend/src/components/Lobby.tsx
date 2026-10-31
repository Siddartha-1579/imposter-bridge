import React, { useState } from "react";
import { PersonalizedState } from "../types";

interface LobbyProps {
  state: PersonalizedState;
  onStartGame: () => void;
}

export const Lobby: React.FC<LobbyProps> = ({ state, onStartGame }) => {
  const [copied, setCopied] = useState(false);

  const inviteUrl = `${window.location.origin}?room=${state.room_code}`;

  const handleCopy = async () => {
    try {
      if (navigator.share) {
        await navigator.share({
          title: "Join Imposter Word!",
          text: `Join my Imposter Word game room: ${state.room_code}`,
          url: inviteUrl,
        });
      } else {
        await navigator.clipboard.writeText(inviteUrl);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const playerCount = state.players.length;
  const canStart = state.is_host && playerCount >= 3 && playerCount <= 8;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div className="card" style={{ textAlign: "center", alignItems: "center", gap: "0.75rem" }}>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#94a3b8" }}>
          ROOM CODE
        </span>
        <div style={{
          fontSize: "2.8rem",
          fontWeight: 900,
          letterSpacing: "0.2em",
          color: "#818cf8",
          lineHeight: 1,
        }}>
          {state.room_code}
        </div>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleCopy}
          style={{ width: "100%", maxWidth: "240px", minHeight: "44px" }}
        >
          {copied ? "✓ Copied Link!" : "🔗 Share Invite Link"}
        </button>
      </div>

      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 800 }}>
            Players in Lobby
          </h2>
          <span style={{ fontSize: "0.85rem", color: "#94a3b8", fontWeight: 600 }}>
            {playerCount} / 8
          </span>
        </div>

        <div className="players-grid">
          {state.players.map((p) => (
            <div key={p.id} className="player-chip">
              <div className="player-name-wrapper">
                <span>{p.nickname}</span>
                {p.id === state.my_id && (
                  <span style={{ fontSize: "0.75rem", color: "#818cf8" }}>(You)</span>
                )}
                {p.is_host && <span className="host-tag">HOST</span>}
              </div>
              <div>
                {!p.is_connected ? (
                  <span className="disconnected-tag">Offline</span>
                ) : (
                  <span style={{ color: "#10b981", fontSize: "0.8rem", fontWeight: 600 }}>Ready</span>
                )}
              </div>
            </div>
          ))}
        </div>

        {state.is_host ? (
          <div style={{ marginTop: "0.5rem" }}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ width: "100%" }}
              disabled={!canStart}
              onClick={onStartGame}
            >
              {playerCount < 3
                ? `Need ${3 - playerCount} more player${3 - playerCount > 1 ? "s" : ""}`
                : "Start Game"}
            </button>
          </div>
        ) : (
          <div className="waiting-box">
            Waiting for host to start the game...
          </div>
        )}
      </div>
    </div>
  );
};
