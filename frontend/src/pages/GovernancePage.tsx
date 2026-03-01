import { Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import { useViolations, useLayers } from '../lib/hooks';
import { LoadingState, ErrorState } from '../components/ui/StatusStates';

export default function GovernancePage() {
    const violationsQuery = useViolations();
    const layersQuery = useLayers();

    const isLoading = violationsQuery.isLoading || layersQuery.isLoading;
    const isError = violationsQuery.isError && layersQuery.isError;

    if (isLoading) return <LoadingState message="Validating architecture..." />;
    if (isError) return <ErrorState onRetry={() => { violationsQuery.refetch(); layersQuery.refetch(); }} />;

    const violations = violationsQuery.data?.violations ?? [];
    const warnings = violationsQuery.data?.warnings ?? [];
    const allIssues = [...violations, ...warnings];

    // Build layers from the API response
    const layerData = layersQuery.data?.layers ?? [];
    const layers = Array.isArray(layerData) ? layerData.map((l: Record<string, unknown>) => ({
        name: String(l.name ?? 'Unknown'),
        moduleCount: Array.isArray(l.patterns) ? (l.patterns as string[]).length : 0,
        violationCount: violations.filter(v => v.from_layer === l.name || v.to_layer === l.name).length,
        patterns: Array.isArray(l.patterns) ? (l.patterns as string[]) : [],
    })) : [];

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div>
                <h2 className="text-xl font-semibold tracking-tight text-white">Architectural Governance</h2>
                <p className="mt-1 text-sm text-neutral-500">
                    Layered architecture enforcement and drift detection
                </p>
            </div>

            {/* Layers Grid */}
            {layers.length > 0 && (
                <div className="grid grid-cols-4 gap-4">
                    {layers.map((layer) => (
                        <div
                            key={layer.name}
                            className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-200 hover:border-white/[0.1]"
                        >
                            <div className="flex items-center justify-between">
                                <h3 className="text-sm font-medium text-neutral-200">{layer.name} Layer</h3>
                                {layer.violationCount > 0 ? (
                                    <AlertTriangle className="h-4 w-4 text-amber-400" />
                                ) : (
                                    <CheckCircle className="h-4 w-4 text-emerald-400" />
                                )}
                            </div>
                            <div className="mt-3 space-y-2 text-xs text-neutral-500">
                                <div className="flex justify-between">
                                    <span>Patterns</span>
                                    <span className="text-neutral-300">{layer.moduleCount}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Violations</span>
                                    <span className={layer.violationCount > 0 ? 'text-amber-400' : 'text-emerald-400'}>
                                        {layer.violationCount}
                                    </span>
                                </div>
                            </div>
                            <div className="mt-3 flex flex-wrap gap-1">
                                {layer.patterns.slice(0, 3).map((p) => (
                                    <span key={p} className="rounded-md bg-white/[0.04] px-2 py-0.5 text-[10px] text-neutral-500">
                                        {p}
                                    </span>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Violations */}
            <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-6">
                <div className="mb-4 flex items-center gap-2">
                    <Shield className="h-5 w-5 text-amber-400" />
                    <h3 className="text-sm font-medium text-neutral-200">
                        Active Issues ({allIssues.length})
                    </h3>
                </div>
                {allIssues.length === 0 ? (
                    <div className="py-8 text-center text-xs text-neutral-600">
                        <CheckCircle className="mx-auto mb-2 h-8 w-8 text-emerald-500/50" />
                        No architectural violations detected
                    </div>
                ) : (
                    <div className="space-y-2">
                        {allIssues.map((v, i) => {
                            const isError = v.severity === 'error' || v.severity === 'critical';
                            const isWarning = v.severity === 'warning';
                            return (
                                <div key={i} className="flex items-start gap-4 rounded-xl bg-white/[0.02] p-4 transition-colors hover:bg-white/[0.04]">
                                    <div
                                        className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${isError ? 'bg-red-500' : isWarning ? 'bg-amber-500' : 'bg-emerald-500'
                                            }`}
                                    />
                                    <div className="min-w-0 flex-1">
                                        <p className="text-sm font-medium text-neutral-200">{v.rule_name}</p>
                                        <p className="mt-1 font-mono text-xs text-neutral-500">
                                            <span className="text-neutral-400">{v.from_module}</span>
                                            <span className="mx-2 text-neutral-700">→</span>
                                            <span className="text-neutral-400">{v.to_module}</span>
                                        </p>
                                        <p className="mt-1 text-xs text-neutral-600">{v.message}</p>
                                        {v.file_path && (
                                            <p className="mt-1 font-mono text-[10px] text-neutral-700">
                                                {v.file_path}:{v.line_number}
                                            </p>
                                        )}
                                    </div>
                                    <span
                                        className={`shrink-0 rounded-full px-2.5 py-0.5 text-[10px] font-medium ${isError
                                                ? 'bg-red-500/10 text-red-400'
                                                : isWarning
                                                    ? 'bg-amber-500/10 text-amber-400'
                                                    : 'bg-emerald-500/10 text-emerald-400'
                                            }`}
                                    >
                                        {v.severity.toUpperCase()}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
