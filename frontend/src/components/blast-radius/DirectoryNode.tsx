import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { Folder, ChevronRight } from 'lucide-react';
import type { RiskLevel } from '../../types';

export interface DirectoryNodeData {
    label: string;
    fileCount: number;
    entityCount: number;
    riskLevel: RiskLevel;
    totalComplexity: number;
    expanded: boolean;
    [key: string]: unknown;
}

const riskColors: Record<RiskLevel, { bg: string; border: string; glow: string; text: string; accent: string }> = {
    LOW:      { bg: 'bg-emerald-500/8',  border: 'border-emerald-500/30', glow: 'shadow-emerald-500/20', text: 'text-emerald-400', accent: 'bg-emerald-500' },
    MEDIUM:   { bg: 'bg-amber-500/8',    border: 'border-amber-500/30',   glow: 'shadow-amber-500/20',   text: 'text-amber-400',   accent: 'bg-amber-500' },
    HIGH:     { bg: 'bg-rose-500/8',     border: 'border-rose-500/30',    glow: 'shadow-rose-500/20',    text: 'text-rose-400',    accent: 'bg-rose-500' },
    CRITICAL: { bg: 'bg-rose-500/15',    border: 'border-rose-500/50',    glow: 'shadow-rose-500/30',    text: 'text-rose-300',    accent: 'bg-rose-500' },
};

function DirectoryNode({ data, selected }: NodeProps) {
    const d = data as unknown as DirectoryNodeData;
    const colors = riskColors[d.riskLevel];

    return (
        <>
            <Handle type="target" position={Position.Top} className="!h-2.5 !w-2.5 !border-slate-600 !bg-slate-400" />

            <div
                className={`
                    min-w-[200px] max-w-[260px] cursor-pointer rounded-2xl border px-5 py-4
                    backdrop-blur-sm transition-all duration-300
                    ${colors.bg} ${colors.border}
                    ${selected ? `shadow-lg ${colors.glow} scale-105` : 'hover:scale-[1.03] hover:shadow-md'}
                `}
            >
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                        <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${colors.bg} border ${colors.border}`}>
                            <Folder className={`h-3.5 w-3.5 ${colors.text}`} />
                        </div>
                        <span className="text-sm font-semibold text-slate-100 leading-tight">{d.label}</span>
                    </div>
                    <ChevronRight
                        className={`h-4 w-4 text-slate-500 transition-transform duration-200 ${d.expanded ? 'rotate-90' : ''}`}
                    />
                </div>

                {/* Stats row */}
                <div className="mt-3 flex items-center gap-3 text-[10px] font-medium text-slate-500">
                    <span>{d.fileCount} files</span>
                    <span className="text-slate-700">·</span>
                    <span>{d.entityCount} entities</span>
                    <span className="text-slate-700">·</span>
                    <span>CC {d.totalComplexity}</span>
                </div>

                {/* Risk badge */}
                <div className="mt-2.5 flex justify-end">
                    <span className={`rounded-full px-2.5 py-0.5 text-[9px] font-bold tracking-widest ${colors.bg} ${colors.text} border ${colors.border}`}>
                        {d.riskLevel}
                    </span>
                </div>
            </div>

            <Handle type="source" position={Position.Bottom} className="!h-2.5 !w-2.5 !border-slate-600 !bg-slate-400" />
        </>
    );
}

export default memo(DirectoryNode);
