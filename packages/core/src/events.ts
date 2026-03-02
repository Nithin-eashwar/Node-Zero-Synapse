import type { BlastRadiusResult, SmartBlameResult } from "./types.js";

export type SynapseEvent =
  | { type: "NODE_SELECTED"; nodeId: string }
  | { type: "FILTER_CHANGED"; depth: number }
  | {
      type: "VIEW_CHANGED";
      view: "blast-radius" | "smart-blame" | "mentor" | "arch-drift";
    }
  | {
      type: "DATA_UPDATE";
      payload: BlastRadiusResult | SmartBlameResult;
    };
