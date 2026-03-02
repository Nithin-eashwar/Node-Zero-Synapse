export type RuntimeTarget = "tui" | "web";

export interface HelloMessage {
  app: RuntimeTarget;
  text: string;
}

export interface DependencyNode {
  id: string;
  name: string;
  filepath: string;
  riskLevel: "high" | "medium" | "low";
  refCount: number;
}

export interface DependencyEdge {
  sourceId: string;
  targetId: string;
  degrees: number;
}

export interface BlastRadiusResult {
  changedFiles: string[];
  nodes: DependencyNode[];
  edges: DependencyEdge[];
  warnings: string[];
}

export interface Contributor {
  id: string;
  name: string;
  handle: string;
  expertiseScore: number;
  commitCount: number;
  refactorCount: number;
  lastActive: string;
  status: "online" | "away" | "pto";
}

export interface SmartBlameResult {
  filepath: string;
  experts: Contributor[];
  busFactor: number;
}

export interface ArchViolation {
  file: string;
  line: number;
  description: string;
  fromLayer: string;
  toLayer: string;
  suggestedFix: string;
}

export interface MentorMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

// --- TUI API DTO types ---

/** Consistent error shape returned by all /tui/* endpoints on failure. */
export interface TuiApiError {
  code: string;
  message: string;
  detail?: string;
}

/** Wrapper that every /tui/* response may carry on error. */
export interface TuiErrorEnvelope {
  error: TuiApiError;
}

/** GET /tui/blast-radius?target=<string>&repo_path=<string?> */
export interface TuiBlastRadiusRequest {
  target: string;
  repo_path?: string;
}

/** Response from GET /tui/blast-radius */
export type TuiBlastRadiusResponse = BlastRadiusResult;

/** GET /tui/smart-blame?file_path=<string>&repo_path=<string?> */
export interface TuiSmartBlameRequest {
  file_path: string;
  repo_path?: string;
}

/** Response from GET /tui/smart-blame */
export type TuiSmartBlameResponse = SmartBlameResult;

/** GET /tui/arch-drift?repo_path=<string?> */
export interface TuiArchDriftRequest {
  repo_path?: string;
}

/** Response from GET /tui/arch-drift */
export type TuiArchDriftResponse = ArchViolation[];

/** POST /tui/mentor/ask body */
export interface TuiMentorAskRequest {
  query: string;
}

/** Response from POST /tui/mentor/ask */
export interface TuiMentorAskResponse {
  answer: string;
  source?: string;
}
