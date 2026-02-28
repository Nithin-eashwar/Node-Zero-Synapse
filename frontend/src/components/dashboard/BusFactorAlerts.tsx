import { motion } from 'framer-motion';
import { AlertTriangle, FolderOpen } from 'lucide-react';
import { useBusFactor } from '../../lib/hooks';
import { LoadingState, ErrorState } from '../ui/StatusStates';

export default function BusFactorAlerts() {
    const { data, isLoading, isError, refetch } = useBusFactor();

    if (isLoading) return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <LoadingState message="Analyzing bus factor..." />
        </div>
    );
    if (isError) return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <ErrorState title="Bus Factor Unavailable" message="Backend smart blame endpoint not reachable." onRetry={() => refetch()} />
        </div>
    );

    const analysis = data?.analysis ?? {};
    const riskAreas = data?.risk_areas ?? [];

    // Sort entries by bus factor (lowest = most risky first)
    const entries = Object.entries(analysis)
        .sort(([, a], [, b]) => a - b)
        .slice(0, 8);

    return (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5">
            <div className="mb-4 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-red-400" />
                <h3 className="text-sm font-medium text-neutral-200">Bus Factor Analysis</h3>
                <span className="ml-auto rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-medium text-red-400">
                    {riskAreas.length} at risk
                </span>
            </div>

            <div className="space-y-1.5">
                {entries.map(([modulePath, busFactor], i) => {
                    const isRisk = busFactor <= (data?.warning_threshold ?? 2);
                    return (
                        <motion.div
                            key={modulePath}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.06, duration: 0.3 }}
                            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition-colors ${isRisk
                                    ? 'bg-red-500/[0.06] hover:bg-red-500/[0.1]'
                                    : 'bg-white/[0.02] hover:bg-white/[0.04]'
                                }`}
                        >
                            {/* Risk dot */}
                            <div
                                className={`h-1.5 w-1.5 shrink-0 rounded-full ${isRisk
                                        ? 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.4)]'
                                        : 'bg-emerald-500'
                                    }`}
                            />

                            {/* Module info */}
                            <div className="min-w-0 flex-1">
                                <p className="truncate font-mono text-xs text-neutral-300">{modulePath}</p>
                                <div className="mt-0.5 flex items-center gap-2 text-[10px] text-neutral-600">
                                    <FolderOpen className="h-3 w-3" />
                                    <span>Bus factor: {busFactor}</span>
                                </div>
                            </div>

                            {/* Bus factor badge */}
                            <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${isRisk ? 'bg-red-500/10 text-red-400' : 'bg-emerald-500/10 text-emerald-400'
                                }`}>
                                {isRisk ? 'AT RISK' : 'SAFE'}
                            </span>
                        </motion.div>
                    );
                })}
                {entries.length === 0 && (
                    <p className="py-8 text-center text-xs text-neutral-600">No bus factor data available</p>
                )}
            </div>
        </div>
    );
}
