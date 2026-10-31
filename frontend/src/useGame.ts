import { useState, useEffect, useRef, useCallback } from "react";
import { PersonalizedState, ToastInfo } from "./types";

const SESSION_KEY = "imposter_word_session";

interface SessionData {
  room_code: string;
  reconnect_token: string;
}

export function useGame() {
  const [state, setState] = useState<PersonalizedState | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "connecting" | "disconnected">("connecting");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastInfo[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const clockOffsetRef = useRef<number>(0);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const isManuallyClosedRef = useRef<boolean>(false);

  const addToast = useCallback((message: string, level: "info" | "warning" | "success" = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, message, level }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }, []);

  const getWsUrl = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // If running Vite dev server on port 3000 or 5173, point to backend on port 8000
    if (window.location.port === "3000" || window.location.port === "5173") {
      return `${protocol}//${window.location.hostname}:8000/ws`;
    }
    return `${protocol}//${window.location.host}/ws`;
  }, []);

  const send = useCallback((type: string, payload: Record<string, unknown> = {}) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, payload }));
    }
  }, []);

  const connect = useCallback(() => {
    if (isManuallyClosedRef.current) return;

    setConnectionStatus("connecting");
    const ws = new WebSocket(getWsUrl());
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus("connected");
      // Check for saved session to auto-rejoin
      const saved = localStorage.getItem(SESSION_KEY);
      if (saved) {
        try {
          const session: SessionData = JSON.parse(saved);
          if (session.room_code && session.reconnect_token) {
            ws.send(
              JSON.stringify({
                type: "rejoin",
                payload: {
                  room_code: session.room_code,
                  reconnect_token: session.reconnect_token,
                },
              })
            );
          }
        } catch {
          localStorage.removeItem(SESSION_KEY);
        }
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "auth_success") {
          const session: SessionData = {
            room_code: data.room_code,
            reconnect_token: data.reconnect_token,
          };
          localStorage.setItem(SESSION_KEY, JSON.stringify(session));
        } else if (data.type === "state") {
          const payload: PersonalizedState = data.payload;
          clockOffsetRef.current = payload.server_time_ms - Date.now();
          setState(payload);
          setErrorMessage(null);
        } else if (data.type === "error") {
          setErrorMessage(data.message);
          addToast(data.message, "warning");
          // If error during rejoin, clear session
          if (data.message.toLowerCase().includes("not found") || data.message.toLowerCase().includes("invalid")) {
            localStorage.removeItem(SESSION_KEY);
          }
        } else if (data.type === "toast") {
          addToast(data.message, data.level);
        } else if (data.type === "ping") {
          ws.send(JSON.stringify({ type: "pong" }));
        }
      } catch (err) {
        console.error("Failed to parse message:", err);
      }
    };

    ws.onclose = () => {
      setConnectionStatus("disconnected");
      wsRef.current = null;
      if (!isManuallyClosedRef.current) {
        // Auto-reconnect with 2s delay
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, 2000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [addToast, getWsUrl]);

  useEffect(() => {
    isManuallyClosedRef.current = false;
    connect();

    return () => {
      isManuallyClosedRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  // Actions
  const createRoom = useCallback((nickname: string) => {
    send("create_room", { nickname });
  }, [send]);

  const joinRoom = useCallback((roomCode: string, nickname: string) => {
    send("join_room", { room_code: roomCode, nickname });
  }, [send]);

  const startGame = useCallback(() => {
    send("start_game");
  }, [send]);

  const submitClue = useCallback((clue: string) => {
    send("submit_clue", { clue });
  }, [send]);

  const submitVote = useCallback((targetId: string) => {
    send("submit_vote", { target_id: targetId });
  }, [send]);

  const submitGuess = useCallback((guess: string) => {
    send("submit_guess", { guess });
  }, [send]);

  const nextRound = useCallback(() => {
    send("next_round");
  }, [send]);

  const playAgain = useCallback(() => {
    send("play_again");
  }, [send]);

  const leaveRoom = useCallback(() => {
    send("leave");
    localStorage.removeItem(SESSION_KEY);
    setState(null);
  }, [send]);

  // Countdown timer derived from server deadline
  const [secondsRemaining, setSecondsRemaining] = useState<number | null>(null);

  useEffect(() => {
    if (!state?.deadline_ms || state.is_paused) {
      setSecondsRemaining(null);
      return;
    }

    const interval = setInterval(() => {
      const nowEstimated = Date.now() + clockOffsetRef.current;
      const diff = Math.max(0, Math.ceil((state.deadline_ms! - nowEstimated) / 1000));
      setSecondsRemaining(diff);
    }, 250);

    return () => clearInterval(interval);
  }, [state?.deadline_ms, state?.is_paused]);

  return {
    state,
    connectionStatus,
    errorMessage,
    setErrorMessage,
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
  };
}
