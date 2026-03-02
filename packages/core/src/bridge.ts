import { WebSocketServer } from "ws";
import type { WebSocket } from "ws";
import type { RawData } from "ws";

import type { SynapseEvent } from "./events.js";

export function createBridge(port: number) {
  const wss = new WebSocketServer({ port });
  const subscribers = new Set<(event: SynapseEvent) => void>();

  const notify = (event: SynapseEvent) => {
    for (const handler of subscribers) {
      handler(event);
    }
  };

  const tryParseEvent = (raw: string): SynapseEvent | null => {
    try {
      return JSON.parse(raw) as SynapseEvent;
    } catch {
      return null;
    }
  };

  wss.on("connection", (socket: WebSocket) => {
    socket.on("message", (data: RawData) => {
      const parsed = tryParseEvent(data.toString());
      if (parsed) {
        notify(parsed);
      }
    });
  });

  const emit = (event: SynapseEvent) => {
    const serialized = JSON.stringify(event);

    for (const client of wss.clients) {
      if (client.readyState === client.OPEN) {
        client.send(serialized);
      }
    }

    notify(event);
  };

  const subscribe = (handler: (event: SynapseEvent) => void) => {
    subscribers.add(handler);
  };

  return { emit, subscribe };
}
