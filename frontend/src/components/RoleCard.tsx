import React from "react";
import { PlayerRole } from "../types";

interface RoleCardProps {
  role: PlayerRole;
  category: string | null;
  secretWord: string | null;
}

export const RoleCard: React.FC<RoleCardProps> = ({ role, category, secretWord }) => {
  if (role === "imposter") {
    return (
      <div className="role-banner imposter">
        <span className="role-title">🕵️ YOU ARE THE IMPOSTER</span>
        <span className="category-text">Category: <strong>{category}</strong></span>
        <div style={{ margin: "0.25rem 0" }}>
          <span style={{ fontSize: "1.4rem", fontWeight: 900, color: "#fca5a5", letterSpacing: "0.1em" }}>
            SECRET WORD: ???
          </span>
        </div>
        <span style={{ fontSize: "0.8rem", color: "#fecaca" }}>
          Listen closely to clues, blend in, and don't get caught!
        </span>
      </div>
    );
  }

  if (role === "spectator") {
    return (
      <div className="role-banner spectator">
        <span className="role-title">👀 SPECTATOR</span>
        <span className="category-text">Category: <strong>{category}</strong></span>
        <span style={{ fontSize: "0.85rem", color: "#cbd5e1", marginTop: "0.25rem" }}>
          You joined mid-game. You will join the action starting next round!
        </span>
      </div>
    );
  }

  // Crew
  return (
    <div className="role-banner crew">
      <span className="role-title">🛡️ YOU ARE CREW</span>
      <span className="category-text">Category: <strong>{category}</strong></span>
      <div style={{ margin: "0.25rem 0" }}>
        <span className="word-highlight">{secretWord}</span>
      </div>
      <span style={{ fontSize: "0.8rem", color: "#bae6fd" }}>
        Give a 1-word clue that proves you know the word without giving it away!
      </span>
    </div>
  );
};
