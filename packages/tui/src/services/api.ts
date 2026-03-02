/**
 * TUI API service.
 *
 * This adapter keeps the TUI view model stable while mapping onto the
 * backend endpoints that exist in this repository version.
 */

import type {
  ArchViolation,
  Contributor,
  DependencyEdge,
  DependencyNode,
  TuiArchDriftResponse,
  TuiBlastRadiusResponse,
  TuiErrorEnvelope,
  TuiMentorAskResponse,
  TuiSmartBlameResponse,
} from "@nzs/core";
import { existsSync, statSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";
const TIMEOUT_MS = 10_000;
const MENTOR_TIMEOUT_MS = 120_000;
const UNKNOWN_FILE = "(unknown)";

type JsonRecord = Record<string, unknown>;

interface BlastRadiusApiResponse {
  target?: unknown;
  blast_radius_score?: unknown;
  affected_functions?: unknown;
}

interface GraphApiNode {
  id?: unknown;
  name?: unknown;
  file?: unknown;
  filepath?: unknown;
}

interface GraphApiEdge {
  source?: unknown;
  target?: unknown;
}

interface GraphApiResponse {
  nodes?: unknown;
  edges?: unknown;
}

interface BlastTargetResolution {
  resolvedTarget: string;
  warning?: string;
  suggestions: string[];
}

interface SmartBlameDeveloper {
  name?: unknown;
  email?: unknown;
  total_commits?: unknown;
  last_commit_date?: unknown;
  overall_expertise_score?: unknown;
}

interface SmartBlameScore {
  total_score?: unknown;
  commit_count?: unknown;
  last_activity?: unknown;
  factors?: unknown;
}

interface SmartBlameSecondaryExpert {
  developer?: unknown;
  score?: unknown;
}

interface SmartBlameApiResponse {
  target?: unknown;
  primary_expert?: unknown;
  score?: unknown;
  secondary_experts?: unknown;
  bus_factor?: unknown;
}

interface GovernanceViolation {
  file_path?: unknown;
  line_number?: unknown;
  message?: unknown;
  severity?: unknown;
  from_layer?: unknown;
  to_layer?: unknown;
  from_module?: unknown;
  to_module?: unknown;
}

interface GovernanceViolationsResponse {
  violations?: unknown;
  warnings?: unknown;
}

interface MentorAskApiResponse {
  answer?: unknown;
  source?: unknown;
}

function getBaseUrl(): string {
  return process.env["SYNAPSE_API_URL"] ?? DEFAULT_BASE_URL;
}

function isDirectory(path: string): boolean {
  try {
    return statSync(path).isDirectory();
  } catch {
    return false;
  }
}

function findGitRoot(startDir: string): string | null {
  let current = resolve(startDir);
  while (true) {
    const gitDir = join(current, ".git");
    if (existsSync(gitDir) && isDirectory(gitDir)) {
      return current;
    }
    const parent = dirname(current);
    if (parent === current) {
      return null;
    }
    current = parent;
  }
}

function getRepoPath(): string {
  if (process.env["SYNAPSE_REPO_PATH"]) {
    return process.env["SYNAPSE_REPO_PATH"];
  }
  return findGitRoot(process.cwd()) ?? process.cwd();
}

function isSubPath(path: string, root: string): boolean {
  const absolutePath = resolve(path);
  const absoluteRoot = resolve(root);
  return absolutePath === absoluteRoot || absolutePath.startsWith(`${absoluteRoot}${sep}`);
}

function resolveSmartBlameInput(filePath: string): { filePath: string; repoPath: string } | TuiErrorEnvelope {
  const trimmedPath = filePath.trim();
  if (trimmedPath.length === 0) {
    return { error: { code: "VALIDATION_ERROR", message: "File path is required." } };
  }

  const configuredRepo = getRepoPath();
  let repoPath = configuredRepo;
  let normalizedFilePath = trimmedPath;

  if (isAbsolute(trimmedPath)) {
    const absolutePath = resolve(trimmedPath);
    if (isDirectory(absolutePath)) {
      return {
        error: {
          code: "VALIDATION_ERROR",
          message: "Smart Blame expects a file path, not a directory.",
        },
      };
    }

    if (!isSubPath(absolutePath, configuredRepo)) {
      const discoveredRepo = findGitRoot(dirname(absolutePath));
      if (discoveredRepo) {
        repoPath = discoveredRepo;
      }
    }

    normalizedFilePath = isSubPath(absolutePath, repoPath)
      ? relative(repoPath, absolutePath)
      : absolutePath;
  } else if (existsSync(trimmedPath) && isDirectory(trimmedPath)) {
    return {
      error: {
        code: "VALIDATION_ERROR",
        message: "Smart Blame expects a file path, not a directory.",
      },
    };
  } else {
    const candidateFromRepo = resolve(configuredRepo, trimmedPath);
    if (!existsSync(candidateFromRepo)) {
      return {
        error: {
          code: "VALIDATION_ERROR",
          message:
            `File '${trimmedPath}' was not found under repo_path '${normalizePath(resolve(configuredRepo))}'. ` +
            "Use an absolute file path or set SYNAPSE_REPO_PATH to the target git repo root.",
        },
      };
    }
  }

  return {
    filePath: normalizePath(normalizedFilePath),
    repoPath: normalizePath(resolve(repoPath)),
  };
}

function asRecord(value: unknown): JsonRecord | null {
  return typeof value === "object" && value !== null ? (value as JsonRecord) : null;
}

function asString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asStringArray(value: unknown): string[] {
  return asArray(value).filter((item): item is string => typeof item === "string");
}

function normalizePath(value: string | null): string {
  if (!value || value.trim().length === 0) {
    return UNKNOWN_FILE;
  }
  return value.replace(/\\/g, "/");
}

function buildUrl(path: string, params: Record<string, string | undefined>): string {
  const url = new URL(path, getBaseUrl());
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

function isAbortError(error: unknown): boolean {
  const obj = asRecord(error);
  return obj?.["name"] === "AbortError";
}

function toErrorEnvelope(body: unknown, fallbackMessage: string, code = "API_ERROR"): TuiErrorEnvelope {
  if (isTuiError(body)) {
    return body;
  }

  const payload = asRecord(body);
  const detail = payload?.["detail"];
  if (typeof detail === "string" && detail.length > 0) {
    return { error: { code, message: detail } };
  }

  if (typeof body === "string" && body.length > 0) {
    return { error: { code, message: body } };
  }

  return { error: { code, message: fallbackMessage } };
}

async function readBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (text.length === 0) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export function isTuiError(body: unknown): body is TuiErrorEnvelope {
  const payload = asRecord(body);
  const error = asRecord(payload?.["error"]);
  return typeof error?.["message"] === "string";
}

async function tuiFetch<T>(url: string, init?: RequestInit, timeoutMs = TIMEOUT_MS): Promise<T | TuiErrorEnvelope> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...init, signal: controller.signal });
    const body = await readBody(response);
    if (!response.ok) {
      return toErrorEnvelope(body, `${response.status} ${response.statusText}`, `HTTP_${response.status}`);
    }
    return body as T;
  } catch (error: unknown) {
    const message = isAbortError(error)
      ? "Request timed out"
      : error instanceof Error
        ? error.message
        : "Unknown network error";
    return { error: { code: "NETWORK_ERROR", message } };
  } finally {
    clearTimeout(timer);
  }
}

function riskFromRefCount(refCount: number): DependencyNode["riskLevel"] {
  if (refCount >= 8) {
    return "high";
  }
  if (refCount >= 3) {
    return "medium";
  }
  return "low";
}

function normalizeLower(value: string): string {
  return value.trim().toLowerCase();
}

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values.filter((value) => value.length > 0)));
}

function resolveBlastTargetFromGraph(target: string, graphPayload: GraphApiResponse): BlastTargetResolution {
  const graphNodes = asArray(graphPayload.nodes) as GraphApiNode[];
  const candidateNodes = graphNodes
    .map((node) => {
      const id = asString(node.id);
      const name = asString(node.name);
      return id ? { id, name } : null;
    })
    .filter((node): node is { id: string; name: string | null } => node !== null);

  const normalizedTarget = normalizeLower(target);
  if (normalizedTarget.length === 0) {
    return { resolvedTarget: target, suggestions: [] };
  }

  const exactIdMatch = candidateNodes.find((node) => normalizeLower(node.id) === normalizedTarget);
  if (exactIdMatch) {
    return { resolvedTarget: exactIdMatch.id, suggestions: [] };
  }

  const exactNameMatches = candidateNodes.filter(
    (node) => node.name !== null && normalizeLower(node.name) === normalizedTarget,
  );
  if (exactNameMatches.length > 0) {
    const picked = exactNameMatches[0];
    const warning =
      exactNameMatches.length > 1
        ? `Resolved '${target}' to '${picked.id}' (first of ${exactNameMatches.length} name matches).`
        : `Resolved '${target}' to '${picked.id}'.`;
    return {
      resolvedTarget: picked.id,
      warning,
      suggestions: [],
    };
  }

  const suffixMatches = candidateNodes.filter((node) => {
    const idLower = normalizeLower(node.id);
    return (
      idLower.endsWith(`:${normalizedTarget}`) ||
      idLower.endsWith(`/${normalizedTarget}`) ||
      idLower.endsWith(`.${normalizedTarget}`)
    );
  });
  if (suffixMatches.length > 0) {
    const picked = suffixMatches[0];
    const warning =
      suffixMatches.length > 1
        ? `Resolved '${target}' to '${picked.id}' (first of ${suffixMatches.length} suffix matches).`
        : `Resolved '${target}' to '${picked.id}'.`;
    return {
      resolvedTarget: picked.id,
      warning,
      suggestions: [],
    };
  }

  const suggestions = uniqueStrings(
    candidateNodes
      .filter((node) => {
        const idLower = normalizeLower(node.id);
        const nameLower = node.name ? normalizeLower(node.name) : "";
        return idLower.includes(normalizedTarget) || nameLower.includes(normalizedTarget);
      })
      .slice(0, 5)
      .map((node) => node.name ?? node.id),
  );

  return {
    resolvedTarget: target,
    suggestions,
  };
}

function toBlastResult(
  target: string,
  blastPayload: BlastRadiusApiResponse,
  graphPayload: GraphApiResponse | null,
  warning?: string,
): TuiBlastRadiusResponse {
  const impactedIds = new Set<string>([target]);
  const blastTarget = asString(blastPayload.target);
  if (blastTarget) {
    impactedIds.add(blastTarget);
  }
  for (const id of asStringArray(blastPayload.affected_functions)) {
    impactedIds.add(id);
  }

  const graphNodes = asArray(graphPayload?.nodes) as GraphApiNode[];
  const graphEdges = asArray(graphPayload?.edges) as GraphApiEdge[];
  const graphNodesById = new Map<string, GraphApiNode>();
  for (const node of graphNodes) {
    const nodeId = asString(node?.id);
    if (nodeId) {
      graphNodesById.set(nodeId, node);
    }
  }

  const edgeWeights = new Map<string, number>();
  const nodeRefCounts = new Map<string, number>();
  for (const id of impactedIds) {
    nodeRefCounts.set(id, 0);
  }

  for (const edge of graphEdges) {
    const sourceId = asString(edge?.source);
    const targetId = asString(edge?.target);
    if (!sourceId || !targetId) {
      continue;
    }
    if (!impactedIds.has(sourceId) || !impactedIds.has(targetId)) {
      continue;
    }

    const key = `${sourceId}->${targetId}`;
    edgeWeights.set(key, (edgeWeights.get(key) ?? 0) + 1);
    nodeRefCounts.set(sourceId, (nodeRefCounts.get(sourceId) ?? 0) + 1);
    nodeRefCounts.set(targetId, (nodeRefCounts.get(targetId) ?? 0) + 1);
  }

  const nodes: DependencyNode[] = Array.from(impactedIds).map((id) => {
    const rawNode = graphNodesById.get(id);
    const name = asString(rawNode?.name) ?? id;
    const filepath = normalizePath(asString(rawNode?.file) ?? asString(rawNode?.filepath));
    const refCount = nodeRefCounts.get(id) ?? 0;
    return {
      id,
      name,
      filepath,
      refCount,
      riskLevel: riskFromRefCount(refCount),
    };
  });

  nodes.sort((left, right) => right.refCount - left.refCount);

  const edges: DependencyEdge[] = Array.from(edgeWeights.entries()).map(([key, degrees]) => {
    const [sourceId, targetId] = key.split("->");
    return { sourceId: sourceId ?? "", targetId: targetId ?? "", degrees };
  });

  const changedFiles = Array.from(new Set(nodes.map((node) => node.filepath)));
  const warnings: string[] = [];

  const blastRadiusScore = asNumber(blastPayload.blast_radius_score) ?? 0;
  if (blastRadiusScore === 0) {
    warnings.push("No upstream dependents found for this target.");
  }
  if (!graphPayload) {
    warnings.push("Could not load /graph metadata, so file mapping may be incomplete.");
  }
  if (warning) {
    warnings.push(warning);
  }

  return { changedFiles, nodes, edges, warnings };
}

function statusFromLastActive(lastActive: string): Contributor["status"] {
  const timestamp = Date.parse(lastActive);
  if (!Number.isFinite(timestamp)) {
    return "away";
  }

  const daysSince = Math.max(0, (Date.now() - timestamp) / (24 * 60 * 60 * 1000));
  if (daysSince <= 7) {
    return "online";
  }
  if (daysSince <= 30) {
    return "away";
  }
  return "pto";
}

function toContributor(
  developerPayload: SmartBlameDeveloper,
  scorePayload: SmartBlameScore | null,
  fallbackId: string,
): Contributor {
  const name = asString(developerPayload.name) ?? "Unknown";
  const email = asString(developerPayload.email);
  const expertiseScore =
    asNumber(scorePayload?.total_score) ??
    asNumber(developerPayload.overall_expertise_score) ??
    0;
  const commitCount =
    asNumber(scorePayload?.commit_count) ??
    asNumber(developerPayload.total_commits) ??
    0;
  const factors = asRecord(scorePayload?.factors);
  const refactorDepth = asNumber(factors?.["refactor_depth"]) ?? 0;
  const refactorCount = Math.round(Math.max(commitCount, 0) * Math.max(0, refactorDepth));
  const lastActive =
    asString(scorePayload?.last_activity) ??
    asString(developerPayload.last_commit_date) ??
    new Date().toISOString();

  return {
    id: email ?? fallbackId,
    name,
    handle: email ? `@${email.split("@")[0]}` : `@${name.toLowerCase().replace(/\s+/g, "-")}`,
    expertiseScore,
    commitCount,
    refactorCount,
    lastActive,
    status: statusFromLastActive(lastActive),
  };
}

function toSmartBlameResult(filePath: string, payload: SmartBlameApiResponse): TuiSmartBlameResponse {
  const experts: Contributor[] = [];
  const seenIds = new Set<string>();

  const primaryDeveloper = asRecord(payload.primary_expert) as SmartBlameDeveloper | null;
  const primaryScore = asRecord(payload.score) as SmartBlameScore | null;
  if (primaryDeveloper) {
    const contributor = toContributor(primaryDeveloper, primaryScore, "primary");
    experts.push(contributor);
    seenIds.add(contributor.id);
  }

  for (const [index, rawSecondary] of asArray(payload.secondary_experts).entries()) {
    const secondary = asRecord(rawSecondary) as SmartBlameSecondaryExpert | null;
    const dev = asRecord(secondary?.developer) as SmartBlameDeveloper | null;
    const score = asRecord(secondary?.score) as SmartBlameScore | null;
    if (!dev) {
      continue;
    }
    const contributor = toContributor(dev, score, `secondary-${index + 1}`);
    if (seenIds.has(contributor.id)) {
      continue;
    }
    experts.push(contributor);
    seenIds.add(contributor.id);
  }

  experts.sort((left, right) => right.expertiseScore - left.expertiseScore);

  return {
    filepath: asString(payload.target) ?? filePath,
    experts,
    busFactor: asNumber(payload.bus_factor) ?? 0,
  };
}

function toArchViolation(raw: GovernanceViolation): ArchViolation {
  const file = asString(raw.file_path) ?? UNKNOWN_FILE;
  const line = Math.max(1, asNumber(raw.line_number) ?? 1);
  const fromLayer = asString(raw.from_layer) ?? "unknown";
  const toLayer = asString(raw.to_layer) ?? "unknown";
  const severity = (asString(raw.severity) ?? "error").toLowerCase();
  const message = asString(raw.message) ?? `${fromLayer} must not depend on ${toLayer}`;
  const fromModule = asString(raw.from_module) ?? "source module";
  const toModule = asString(raw.to_module) ?? "target module";

  return {
    file,
    line,
    fromLayer,
    toLayer,
    description: `[${severity.toUpperCase()}] ${message}`,
    suggestedFix: [
      `- Remove direct dependency: ${fromModule} -> ${toModule}`,
      `+ Add an interface/adapter so ${fromLayer} can depend on an allowed abstraction`,
      `+ Keep ${toLayer} implementation details inside the ${toLayer} layer`,
    ].join("\n"),
  };
}

export async function fetchBlastRadius(target: string): Promise<TuiBlastRadiusResponse | TuiErrorEnvelope> {
  const trimmedTarget = target.trim();
  if (!trimmedTarget) {
    return { error: { code: "VALIDATION_ERROR", message: "Target function name is required." } };
  }

  const graphUrl = buildUrl("/graph", {});
  const graphResponse = await tuiFetch<GraphApiResponse>(graphUrl);
  const graphPayload = isTuiError(graphResponse) ? null : graphResponse;

  const resolution = graphPayload
    ? resolveBlastTargetFromGraph(trimmedTarget, graphPayload)
    : { resolvedTarget: trimmedTarget, suggestions: [] as string[] };
  const blastUrl = buildUrl(`/blast-radius/${encodeURIComponent(resolution.resolvedTarget)}`, {});

  const blastResponse = await tuiFetch<BlastRadiusApiResponse>(blastUrl);
  if (isTuiError(blastResponse)) {
    if (blastResponse.error.code === "HTTP_404") {
      const suggestionText =
        resolution.suggestions.length > 0
          ? ` Try one of: ${resolution.suggestions.join(", ")}`
          : "";
      return {
        error: {
          code: blastResponse.error.code,
          message: `Function '${trimmedTarget}' not found in graph.${suggestionText}`,
        },
      };
    }
    return blastResponse;
  }
  return toBlastResult(resolution.resolvedTarget, blastResponse, graphPayload, resolution.warning);
}

export async function fetchSmartBlame(filePath: string): Promise<TuiSmartBlameResponse | TuiErrorEnvelope> {
  const resolution = resolveSmartBlameInput(filePath);
  if (isTuiError(resolution)) {
    return resolution;
  }

  const url = buildUrl(`/blame/expert/${encodeURI(resolution.filePath)}`, {
    repo_path: resolution.repoPath,
  });
  const response = await tuiFetch<SmartBlameApiResponse>(url);
  if (isTuiError(response)) {
    return response;
  }
  return toSmartBlameResult(resolution.filePath, response);
}

export async function fetchArchDrift(): Promise<TuiArchDriftResponse | TuiErrorEnvelope> {
  const url = buildUrl("/governance/violations", {
    repo_path: getRepoPath(),
  });
  const response = await tuiFetch<GovernanceViolationsResponse>(url);
  if (isTuiError(response)) {
    return response;
  }

  const violations = asArray(response.violations)
    .map((entry) => asRecord(entry) as GovernanceViolation | null)
    .filter((entry): entry is GovernanceViolation => entry !== null)
    .map(toArchViolation);
  const warnings = asArray(response.warnings)
    .map((entry) => asRecord(entry) as GovernanceViolation | null)
    .filter((entry): entry is GovernanceViolation => entry !== null)
    .map(toArchViolation);

  return [...violations, ...warnings];
}

export async function fetchMentorAsk(query: string): Promise<TuiMentorAskResponse | TuiErrorEnvelope> {
  const trimmedQuery = query.trim();
  if (!trimmedQuery) {
    return { error: { code: "VALIDATION_ERROR", message: "Query is required." } };
  }

  const url = buildUrl("/ai/ask", { query: trimmedQuery });
  const response = await tuiFetch<MentorAskApiResponse>(url, undefined, MENTOR_TIMEOUT_MS);
  if (isTuiError(response)) {
    return response;
  }

  const answer = asString(response.answer);
  if (!answer) {
    return toErrorEnvelope(response, "AI response missing 'answer' field.");
  }

  const source = asString(response.source) ?? undefined;
  return { answer, source };
}
