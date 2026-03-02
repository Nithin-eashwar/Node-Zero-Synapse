import { useCallback, useEffect, useMemo, useState } from 'react';
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
import DirectoryNode from './DirectoryNode';
import FileNode from './FileNode';
import type { CustomNodeData } from './CustomNode';
import type { DirectoryNodeData } from './DirectoryNode';
import type { FileNodeData } from './FileNode';
import { useFullGraph, useCondensedGraph } from '../../lib/hooks';
import type {
    BlastRadiusNode,
    CondensedGraphResponse,
    FullGraphNode,
    RiskLevel,
} from '../../types';
import { LoadingState, ErrorState } from '../ui/StatusStates';

interface BlastRadiusGraphProps {
    onNodeSelect: (node: BlastRadiusNode | null) => void;
    viewMode: 'hierarchy' | 'full';
}

const nodeTypes = {
    custom: CustomNode,
    directory: DirectoryNode,
    file: FileNode,
};

const riskEdgeColors: Record<RiskLevel, string> = {
    LOW: '#34d399',
    MEDIUM: '#fbbf24',
    HIGH: '#fb7185',
    CRITICAL: '#ef4444',
};

function getRiskFromDegree(total: number): RiskLevel {
    if (total >= 8) return 'CRITICAL';
    if (total >= 5) return 'HIGH';
    if (total >= 2) return 'MEDIUM';
    return 'LOW';
}

function inferNodeType(node: FullGraphNode): BlastRadiusNode['type'] {
    if (node.type === 'class' || node.type === 'function' || node.type === 'module') {
        return node.type;
    }
    if (node.id.includes('.') || (node.id.length > 0 && node.id[0] === node.id[0].toUpperCase())) {
        return 'class';
    }
    return 'function';
}

function useFullViewGraph(data: ReturnType<typeof useFullGraph>['data']) {
    return useMemo(() => {
        if (!data) {
            return { flowNodes: [] as Node[], flowEdges: [] as Edge[], blastNodes: [] as BlastRadiusNode[] };
        }

        const apiNodes = data.nodes ?? [];
        const apiEdges = data.edges ?? [];

        const outDegree: Record<string, number> = {};
        const inDegree: Record<string, number> = {};
        apiEdges.forEach((edge) => {
            outDegree[edge.source] = (outDegree[edge.source] ?? 0) + 1;
            inDegree[edge.target] = (inDegree[edge.target] ?? 0) + 1;
        });

        const blastNodes: BlastRadiusNode[] = apiNodes.map((node) => {
            const out = outDegree[node.id] ?? 0;
            const inn = inDegree[node.id] ?? 0;
            const total = out + inn;
            const line = Array.isArray(node.range) && node.range.length > 0 ? node.range[0] : 0;
            return {
                id: node.id,
                label: node.id,
                type: inferNodeType(node),
                riskLevel: getRiskFromDegree(total),
                complexity: out,
                testCoverage: 0,
                description: `File: ${node.file ?? 'unknown'} (line ${line}). ${out} outgoing, ${inn} incoming edges.`,
            };
        });

        const cols = Math.max(1, Math.ceil(Math.sqrt(apiNodes.length)));
        const flowNodes: Node[] = blastNodes.map((node, index) => ({
            id: node.id,
            type: 'custom',
            position: {
                x: (index % cols) * 240 + (Math.random() * 40 - 20),
                y: Math.floor(index / cols) * 160 + (Math.random() * 30 - 15),
            },
            data: {
                label: node.label,
                nodeType: node.type,
                riskLevel: node.riskLevel,
                complexity: node.complexity,
                testCoverage: node.testCoverage,
                description: node.description,
            } satisfies CustomNodeData,
        }));

        const nodeMap = Object.fromEntries(blastNodes.map((node) => [node.id, node]));
        const flowEdges: Edge[] = apiEdges.map((edge, index) => {
            const targetRisk = nodeMap[edge.target]?.riskLevel ?? 'LOW';
            return {
                id: `e-${index}`,
                source: edge.source,
                target: edge.target,
                animated: true,
                style: { stroke: riskEdgeColors[targetRisk], strokeWidth: 1.5, opacity: 0.6 },
                markerEnd: { type: MarkerType.ArrowClosed, color: riskEdgeColors[targetRisk], width: 14, height: 14 },
            };
        });

        return { flowNodes, flowEdges, blastNodes };
    }, [data]);
}

function buildHierarchyGraph(
    graphData: CondensedGraphResponse,
    expandedDirs: Set<string>,
    expandedFiles: Set<string>,
): { nodes: Node[]; edges: Edge[] } {
    const nodes: Node[] = [];
    const edges: Edge[] = [];

    const directoryColumns = Math.max(1, Math.ceil(Math.sqrt(graphData.directory_nodes.length)));
    for (let index = 0; index < graphData.directory_nodes.length; index++) {
        const directory = graphData.directory_nodes[index];
        const isExpanded = expandedDirs.has(directory.id);
        const directoryX = (index % directoryColumns) * 340;
        const directoryY = Math.floor(index / directoryColumns) * 300;

        nodes.push({
            id: directory.id,
            type: 'directory',
            position: { x: directoryX, y: directoryY },
            data: {
                label: directory.label,
                fileCount: directory.file_count,
                entityCount: directory.entity_count,
                riskLevel: directory.risk_level,
                totalComplexity: directory.total_complexity,
                expanded: isExpanded,
            } satisfies DirectoryNodeData,
        });

        if (!isExpanded) {
            continue;
        }

        const files = graphData.files_by_directory[directory.id] ?? [];
        const fileColumns = Math.max(1, Math.ceil(Math.sqrt(files.length)));
        for (let fileIndex = 0; fileIndex < files.length; fileIndex++) {
            const fileNode = files[fileIndex];
            const isFileExpanded = expandedFiles.has(fileNode.id);
            const fileX = directoryX + (fileIndex % fileColumns) * 260;
            const fileY = directoryY + 140 + Math.floor(fileIndex / fileColumns) * 260;

            nodes.push({
                id: fileNode.id,
                type: 'file',
                position: { x: fileX, y: fileY },
                data: {
                    label: fileNode.label,
                    fullPath: fileNode.full_path,
                    entityCount: fileNode.entity_count,
                    riskLevel: fileNode.risk_level,
                    totalComplexity: fileNode.total_complexity,
                    expanded: isFileExpanded,
                } satisfies FileNodeData,
            });

            if (!isFileExpanded) {
                continue;
            }

            const entities = graphData.entities_by_file[fileNode.id] ?? [];
            const entityColumns = Math.max(1, Math.ceil(Math.sqrt(entities.length)));
            for (let entityIndex = 0; entityIndex < entities.length; entityIndex++) {
                const entity = entities[entityIndex];
                nodes.push({
                    id: entity.id,
                    type: 'custom',
                    position: {
                        x: fileX + (entityIndex % entityColumns) * 240,
                        y: fileY + 130 + Math.floor(entityIndex / entityColumns) * 140,
                    },
                    data: {
                        label: entity.name,
                        nodeType: entity.type === 'class' ? 'class' : 'function',
                        riskLevel: entity.risk_level,
                        complexity: entity.complexity,
                        testCoverage: 0,
                        description: `${entity.type} in ${fileNode.full_path} (line ${entity.line})`,
                    } satisfies CustomNodeData,
                });
            }
        }
    }

    const visibleNodeIds = new Set(nodes.map((node) => node.id));
    const entityToVisible: Record<string, string> = {};

    for (const directory of graphData.directory_nodes) {
        const files = graphData.files_by_directory[directory.id] ?? [];
        if (!expandedDirs.has(directory.id)) {
            for (const fileNode of files) {
                entityToVisible[fileNode.id] = directory.id;
                const entities = graphData.entities_by_file[fileNode.id] ?? [];
                for (const entity of entities) {
                    entityToVisible[entity.id] = directory.id;
                }
            }
            continue;
        }

        for (const fileNode of files) {
            if (!expandedFiles.has(fileNode.id)) {
                entityToVisible[fileNode.id] = fileNode.id;
                const entities = graphData.entities_by_file[fileNode.id] ?? [];
                for (const entity of entities) {
                    entityToVisible[entity.id] = fileNode.id;
                }
                continue;
            }

            entityToVisible[fileNode.id] = fileNode.id;
            const entities = graphData.entities_by_file[fileNode.id] ?? [];
            for (const entity of entities) {
                entityToVisible[entity.id] = entity.id;
            }
        }
    }

    const seenEdges = new Set<string>();
    let edgeIndex = 0;
    for (const edge of graphData.entity_edges) {
        const sourceVisible = entityToVisible[edge.source] ?? edge.source;
        const targetVisible = entityToVisible[edge.target] ?? edge.target;
        if (sourceVisible === targetVisible) continue;
        if (!visibleNodeIds.has(sourceVisible) || !visibleNodeIds.has(targetVisible)) continue;

        const key = `${sourceVisible}->${targetVisible}`;
        if (seenEdges.has(key)) continue;
        seenEdges.add(key);

        edges.push({
            id: `he-${edgeIndex++}`,
            source: sourceVisible,
            target: targetVisible,
            animated: true,
            style: { stroke: '#64748b', strokeWidth: 1.5, opacity: 0.5 },
            markerEnd: { type: MarkerType.ArrowClosed, color: '#64748b', width: 12, height: 12 },
        });
    }

    return { nodes, edges };
}

export default function BlastRadiusGraph({ onNodeSelect, viewMode }: BlastRadiusGraphProps) {
    const fullQuery = useFullGraph();
    const condensedQuery = useCondensedGraph();

    const isHierarchy = viewMode === 'hierarchy';
    const query = isHierarchy ? condensedQuery : fullQuery;

    const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());
    const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
    const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

    const fullView = useFullViewGraph(isHierarchy ? undefined : fullQuery.data);

    const { renderNodes, renderEdges, blastNodes } = useMemo(() => {
        if (isHierarchy) {
            if (!condensedQuery.data) {
                return { renderNodes: [] as Node[], renderEdges: [] as Edge[], blastNodes: [] as BlastRadiusNode[] };
            }
            const { nodes, edges } = buildHierarchyGraph(condensedQuery.data, expandedDirs, expandedFiles);
            return { renderNodes: nodes, renderEdges: edges, blastNodes: [] as BlastRadiusNode[] };
        }

        return { renderNodes: fullView.flowNodes, renderEdges: fullView.flowEdges, blastNodes: fullView.blastNodes };
    }, [isHierarchy, condensedQuery.data, expandedDirs, expandedFiles, fullView]);

    const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

    useEffect(() => {
        setNodes(renderNodes);
        setEdges(renderEdges);
    }, [renderNodes, renderEdges, setNodes, setEdges]);

    useEffect(() => {
        if (!selectedNodeId) return;
        if (renderNodes.some((node) => node.id === selectedNodeId)) return;
        setSelectedNodeId(null);
        onNodeSelect(null);
    }, [renderNodes, selectedNodeId, onNodeSelect]);

    const onNodeClick: NodeMouseHandler = useCallback(
        (_event, node) => {
            if (isHierarchy && node.type === 'directory') {
                const isCollapsing = expandedDirs.has(node.id);
                setExpandedDirs((prev) => {
                    const next = new Set(prev);
                    if (next.has(node.id)) {
                        next.delete(node.id);
                    } else {
                        next.add(node.id);
                    }
                    return next;
                });

                if (isCollapsing && condensedQuery.data) {
                    const fileIds = (condensedQuery.data.files_by_directory[node.id] ?? []).map((file) => file.id);
                    setExpandedFiles((prev) => {
                        const next = new Set(prev);
                        fileIds.forEach((fileId) => next.delete(fileId));
                        return next;
                    });
                }

                return;
            }

            if (!isHierarchy) {
                const blastNode = blastNodes.find((candidate) => candidate.id === node.id) ?? null;
                setSelectedNodeId(node.id);
                onNodeSelect(blastNode);
                return;
            }

            setSelectedNodeId(node.id);
            onNodeSelect(null);
        },
        [isHierarchy, expandedDirs, condensedQuery.data, blastNodes, onNodeSelect],
    );

    const onNodeDoubleClick: NodeMouseHandler = useCallback(
        (_event, node) => {
            if (!isHierarchy || node.type !== 'file') return;
            setExpandedFiles((prev) => {
                const next = new Set(prev);
                if (next.has(node.id)) {
                    next.delete(node.id);
                } else {
                    next.add(node.id);
                }
                return next;
            });
        },
        [isHierarchy],
    );

    const onPaneClick = useCallback(() => {
        setSelectedNodeId(null);
        onNodeSelect(null);
    }, [onNodeSelect]);

    useEffect(() => {
        setExpandedDirs(new Set());
        setExpandedFiles(new Set());
        setSelectedNodeId(null);
        onNodeSelect(null);
    }, [viewMode, onNodeSelect]);

    if (query.isLoading) {
        return (
            <div className="h-full w-full rounded-2xl border border-white/[0.06] bg-black">
                <LoadingState message="Loading graph..." />
            </div>
        );
    }

    if (query.isError) {
        return (
            <div className="h-full w-full rounded-2xl border border-white/[0.06] bg-black">
                <ErrorState onRetry={() => query.refetch()} />
            </div>
        );
    }

    return (
        <div className="h-full w-full rounded-2xl border border-white/[0.06] bg-black">
            <ReactFlow
                nodes={nodes.map((node) => ({ ...node, selected: node.id === selectedNodeId }))}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onNodeClick={onNodeClick}
                onNodeDoubleClick={onNodeDoubleClick}
                onPaneClick={onPaneClick}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.3 }}
                minZoom={0.1}
                maxZoom={1.5}
                proOptions={{ hideAttribution: true }}
            >
                <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="rgba(255,255,255,0.04)" />
                <Controls showInteractive={false} className="!bottom-4 !left-4" />
                <MiniMap
                    nodeStrokeWidth={3}
                    pannable
                    zoomable
                    className="!bottom-4 !right-4"
                    nodeColor={(node) => {
                        const data = node.data as { riskLevel?: RiskLevel; risk_level?: RiskLevel } | undefined;
                        const risk = data?.riskLevel ?? data?.risk_level ?? 'LOW';
                        switch (risk) {
                            case 'CRITICAL':
                                return '#ef4444';
                            case 'HIGH':
                                return '#fb7185';
                            case 'MEDIUM':
                                return '#fbbf24';
                            default:
                                return '#34d399';
                        }
                    }}
                />
            </ReactFlow>
        </div>
    );
}
