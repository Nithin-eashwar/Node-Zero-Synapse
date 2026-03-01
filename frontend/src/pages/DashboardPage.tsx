import { motion } from 'framer-motion';
import {
    Activity,
    GitPullRequest,
    Box,
    TriangleAlert,
} from 'lucide-react';
import DriftChart from '../components/dashboard/DriftChart';
import BusFactorAlerts from '../components/dashboard/BusFactorAlerts';
import RepoHeatmap from '../components/dashboard/RepoHeatmap';
import { useFullGraph, useBusFactor, useViolations } from '../lib/hooks';
import { LoadingState, ErrorState } from '../components/ui/StatusStates';

export default function DashboardPage() {
    const graphQuery = useFullGraph();
    const busQuery = useBusFactor();
    const violationsQuery = useViolations();

    const isLoading = graphQuery.isLoading;
    const isError = graphQuery.isError;

    // Derive stats from real data (fallback to 0)
    const nodeCount = graphQuery.data?.nodes?.length ?? 0;
    const edgeCount = graphQuery.data?.edges?.length ?? 0;
    const riskAreas = busQuery.data?.risk_areas?.length ?? 0;
    const violationCount = violationsQuery.data?.total_violations ?? 0;

    const stats = [
        { label: 'Total Nodes', value: String(nodeCount), change: `${edgeCount} edges`, icon: Box, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
        { label: 'Active Edges', value: String(edgeCount), change: `${nodeCount} nodes connected`, icon: GitPullRequest, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
        { label: 'Risk Areas', value: String(riskAreas), change: `bus factor ≤ 2`, icon: Activity, color: 'text-amber-400', bg: 'bg-amber-500/10' },
        { label: 'Violations', value: String(violationCount), change: `${violationsQuery.data?.total_warnings ?? 0} warnings`, icon: TriangleAlert, color: 'text-red-400', bg: 'bg-red-500/10' },
    ];

    if (isLoading) return <LoadingState message="Analyzing codebase..." />;
    if (isError) return <ErrorState onRetry={() => graphQuery.refetch()} />;

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div>
                <h2 className="text-xl font-semibold tracking-tight text-white">Dashboard</h2>
                <p className="mt-1 text-sm text-neutral-500">
                    Real-time codebase intelligence and architectural health
                </p>
            </div>

            {/* Stat Cards */}
            <div className="grid grid-cols-4 gap-4">
                {stats.map((s, i) => {
                    const Icon = s.icon;
                    return (
                        <motion.div
                            key={s.label}
                            initial={{ opacity: 0, y: 16 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.06, duration: 0.4 }}
                            className="group rounded-2xl border border-white/[0.06] bg-white/[0.02] p-5 transition-all duration-300 hover:border-white/[0.1] hover:bg-white/[0.04]"
                        >
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-medium text-neutral-500">{s.label}</span>
                                <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${s.bg}`}>
                                    <Icon className={`h-4 w-4 ${s.color}`} />
                                </div>
                            </div>
                            <div className="mt-3 text-2xl font-semibold tracking-tight text-white">{s.value}</div>
                            <div className="mt-1 text-[11px] text-neutral-600">{s.change}</div>
                        </motion.div>
                    );
                })}
            </div>

            {/* Bento Grid: Drift + Bus Factor */}
            <div className="grid grid-cols-12 gap-4">
                <div className="col-span-7">
                    <DriftChart />
                </div>
                <div className="col-span-5">
                    <BusFactorAlerts />
                </div>
            </div>

            {/* Heatmap (Full Width) */}
            <RepoHeatmap />
        </div>
    );
}
