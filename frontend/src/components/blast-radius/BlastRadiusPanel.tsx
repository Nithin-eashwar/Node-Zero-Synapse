import { AnimatePresence, motion } from 'framer-motion';
import { X, AlertTriangle, ShieldCheck, Info } from 'lucide-react';
import {
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    ResponsiveContainer,
} from 'recharts';
import type { BlastRadiusNode, RiskLevel } from '../../types';

interface BlastRadiusPanelProps {
    node: BlastRadiusNode | null;
    onClose: () => void;
}

/** Risk level → recommendation mapping */
const recommendations: Record<RiskLevel, { icon: React.ElementType; text: string; color: string; bgColor: string }> = {
    LOW: {
        icon: ShieldCheck,
        text: 'This node is well tested and low complexity. Standard workflow applies.',
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500/10 border-emerald-500/30',
    },
    MEDIUM: {
        icon: Info,
        text: 'Extra code review recommended before modifying. Consider increasing test coverage.',
        color: 'text-amber-400',
        bgColor: 'bg-amber-500/10 border-amber-500/30',
    },
    HIGH: {
        icon: AlertTriangle,
        text: 'Add unit tests before modifying this code. Pair programming suggested.',
        color: 'text-red-400',
        bgColor: 'bg-red-500/10 border-red-500/30',
    },
    CRITICAL: {
        icon: AlertTriangle,
        text: 'CRITICAL: Refactor before making changes. This is a hub node with wide downstream impact.',
        color: 'text-red-300',
        bgColor: 'bg-red-500/15 border-red-500/40',
    },
};

export default function BlastRadiusPanel({ node, onClose }: BlastRadiusPanelProps) {
    // Generate risk factors from the node data
    const riskFactors = node ? [
        { factor: 'Connectivity', value: Math.min(1, (node.complexity ?? 0) / 10), fullMark: 1 },
        { factor: 'Test Coverage', value: node.testCoverage ?? 0, fullMark: 1 },
        { factor: 'Complexity', value: Math.min(1, (node.complexity ?? 0) / 15), fullMark: 1 },
        { factor: 'Risk Level', value: node.riskLevel === 'CRITICAL' ? 1 : node.riskLevel === 'HIGH' ? 0.75 : node.riskLevel === 'MEDIUM' ? 0.5 : 0.25, fullMark: 1 },
    ] : [];

    return (
        <AnimatePresence>
            {node && (
                <motion.div
                    initial={{ x: 400, opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: 400, opacity: 0 }}
                    transition={{ type: 'spring', damping: 25, stiffness: 250 }}
                    className="fixed right-0 top-14 z-30 flex h-[calc(100vh-3.5rem)] w-[400px] flex-col border-l border-white/[0.06] bg-black/95 backdrop-blur-xl"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
                        <div>
                            <h3 className="text-sm font-medium text-white">{node.label}</h3>
                            <span className="text-xs text-neutral-500 capitalize">{node.type}</span>
                        </div>
                        <button
                            onClick={onClose}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-neutral-500 transition-colors hover:bg-white/[0.04] hover:text-white"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </div>

                    {/* Scrollable Content */}
                    <div className="flex-1 space-y-5 overflow-y-auto p-5">
                        {/* Risk Badge */}
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-neutral-500">Risk Assessment</span>
                            <span
                                className={`rounded-full px-3 py-1 text-xs font-medium tracking-wider ${node.riskLevel === 'CRITICAL'
                                    ? 'bg-red-500/20 text-red-300'
                                    : node.riskLevel === 'HIGH'
                                        ? 'bg-red-500/15 text-red-400'
                                        : node.riskLevel === 'MEDIUM'
                                            ? 'bg-amber-500/15 text-amber-400'
                                            : 'bg-emerald-500/15 text-emerald-400'
                                    }`}
                            >
                                {node.riskLevel}
                            </span>
                        </div>

                        {/* Description */}
                        <p className="text-xs leading-relaxed text-neutral-400">{node.description}</p>

                        {/* Metrics */}
                        <div className="grid grid-cols-2 gap-3">
                            <div className="rounded-xl bg-white/[0.03] p-3 text-center">
                                <div className="text-lg font-semibold text-white">{node.complexity}</div>
                                <div className="text-[10px] text-neutral-600">Connections</div>
                            </div>
                            <div className="rounded-xl bg-white/[0.03] p-3 text-center">
                                <div className="text-lg font-semibold text-white">
                                    {Math.round(node.testCoverage * 100)}%
                                </div>
                                <div className="text-[10px] text-neutral-600">Test Coverage</div>
                            </div>
                        </div>

                        {/* Radar Chart */}
                        <div>
                            <h4 className="mb-3 text-xs font-medium text-neutral-300">Risk Factor Analysis</h4>
                            <div className="rounded-xl bg-white/[0.02] p-2">
                                <ResponsiveContainer width="100%" height={220}>
                                    <RadarChart data={riskFactors} cx="50%" cy="50%" outerRadius="70%">
                                        <PolarGrid stroke="rgba(255,255,255,0.06)" strokeWidth={0.5} />
                                        <PolarAngleAxis
                                            dataKey="factor"
                                            tick={{ fill: '#737373', fontSize: 10 }}
                                        />
                                        <PolarRadiusAxis
                                            angle={30}
                                            domain={[0, 1]}
                                            tick={{ fill: '#525252', fontSize: 9 }}
                                            tickCount={4}
                                        />
                                        <Radar
                                            name="Risk"
                                            dataKey="value"
                                            stroke="#fb7185"
                                            fill="#fb7185"
                                            fillOpacity={0.15}
                                            strokeWidth={2}
                                        />
                                    </RadarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Recommendation */}
                        {(() => {
                            const rec = recommendations[node.riskLevel];
                            const RecIcon = rec.icon;
                            return (
                                <div className={`flex gap-3 rounded-xl border p-4 ${rec.bgColor}`}>
                                    <RecIcon className={`h-5 w-5 shrink-0 ${rec.color}`} />
                                    <div>
                                        <h4 className={`text-xs font-medium ${rec.color}`}>Recommendation</h4>
                                        <p className="mt-1 text-xs leading-relaxed text-neutral-400">{rec.text}</p>
                                    </div>
                                </div>
                            );
                        })()}
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
