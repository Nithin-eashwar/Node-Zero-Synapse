import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Box, GitBranch, Zap } from 'lucide-react';
import type { RiskLevel } from '../../types';

/** Data attached to each custom flow node */
export interface CustomNodeData {
    label: string;
    nodeType: 'function' | 'class' | 'module';
    riskLevel: RiskLevel;
    complexity: number;
    testCoverage: number;
    description: string;
    [key: string]: unknown;
}

/** Risk level → color mapping */
const riskColors: Record<RiskLevel, { bg: string; border: string; glow: string; text: string }> = {
    LOW: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/40', glow: 'glow-emerald', text: 'text-emerald-400' },
    MEDIUM: { bg: 'bg-amber-500/10', border: 'border-amber-500/40', glow: 'glow-amber', text: 'text-amber-400' },
    HIGH: { bg: 'bg-rose-500/10', border: 'border-rose-500/40', glow: 'glow-rose', text: 'text-rose-400' },
    CRITICAL: { bg: 'bg-rose-500/20', border: 'border-rose-500/60', glow: 'glow-rose', text: 'text-rose-300' },
};

const typeIcons = {
    function: Zap,
    class: Box,
    module: GitBranch,
};

function CustomNode({ data, selected }: NodeProps) {
    const nodeData = data as unknown as CustomNodeData;
    const colors = riskColors[nodeData.riskLevel];
    const Icon = typeIcons[nodeData.nodeType];

    return (
        <>
            {/* Input handle (top) */}
            <Handle
                type="target"
                position={Position.Top}
                className="!h-2 !w-2 !border-slate-600 !bg-slate-400"
            />

            {/* Node body */}
            <div
                className={`
          min-w-[160px] cursor-pointer rounded-xl border px-4 py-3 transition-all duration-300
          ${colors.bg} ${colors.border}
          ${selected ? `${colors.glow} scale-105` : 'hover:scale-102'}
        `}
            >
                {/* Header row */}
                <div className="flex items-center gap-2">
                    <Icon className={`h-3.5 w-3.5 ${colors.text}`} />
                    <span className="text-xs font-semibold text-slate-200">{nodeData.label}</span>
                </div>

                {/* Metrics row */}
                <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-500">
                    <span>CC: {nodeData.complexity}</span>
                    <span>TC: {Math.round(nodeData.testCoverage * 100)}%</span>
                </div>

                {/* Risk badge */}
                <div className="mt-2 flex justify-end">
                    <span
                        className={`rounded-full px-2 py-0.5 text-[9px] font-bold tracking-wider ${colors.bg} ${colors.text}`}
                    >
                        {nodeData.riskLevel}
                    </span>
                </div>
            </div>

            {/* Output handle (bottom) */}
            <Handle
                type="source"
                position={Position.Bottom}
                className="!h-2 !w-2 !border-slate-600 !bg-slate-400"
            />
        </>
    );
}

export default memo(CustomNode);
