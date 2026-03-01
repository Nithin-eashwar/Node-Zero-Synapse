import type {
    BlastRadiusNode,
    BlastRadiusEdge,
    RiskFactor,
    ExpertProfile,
    DriftDataPoint,
    BusFactorAlert,
    HeatmapModule,
    Violation,
    GovernanceLayer,
} from '../types';

// ── Blast Radius Graph Data ─────────────────────────────

export const blastRadiusNodes: BlastRadiusNode[] = [
    {
        id: 'process_data',
        label: 'process_data()',
        type: 'function',
        riskLevel: 'HIGH',
        complexity: 18,
        testCoverage: 0.12,
        description: 'Core data transformation pipeline. High cyclomatic complexity and poor test coverage.',
    },
    {
        id: 'validate_input',
        label: 'validate_input()',
        type: 'function',
        riskLevel: 'MEDIUM',
        complexity: 8,
        testCoverage: 0.65,
        description: 'Input sanitization and schema validation layer.',
    },
    {
        id: 'transform_record',
        label: 'transform_record()',
        type: 'function',
        riskLevel: 'LOW',
        complexity: 4,
        testCoverage: 0.92,
        description: 'Maps raw records to internal data model.',
    },
    {
        id: 'DataPipeline',
        label: 'DataPipeline',
        type: 'class',
        riskLevel: 'CRITICAL',
        complexity: 32,
        testCoverage: 0.05,
        description: 'Orchestrator class. Single point of failure with 12 downstream dependents.',
    },
    {
        id: 'cache_manager',
        label: 'cache_manager()',
        type: 'function',
        riskLevel: 'MEDIUM',
        complexity: 11,
        testCoverage: 0.43,
        description: 'Redis-backed caching layer for processed results.',
    },
    {
        id: 'emit_event',
        label: 'emit_event()',
        type: 'function',
        riskLevel: 'LOW',
        complexity: 3,
        testCoverage: 0.88,
        description: 'Publishes domain events to the message bus.',
    },
    {
        id: 'write_output',
        label: 'write_output()',
        type: 'function',
        riskLevel: 'HIGH',
        complexity: 15,
        testCoverage: 0.22,
        description: 'Writes results to database and file system. Side-effect heavy.',
    },
    {
        id: 'notify_service',
        label: 'notify_service()',
        type: 'function',
        riskLevel: 'LOW',
        complexity: 5,
        testCoverage: 0.78,
        description: 'Sends Slack/email notifications on pipeline completion.',
    },
    {
        id: 'audit_logger',
        label: 'audit_logger()',
        type: 'function',
        riskLevel: 'MEDIUM',
        complexity: 7,
        testCoverage: 0.55,
        description: 'Compliance audit trail for all data mutations.',
    },
    {
        id: 'retry_handler',
        label: 'retry_handler()',
        type: 'function',
        riskLevel: 'MEDIUM',
        complexity: 9,
        testCoverage: 0.38,
        description: 'Exponential backoff retry logic for transient failures.',
    },
];

export const blastRadiusEdges: BlastRadiusEdge[] = [
    { id: 'e1', source: 'DataPipeline', target: 'process_data', label: 'CALLS', weight: 0.9 },
    { id: 'e2', source: 'process_data', target: 'validate_input', label: 'CALLS', weight: 0.7 },
    { id: 'e3', source: 'process_data', target: 'transform_record', label: 'CALLS', weight: 0.6 },
    { id: 'e4', source: 'process_data', target: 'cache_manager', label: 'CALLS', weight: 0.5 },
    { id: 'e5', source: 'DataPipeline', target: 'emit_event', label: 'CALLS', weight: 0.4 },
    { id: 'e6', source: 'DataPipeline', target: 'write_output', label: 'CALLS', weight: 0.8 },
    { id: 'e7', source: 'write_output', target: 'notify_service', label: 'CALLS', weight: 0.3 },
    { id: 'e8', source: 'write_output', target: 'audit_logger', label: 'CALLS', weight: 0.5 },
    { id: 'e9', source: 'DataPipeline', target: 'retry_handler', label: 'CALLS', weight: 0.6 },
    { id: 'e10', source: 'retry_handler', target: 'process_data', label: 'CALLS', weight: 0.4 },
];

// ── Risk Factor Radar Data ──────────────────────────────

export const riskFactors: RiskFactor[] = [
    { factor: 'Complexity', value: 0.75, fullMark: 1 },
    { factor: 'Centrality', value: 0.82, fullMark: 1 },
    { factor: 'Test Coverage', value: 0.95, fullMark: 1 },
    { factor: 'Dependencies', value: 0.45, fullMark: 1 },
    { factor: 'Change Freq', value: 0.60, fullMark: 1 },
    { factor: 'Bus Factor', value: 0.70, fullMark: 1 },
];

// ── Expert Profile ──────────────────────────────────────

export const expertProfile: ExpertProfile = {
    name: 'Sarah Chen',
    email: 'sarah.chen@company.dev',
    totalScore: 0.85,
    confidence: 0.92,
    recommendation: 'Ask Sarah, she architected this module',
    factors: [
        { name: 'commit_frequency', value: 0.75, label: 'Commit Frequency', color: '#10b981' },
        { name: 'lines_changed', value: 0.80, label: 'Lines Changed', color: '#06b6d4' },
        { name: 'refactor_depth', value: 0.95, label: 'Refactor Depth', color: '#6366f1' },
        { name: 'architectural_changes', value: 0.90, label: 'Architecture', color: '#8b5cf6' },
        { name: 'bug_fixes', value: 0.60, label: 'Bug Fixes', color: '#f59e0b' },
        { name: 'recency', value: 0.85, label: 'Recency', color: '#f43f5e' },
        { name: 'code_review_participation', value: 0.70, label: 'Code Review', color: '#64748b' },
    ],
};

// ── Drift Metrics (30 days) ─────────────────────────────

export const driftMetrics: DriftDataPoint[] = Array.from({ length: 30 }, (_, i) => {
    const day = `Day ${i + 1}`;
    const base = 0.15;
    const trend = i * 0.008;
    const noise = () => (Math.random() - 0.5) * 0.04;
    return {
        day,
        coupling: Math.min(1, +(base + trend + noise()).toFixed(3)),
        violations: Math.max(0, Math.floor(2 + i * 0.3 + (Math.random() - 0.5) * 2)),
        cohesion: Math.max(0.2, +(0.85 - i * 0.006 + noise()).toFixed(3)),
    };
});

// ── Bus Factor Alerts ───────────────────────────────────

export const busFactorAlerts: BusFactorAlert[] = [
    {
        filePath: 'backend/graph/code_graph.py',
        expertCount: 1,
        primaryExpert: 'Marcus Rivera',
        riskLevel: 'CRITICAL',
        lastModified: '2 days ago',
    },
    {
        filePath: 'backend/parsing/parser.py',
        expertCount: 1,
        primaryExpert: 'Sarah Chen',
        riskLevel: 'CRITICAL',
        lastModified: '5 days ago',
    },
    {
        filePath: 'backend/governance/drift.py',
        expertCount: 2,
        primaryExpert: 'Alex Petrov',
        riskLevel: 'HIGH',
        lastModified: '1 week ago',
    },
    {
        filePath: 'backend/git/blame/analyzer.py',
        expertCount: 2,
        primaryExpert: 'Sarah Chen',
        riskLevel: 'HIGH',
        lastModified: '3 days ago',
    },
    {
        filePath: 'backend/api/routes/governance.py',
        expertCount: 1,
        primaryExpert: 'Jordan Lee',
        riskLevel: 'CRITICAL',
        lastModified: '1 day ago',
    },
];

// ── Heatmap Modules ─────────────────────────────────────

export const heatmapModules: HeatmapModule[] = [
    { name: 'api', health: 78, complexity: 12, testCoverage: 0.72, changeFrequency: 0.65 },
    { name: 'parsing', health: 85, complexity: 22, testCoverage: 0.81, changeFrequency: 0.40 },
    { name: 'graph', health: 42, complexity: 35, testCoverage: 0.25, changeFrequency: 0.88 },
    { name: 'git/blame', health: 68, complexity: 18, testCoverage: 0.55, changeFrequency: 0.50 },
    { name: 'governance', health: 90, complexity: 10, testCoverage: 0.90, changeFrequency: 0.30 },
    { name: 'core/scoring', health: 55, complexity: 28, testCoverage: 0.35, changeFrequency: 0.72 },
    { name: 'data', health: 95, complexity: 5, testCoverage: 0.95, changeFrequency: 0.15 },
    { name: 'services', health: 62, complexity: 20, testCoverage: 0.48, changeFrequency: 0.60 },
];

// ── Governance Violations ───────────────────────────────

export const governanceViolations: Violation[] = [
    {
        id: 'v1',
        rule: 'API cannot access Data directly',
        fromModule: 'api/routes/graph.py',
        toModule: 'data/models.py',
        severity: 'HIGH',
        description: 'Direct import from data layer bypasses service abstraction.',
    },
    {
        id: 'v2',
        rule: 'Service layer isolation',
        fromModule: 'services/pipeline.py',
        toModule: 'api/middleware.py',
        severity: 'MEDIUM',
        description: 'Reverse dependency — service should not depend on API layer.',
    },
    {
        id: 'v3',
        rule: 'No circular imports',
        fromModule: 'graph/resolver.py',
        toModule: 'parsing/entities.py',
        severity: 'LOW',
        description: 'Potential circular dependency through transitive imports.',
    },
];

// ── Governance Layers ───────────────────────────────────

export const governanceLayers: GovernanceLayer[] = [
    { name: 'API', patterns: ['**/api/**', '**/routes/**'], moduleCount: 8, violationCount: 1 },
    { name: 'Service', patterns: ['**/services/**', '**/core/**'], moduleCount: 12, violationCount: 1 },
    { name: 'Data', patterns: ['**/data/**', '**/models/**'], moduleCount: 6, violationCount: 0 },
    { name: 'Graph', patterns: ['**/graph/**'], moduleCount: 5, violationCount: 1 },
];
