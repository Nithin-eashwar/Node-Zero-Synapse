import { useCallback, useEffect, useRef, useState } from "react";
import type { SynapseEvent } from "@nzs/core";

const BRIDGE_URL = "ws://localhost:4242";
const INITIAL_RETRY_DELAY_MS = 500;
const MAX_RETRY_DELAY_MS = 30000;

function tryParseEvent(raw: string): SynapseEvent | null {
  try {
    return JSON.parse(raw) as SynapseEvent;
  } catch {
    return null;
  }
}

function getBackoffDelay(attempt: number): number {
  return Math.min(INITIAL_RETRY_DELAY_MS * 2 ** attempt, MAX_RETRY_DELAY_MS);
}

type UseBridgeResult = {
  lastEvent: SynapseEvent | null;
  emit: (event: SynapseEvent) => void;
};

export function useBridge(): UseBridgeResult {
  const [lastEvent, setLastEvent] = useState<SynapseEvent | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const reconnectAttemptsRef = useRef(0);

  useEffect(() => {
    let disposed = false;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (disposed || reconnectTimerRef.current !== null) {
        return;
      }

      const delay = getBackoffDelay(reconnectAttemptsRef.current);
      reconnectAttemptsRef.current += 1;

      reconnectTimerRef.current = window.setTimeout(() => {
        reconnectTimerRef.current = null;
        connect();
      }, delay);
    };

    const connect = () => {
      if (disposed) {
        return;
      }

      const existingSocket = socketRef.current;
      if (
        existingSocket &&
        (existingSocket.readyState === WebSocket.OPEN ||
          existingSocket.readyState === WebSocket.CONNECTING)
      ) {
        return;
      }

      const socket = new WebSocket(BRIDGE_URL);
      socketRef.current = socket;

      socket.addEventListener("open", () => {
        reconnectAttemptsRef.current = 0;
      });

      socket.addEventListener("message", (message) => {
        if (typeof message.data !== "string") {
          return;
        }

        const parsed = tryParseEvent(message.data);
        if (parsed) {
          setLastEvent(parsed);
        }
      });

      socket.addEventListener("close", () => {
        if (socketRef.current === socket) {
          socketRef.current = null;
        }

        scheduleReconnect();
      });

      socket.addEventListener("error", () => {
        socket.close();
      });
    };

    connect();

    return () => {
      disposed = true;
      clearReconnectTimer();
      const socket = socketRef.current;
      socketRef.current = null;
      socket?.close();
    };
  }, []);

  const emit = useCallback((event: SynapseEvent) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    socket.send(JSON.stringify(event));
  }, []);

  return { lastEvent, emit };
}
