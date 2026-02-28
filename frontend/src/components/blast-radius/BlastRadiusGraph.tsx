import { useCallback, useMemo, useState, useEffect } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    type Node,
    type Edge,
    type NodeMouseHandler,
    MarkerType,
    BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import CustomNode from './CustomNode';
import type { CustomNodeData } from './CustomNode';
import { useFullGraph } from '../../lib/hooks';
import type { BlastRadiusNode } from '../../types';
import { LoadingState, ErrorState } from '../ui/StatusStates';

interface BlastRadiusGraphProps {
    onNodeSelect: (node: BlastRadiusNode | null) => void;
}

const nodeTypes = { custom: CustomNode };

export default function BlastRadiusGraph({ onNodeSelect }: BlastRadiusGraphProps) {
    const { data, isLoading, isError, refetch } = useFullGraph();
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

    // Convert API response into React Flow nodes + edges
    const { flowNodes, flowEdges, blastNodes } = useMemo(() => {
        if (!data) return { flowNodes: [] as Node[], flowEdges: [] as Edge[], blastNodes: [] as BlastRadiusNode[] };

        const apiNodes = data.nodes ?? [];
        const apiEdges = data.edges ?? [];

        // Calculate metrics per node
        const outDegree: Record<string, number> = {};
        const inDegree: Record<string, number> = {};
        apiEdges.forEach(e => {
            outDegree[e.source] = (outDegree[e.source] ?? 0) + 1;
            inDegree[e.target] = (inDegree[e.target] ?? 0) + 1;
        });

        // Build BlastRadiusNode from API node
        const blastNodes: BlastRadiusNode[] = apiNodes.map(n => {
            const out = outDegree[n.id] ?? 0;
            const inn = inDegree[n.id] ?? 0;
            const total = out + inn;
            const riskLevel = total >= 8 ? 'CRITICAL' : total >= 5 ? 'HIGH' : total >= 2 ? 'MEDIUM' : 'LOW';
            return {
                id: n.id,
                label: n.id,
                type: n.id.includes('.') || n.id[0] === n.id[0].toUpperCase() ? 'class' : 'function',
                riskLevel,
                complexity: out,
                testCoverage: 0,
                description: `File: ${n.file} (line ${n.line}). ${out} outgoing, ${inn} incoming edges.`,
            };
        });

        // Layout: arrange nodes in a grid-like layout
        const cols = Math.max(1, Math.ceil(Math.sqrt(apiNodes.length)));
        const flowNodes: Node[] = blastNodes.map((n, i) => ({
            id: n.id,
            type: 'custom',
            position: {
                x: (i % cols) * 240 + (Math.random() * 40 - 20),
                y: Math.floor(i / cols) * 160 + (Math.random() * 30 - 15),
            },
            data: {
                label: n.label,
                nodeType: n.type,
                riskLevel: n.riskLevel,
                complexity: n.complexity,
                testCoverage: n.testCoverage,
                description: n.description,
            } satisfies CustomNodeData,
        }));

        const riskEdgeColors: Record<string, string> = {
            LOW: '#34d399',
            MEDIUM: '#fbbf24',
            HIGH: '#fb7185',
            CRITICAL: '#fb7185',
        };

        const nodeMap = Object.fromEntries(blastNodes.map(n => [n.id, n]));

        const flowEdges: Edge[] = apiEdges.map((e, i) => {
            const targetRisk = nodeMap[e.target]?.riskLevel ?? 'LOW';
            return {
                id: `e-${i}`,
                source: e.source,
                target: e.target,
                animated: true,
                style: { stroke: riskEdgeColors[targetRisk], strokeWidth: 1.5, opacity: 0.6 },
                markerEnd: { type: MarkerType.ArrowClosed, color: riskEdgeColors[targetRisk], width: 14, height: 14 },
            };
        });

        return { flowNodes, flowEdges, blastNodes };
    }, [data]);

    // Use controlled state so we can update when data arrives
    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

    // Sync derived nodes/edges into React Flow state when data changes
    useEffect(() => {
        if (flowNodes.length > 0) {
            setNodes(flowNodes);
            setEdges(flowEdges);
        }
    }, [flowNodes, flowEdges, setNodes, setEdges]);

    const onNodeClick: NodeMouseHandler = useCallback(
        (_event, node) => {
            const blastNode = blastNodes.find(n => n.id === node.id) ?? null;
            setSelectedNodeId(node.id);
            onNodeSelect(blastNode);
        },
        [onNodeSelect, blastNodes],
    );

    const onPaneClick = useCallback(() => {
        setSelectedNodeId(null);
        onNodeSelect(null);
    }, [onNodeSelect]);

    if (isLoading) return (
        <div className="h-full w-full rounded-2xl border border-white/[0.06] bg-black">
            <LoadingState message="Loading graph..." />
        </div>
    );
    if (isError) return (
        <div className="h-full w-full rounded-2xl border border-white/[0.06] bg-black">
            <ErrorState onRetry={() => refetch()} />
        </div>
    );

    return (
        <div className="h-full w-full rounded-2xl border border-white/[0.06] bg-black">
            <ReactFlow
                nodes={nodes.map(n => ({ ...n, selected: n.id === selectedNodeId }))}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.3 }}
                minZoom={0.1}
                maxZoom={1.5}
                proOptions={{ hideAttribution: true }}
            >
                <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="rgba(255,255,255,0.04)" />
                <Controls
                    showInteractive={false}
                    className="!bottom-4 !left-4"
                />
                <MiniMap
                    nodeStrokeWidth={3}
                    pannable
                    zoomable
                    className="!bottom-4 !right-4"
                    nodeColor={(node) => {
                        const d = node.data as unknown as CustomNodeData;
                        switch (d.riskLevel) {
                            case 'CRITICAL': return '#fb7185';
                            case 'HIGH': return '#fb7185';
                            case 'MEDIUM': return '#fbbf24';
                            default: return '#34d399';
                        }
                    }}
                />
            </ReactFlow>
        </div>
    );
}
