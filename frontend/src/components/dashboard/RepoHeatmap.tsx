import { motion } from 'framer-motion';
import { useHeatmap } from '../../lib/hooks';
import { LoadingState, ErrorState } from '../ui/StatusStates';

export default function RepoHeatmap() {
    const { data, isLoading, isError, refetch } = useHeatmap();

    if (isLoading) return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <LoadingState message="Generating heatmap..." />
        </div>
    );
    if (isError) return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <ErrorState title="Heatmap Unavailable" message="Backend heatmap endpoint not reachable." onRetry={() => refetch()} />
        </div>
    );

    // The backend returns { modules: { [name]: { module_path, ... } }, risk_areas, average_bus_factor }
    const rawModules = data?.modules ?? {};
    const moduleEntries = Object.entries(rawModules).filter(([name]) => name !== '');

    // Parse each module entry safely
    const moduleHealth = moduleEntries.map(([name, moduleData]) => {
        const mod = moduleData as Record<string, unknown>;
        // Extract available fields with safe defaults
        const busFactorVal = (mod.bus_factor ?? mod.average_bus_factor ?? 0) as number;
        const hasGap = (mod.has_knowledge_gap ?? false) as boolean;
        const expertCount = (mod.expert_count ?? mod.total_experts ?? 0) as number;
        const fileCount = (mod.file_count ?? mod.total_files ?? 1) as number;

        // Health: higher bus factor = healthier, has_knowledge_gap = bad
        const healthRaw = hasGap ? 20 : Math.min(100, busFactorVal * 30 + expertCount * 10);
        const health = Math.max(0, Math.min(100, Math.round(healthRaw)));

        return {
            name: name || 'root',
            health,
            fileCount,
            busFactor: busFactorVal,
            expertCount,
            hasGap,
        };
    });

    function healthStyle(h: number): string {
        if (h >= 60) return 'border-emerald-500/15 bg-emerald-500/[0.04] hover:border-emerald-500/25';
        if (h >= 30) return 'border-amber-500/15 bg-amber-500/[0.04] hover:border-amber-500/25';
        return 'border-red-500/15 bg-red-500/[0.04] hover:border-red-500/25';
    }

    function healthTextColor(h: number): string {
        if (h >= 60) return 'text-emerald-400';
        if (h >= 30) return 'text-amber-400';
        return 'text-red-400';
    }

    return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <div className="mb-4 flex items-center justify-between">
                <div>
                    <h3 className="text-sm font-medium text-neutral-200">Repository Heatmap</h3>
                    <p className="text-[11px] text-neutral-600">
                        {moduleEntries.length} modules analyzed
                    </p>
                </div>
                <div className="flex items-center gap-4 text-[10px] text-neutral-500">
                    <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-sm bg-emerald-500" /> Good
                    </span>
                    <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-sm bg-amber-500" /> Moderate
                    </span>
                    <span className="flex items-center gap-1.5">
                        <span className="h-2 w-2 rounded-sm bg-red-500" /> Low
                    </span>
                </div>
            </div>

            <div className="grid grid-cols-4 gap-3">
                {moduleHealth
                    .sort((a, b) => a.health - b.health)
                    .map((mod, i) => (
                        <motion.div
                            key={mod.name}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: i * 0.05, duration: 0.3 }}
                            className={`cursor-pointer rounded-xl border p-4 transition-all duration-200 hover:scale-[1.02] ${healthStyle(mod.health)}`}
                        >
                            <div className="flex items-center justify-between">
                                <span className="truncate text-xs font-medium text-neutral-300">{mod.name}</span>
                                <span className={`text-lg font-semibold tabular-nums ${healthTextColor(mod.health)}`}>
                                    {mod.health}
                                </span>
                            </div>
                            <div className="mt-3 space-y-1.5 text-[10px] text-neutral-600">
                                <div className="flex justify-between">
                                    <span>Bus Factor</span>
                                    <span className={mod.busFactor <= 1 ? 'text-red-400' : 'text-neutral-400'}>
                                        {mod.busFactor}
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Experts</span>
                                    <span className="text-neutral-400">{mod.expertCount}</span>
                                </div>
                                {mod.hasGap && (
                                    <div className="mt-1 rounded-md bg-red-500/10 px-2 py-0.5 text-center text-red-400">
                                        Knowledge Gap
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    ))}
                {moduleHealth.length === 0 && (
                    <div className="col-span-4 py-8 text-center text-xs text-neutral-600">
                        No heatmap data available
                    </div>
                )}
            </div>
        </div>
    );
}
