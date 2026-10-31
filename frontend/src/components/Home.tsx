import React, { useState, useEffect } from "react";

interface HomeProps {
  onCreateRoom: (nickname: string) => void;
  onJoinRoom: (roomCode: string, nickname: string) => void;
  errorMessage: string | null;
}

export const Home: React.FC<HomeProps> = ({ onCreateRoom, onJoinRoom, errorMessage }) => {
  const [mode, setMode] = useState<"join" | "create">("create");
  const [createNick, setCreateNick] = useState("");
  const [joinNick, setJoinNick] = useState("");
  const [roomCode, setRoomCode] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  // Check URL query parameters for ?room=ABCD
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("room");
    if (code) {
      setRoomCode(code.toUpperCase().replace(/[^A-Z]/g, "").slice(0, 4));
      setMode("join");
    }
  }, []);

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    const trimmed = createNick.trim();
    if (!trimmed) {
      setLocalError("Please enter your nickname.");
      return;
    }
    if (trimmed.length > 12) {
      setLocalError("Nickname must be at most 12 characters.");
      return;
    }
    onCreateRoom(trimmed);
  };

  const handleJoin = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    const trimmedCode = roomCode.trim().toUpperCase();
    const trimmedNick = joinNick.trim();

    if (!trimmedCode || trimmedCode.length !== 4) {
      setLocalError("Room code must be exactly 4 letters.");
      return;
    }
    if (!trimmedNick) {
      setLocalError("Please enter your nickname.");
      return;
    }
    if (trimmedNick.length > 12) {
      setLocalError("Nickname must be at most 12 characters.");
      return;
    }
    onJoinRoom(trimmedCode, trimmedNick);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", marginTop: "1rem" }}>
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        <div style={{ fontSize: "3rem" }}>🕵️‍♂️</div>
        <h1 style={{ fontSize: "2rem", fontWeight: 900, letterSpacing: "-0.03em" }}>
          Imposter Word
        </h1>
        <p style={{ color: "#94a3b8", fontSize: "0.95rem" }}>
          The real-time deception party game.
        </p>
      </div>

      <div style={{ display: "flex", background: "#1e293b", borderRadius: "12px", padding: "4px" }}>
        <button
          type="button"
          onClick={() => { setMode("create"); setLocalError(null); }}
          className="btn"
          style={{
            flex: 1,
            background: mode === "create" ? "#6366f1" : "transparent",
            color: "white",
            minHeight: "44px",
          }}
        >
          Create Room
        </button>
        <button
          type="button"
          onClick={() => { setMode("join"); setLocalError(null); }}
          className="btn"
          style={{
            flex: 1,
            background: mode === "join" ? "#6366f1" : "transparent",
            color: "white",
            minHeight: "44px",
          }}
        >
          Join Room
        </button>
      </div>

      {(localError || errorMessage) && (
        <div style={{
          background: "#450a0a",
          border: "1px solid #ef4444",
          color: "#fca5a5",
          padding: "0.75rem 1rem",
          borderRadius: "10px",
          fontSize: "0.9rem",
          fontWeight: 600,
        }}>
          {localError || errorMessage}
        </div>
      )}

      {mode === "create" ? (
        <form onSubmit={handleCreate} className="card">
          <label style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#94a3b8" }}>
              YOUR NICKNAME
            </span>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. Detective Sam"
              value={createNick}
              maxLength={12}
              autoFocus
              onChange={(e) => setCreateNick(e.target.value)}
            />
          </label>
          <button type="submit" className="btn btn-primary" style={{ marginTop: "0.5rem" }}>
            Create Room
          </button>
        </form>
      ) : (
        <form onSubmit={handleJoin} className="card">
          <label style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#94a3b8" }}>
              4-LETTER ROOM CODE
            </span>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. ABCD"
              value={roomCode}
              maxLength={4}
              style={{ textTransform: "uppercase", letterSpacing: "0.2em", textAlign: "center" }}
              onChange={(e) => setRoomCode(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""))}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.85rem", fontWeight: 700, color: "#94a3b8" }}>
              YOUR NICKNAME
            </span>
            <input
              type="text"
              className="input-field"
              placeholder="e.g. Alex"
              value={joinNick}
              maxLength={12}
              onChange={(e) => setJoinNick(e.target.value)}
            />
          </label>

          <button type="submit" className="btn btn-primary" style={{ marginTop: "0.5rem" }}>
            Join Game
          </button>
        </form>
      )}

      <div style={{ textAlign: "center", color: "#64748b", fontSize: "0.85rem", marginTop: "1rem" }}>
        No logins, no downloads. 3 to 8 players.
      </div>
    </div>
  );
};
