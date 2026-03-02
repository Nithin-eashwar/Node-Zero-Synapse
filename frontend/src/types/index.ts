// ── Risk & Graph Types ──────────────────────────────────

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface RiskFactor {
    factor: string;
    value: number;
    fullMark: number;
}

export interface BlastRadiusNode {
    id: string;
    label: string;
    type: 'function' | 'class' | 'module';
    riskLevel: RiskLevel;
    complexity: number;
    testCoverage: number;
    description: string;
}

export interface BlastRadiusEdge {
    id: string;
    source: string;
    target: string;
    label?: string;
    weight: number;
}

export interface FullGraphNode {
    id: string;
    file?: string;
    name?: string;
    type?: string;
    range?: number[];
    complexity?: number | { cyclomatic?: number };
    [key: string]: unknown;
}

export interface FullGraphEdge {
    source: string;
    target: string;
}

export interface FullGraphResponse {
    nodes: FullGraphNode[];
    edges: FullGraphEdge[];
}

export interface CondensedDirectoryNode {
    id: string;
    type: 'directory';
    label: string;
    file_count: number;
    entity_count: number;
    risk_level: RiskLevel;
    total_complexity: number;
}

export interface CondensedDirectoryEdge {
    source: string;
    target: string;
    weight: number;
}

export interface CondensedFileNode {
    id: string;
    type: 'file';
    label: string;
    full_path: string;
    directory: string;
    entity_count: number;
    risk_level: RiskLevel;
    total_complexity: number;
}

export interface CondensedFileEdge {
    source: string;
    target: string;
    weight: number;
}

export interface CondensedEntityNode {
    id: string;
    name: string;
    type: string;
    risk_level: RiskLevel;
    complexity: number;
    degree: number;
    line: number;
}

export interface CondensedEntityEdge {
    source: string;
    target: string;
}

export interface CondensedGraphResponse {
    directory_nodes: CondensedDirectoryNode[];
    directory_edges: CondensedDirectoryEdge[];
    files_by_directory: Record<string, CondensedFileNode[]>;
    file_edges: CondensedFileEdge[];
    entities_by_file: Record<string, CondensedEntityNode[]>;
    entity_edges: CondensedEntityEdge[];
}

// ── Expert / Smart Blame Types ──────────────────────────

export interface ExpertiseFactor {
    name: string;
    value: number;
    label: string;
    color: string;
}

export interface ExpertProfile {
    name: string;
    email: string;
    avatarUrl?: string;
    totalScore: number;
    confidence: number;
    recommendation: string;
    factors: ExpertiseFactor[];
}

// ── Drift & Governance Types ────────────────────────────

export interface DriftDataPoint {
    day: string;
    coupling: number;
    violations: number;
    cohesion: number;
}

export interface BusFactorAlert {
    filePath: string;
    expertCount: number;
    primaryExpert: string;
    riskLevel: RiskLevel;
    lastModified: string;
}

export interface HeatmapModule {
    name: string;
    health: number; // 0-100
    complexity: number;
    testCoverage: number;
    changeFrequency: number;
}

// ── Governance Types ────────────────────────────────────

export interface Violation {
    id: string;
    rule: string;
    fromModule: string;
    toModule: string;
    severity: RiskLevel;
    description: string;
}

export interface GovernanceLayer {
    name: string;
    patterns: string[];
    moduleCount: number;
    violationCount: number;
}
