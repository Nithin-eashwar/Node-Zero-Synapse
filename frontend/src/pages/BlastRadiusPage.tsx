import { useState } from 'react';
import { Radiation } from 'lucide-react';
import BlastRadiusGraph from '../components/blast-radius/BlastRadiusGraph';
import BlastRadiusPanel from '../components/blast-radius/BlastRadiusPanel';
import type { BlastRadiusNode } from '../types';

export default function BlastRadiusPage() {
    const [selectedNode, setSelectedNode] = useState<BlastRadiusNode | null>(null);

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
                            Click any node to inspect risk factors and recommendations
                        </p>
                    </div>
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

            {/* Graph Area */}
            <div className="flex-1">
                <BlastRadiusGraph onNodeSelect={setSelectedNode} />
            </div>

            {/* Side Panel */}
            <BlastRadiusPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
        </div>
    );
}
