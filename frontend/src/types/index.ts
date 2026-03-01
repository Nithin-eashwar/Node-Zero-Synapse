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
