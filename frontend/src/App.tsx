import React from "react";
import { useGame } from "./useGame";
import { Header } from "./components/Header";
import { Home } from "./components/Home";
import { Lobby } from "./components/Lobby";
import { CluePhase } from "./components/CluePhase";
import { VotePhase } from "./components/VotePhase";
import { RevealPhase } from "./components/RevealPhase";
import { Scoreboard } from "./components/Scoreboard";
import { GameOver } from "./components/GameOver";

export const App: React.FC = () => {
  const {
    state,
    connectionStatus,
    errorMessage,
    toasts,
    secondsRemaining,
    createRoom,
    joinRoom,
    startGame,
    submitClue,
    submitVote,
    submitGuess,
    nextRound,
    playAgain,
    leaveRoom,
  } = useGame();

  return (
    <div className="app-container">
      {/* Toast Notifications */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast toast-${t.level}`}>
            {t.message}
          </div>
        ))}
      </div>

      <Header
        state={state}
        connectionStatus={connectionStatus}
        onLeave={state ? leaveRoom : undefined}
      />

      {/* Low Connected Players Pause Screen */}
      {state && state.is_paused && (
        <div className="pause-overlay">
          <div style={{ fontSize: "3rem" }}>⏳</div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: 800 }}>Game Paused</h2>
          <p style={{ color: "#94a3b8", maxWidth: "300px" }}>
            Fewer than 3 players are connected. The game will resume automatically as soon as players reconnect!
          </p>
          <div className="timer-pill" style={{ background: "#1e293b" }}>
            Connected: {state.players.filter((p) => p.is_connected).length} / {state.players.length}
          </div>
        </div>
      )}

      {/* Screen Router */}
      <main style={{ flex: 1, display: "flex", flexDirection: "column" }}>
        {!state ? (
          <Home
            onCreateRoom={createRoom}
            onJoinRoom={joinRoom}
            errorMessage={errorMessage}
          />
        ) : state.phase === "LOBBY" ? (
          <Lobby state={state} onStartGame={startGame} />
        ) : state.phase === "CLUE" ? (
          <CluePhase
            state={state}
            secondsRemaining={secondsRemaining}
            onSubmitClue={submitClue}
          />
        ) : state.phase === "VOTE" ? (
          <VotePhase
            state={state}
            secondsRemaining={secondsRemaining}
            onSubmitVote={submitVote}
          />
        ) : state.phase === "REVEAL" ? (
          <RevealPhase
            state={state}
            secondsRemaining={secondsRemaining}
            onSubmitGuess={submitGuess}
          />
        ) : state.phase === "SCOREBOARD" ? (
          <Scoreboard
            state={state}
            secondsRemaining={secondsRemaining}
            onNextRound={nextRound}
          />
        ) : state.phase === "GAME_OVER" ? (
          <GameOver
            state={state}
            onPlayAgain={playAgain}
            onLeave={leaveRoom}
          />
        ) : null}
      </main>
    </div>
  );
};

export default App;
