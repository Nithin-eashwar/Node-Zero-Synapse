import { useState } from 'react';
import { Radiation, Network, GitBranch } from 'lucide-react';
import BlastRadiusGraph from '../components/blast-radius/BlastRadiusGraph';
import BlastRadiusPanel from '../components/blast-radius/BlastRadiusPanel';
import type { BlastRadiusNode } from '../types';

type ViewMode = 'hierarchy' | 'full';

export default function BlastRadiusPage() {
    const [selectedNode, setSelectedNode] = useState<BlastRadiusNode | null>(null);
    const [viewMode, setViewMode] = useState<ViewMode>('hierarchy');

    return (
        <div className="flex h-[calc(100vh-5rem)] flex-col">
            {/* Page Header */}
            <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-red-500/10">
                        <Radiation className="h-5 w-5 text-red-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold tracking-tight text-white">Blast Radius Analysis</h2>
                        <p className="text-xs text-neutral-500">
                            {viewMode === 'hierarchy'
                                ? 'Click a module to expand files · Double-click a file to see entities'
                                : 'Click any node to inspect risk factors and recommendations'}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-4">
                    {/* View Mode Toggle */}
                    <div className="flex items-center rounded-lg border border-white/[0.08] bg-white/[0.03] p-0.5">
                        <button
                            onClick={() => setViewMode('hierarchy')}
                            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[11px] font-medium transition-all ${
                                viewMode === 'hierarchy'
                                    ? 'bg-white/10 text-white shadow-sm'
                                    : 'text-neutral-500 hover:text-neutral-300'
                            }`}
                        >
                            <Network className="h-3.5 w-3.5" />
                            Hierarchy
                        </button>
                        <button
                            onClick={() => setViewMode('full')}
                            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[11px] font-medium transition-all ${
                                viewMode === 'full'
                                    ? 'bg-white/10 text-white shadow-sm'
                                    : 'text-neutral-500 hover:text-neutral-300'
                            }`}
                        >
                            <GitBranch className="h-3.5 w-3.5" />
                            Full Graph
                        </button>
                    </div>

                    {/* Legend */}
                    <div className="flex items-center gap-4 text-[10px] font-medium text-neutral-500">
                        <span className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-emerald-500" /> LOW
                        </span>
                        <span className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-amber-500" /> MEDIUM
                        </span>
                        <span className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-red-500" /> HIGH
                        </span>
                        <span className="flex items-center gap-1.5">
                            <span className="h-2 w-2 rounded-full bg-red-400 ring-2 ring-red-500/30" /> CRITICAL
                        </span>
                    </div>
                </div>
            </div>

            {/* Graph Area */}
            <div className="flex-1">
                <BlastRadiusGraph onNodeSelect={setSelectedNode} viewMode={viewMode} />
            </div>

            {/* Side Panel */}
            <BlastRadiusPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        </div>
    );
}
