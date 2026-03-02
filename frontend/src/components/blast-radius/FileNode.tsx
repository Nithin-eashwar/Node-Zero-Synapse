import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { FileCode, ChevronRight } from 'lucide-react';
import type { RiskLevel } from '../../types';

export interface FileNodeData {
    label: string;
    fullPath: string;
    entityCount: number;
    riskLevel: RiskLevel;
    totalComplexity: number;
    expanded: boolean;
    [key: string]: unknown;
}

const riskColors: Record<RiskLevel, { bg: string; border: string; glow: string; text: string }> = {
    LOW:      { bg: 'bg-emerald-500/8',  border: 'border-emerald-500/30', glow: 'shadow-emerald-500/20', text: 'text-emerald-400' },
    MEDIUM:   { bg: 'bg-amber-500/8',    border: 'border-amber-500/30',   glow: 'shadow-amber-500/20',   text: 'text-amber-400' },
    HIGH:     { bg: 'bg-rose-500/8',     border: 'border-rose-500/30',    glow: 'shadow-rose-500/20',    text: 'text-rose-400' },
    CRITICAL: { bg: 'bg-rose-500/15',    border: 'border-rose-500/50',    glow: 'shadow-rose-500/30',    text: 'text-rose-300' },
};

function FileNode({ data, selected }: NodeProps) {
    const d = data as unknown as FileNodeData;
    const colors = riskColors[d.riskLevel];

    return (
        <>
            <Handle type="target" position={Position.Top} className="!h-2 !w-2 !border-slate-600 !bg-slate-400" />

            <div
                className={`
                    min-w-[170px] max-w-[220px] cursor-pointer rounded-xl border px-4 py-3
                    backdrop-blur-sm transition-all duration-300
                    ${colors.bg} ${colors.border}
                    ${selected ? `shadow-lg ${colors.glow} scale-105` : 'hover:scale-[1.02]'}
                `}
            >
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <FileCode className={`h-3.5 w-3.5 ${colors.text}`} />
                        <span className="text-xs font-semibold text-slate-200 leading-tight">{d.label}</span>
                    </div>
                    <ChevronRight
                        className={`h-3.5 w-3.5 text-slate-500 transition-transform duration-200 ${d.expanded ? 'rotate-90' : ''}`}
                    />
                </div>

                {/* Stats */}
                <div className="mt-2 flex items-center gap-2.5 text-[10px] font-medium text-slate-500">
                    <span>{d.entityCount} entities</span>
                    <span className="text-slate-700">·</span>
                    <span>CC {d.totalComplexity}</span>
                </div>

                {/* Risk badge */}
                <div className="mt-2 flex justify-end">
                    <span className={`rounded-full px-2 py-0.5 text-[9px] font-bold tracking-wider ${colors.bg} ${colors.text}`}>
                        {d.riskLevel}
                    </span>
                </div>
            </div>

            <Handle type="source" position={Position.Bottom} className="!h-2 !w-2 !border-slate-600 !bg-slate-400" />
        </>
    );
}

export default memo(FileNode);
