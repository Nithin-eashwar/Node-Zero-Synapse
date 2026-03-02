import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { vi, describe, it, expect } from 'vitest';

import BlastRadiusGraph from '../src/components/blast-radius/BlastRadiusGraph';
import type { CondensedGraphResponse, FullGraphResponse } from '../src/types';

const condensedData: CondensedGraphResponse = {
    directory_nodes: [
        {
            id: 'backend/api',
            type: 'directory',
            label: 'backend/api',
            file_count: 1,
            entity_count: 2,
            risk_level: 'HIGH',
            total_complexity: 11,
        },
        {
            id: 'backend/ai',
            type: 'directory',
            label: 'backend/ai',
            file_count: 1,
            entity_count: 1,
            risk_level: 'MEDIUM',
            total_complexity: 4,
        },
    ],
    directory_edges: [],
    files_by_directory: {
        'backend/api': [
            {
                id: 'backend/api/main.py',
                type: 'file',
                label: 'main.py',
                full_path: 'backend/api/main.py',
                directory: 'backend/api',
                entity_count: 2,
                risk_level: 'HIGH',
                total_complexity: 11,
            },
        ],
        'backend/ai': [
            {
                id: 'backend/ai/rag.py',
                type: 'file',
                label: 'rag.py',
                full_path: 'backend/ai/rag.py',
                directory: 'backend/ai',
                entity_count: 1,
                risk_level: 'MEDIUM',
                total_complexity: 4,
            },
        ],
    },
    file_edges: [],
    entities_by_file: {
        'backend/api/main.py': [
            {
                id: '.\\backend\\api\\main.py:load_data',
                name: 'load_data',
                type: 'function',
                risk_level: 'HIGH',
                complexity: 6,
                degree: 7,
                line: 42,
            },
            {
                id: '.\\backend\\api\\main.py:get_condensed_graph',
                name: 'get_condensed_graph',
                type: 'function',
                risk_level: 'MEDIUM',
                complexity: 5,
                degree: 4,
                line: 120,
            },
        ],
        'backend/ai/rag.py': [
            {
                id: '.\\backend\\ai\\rag.py:RAGPipeline.ask',
                name: 'ask',
                type: 'function',
                risk_level: 'MEDIUM',
                complexity: 4,
                degree: 3,
                line: 30,
            },
        ],
    },
    entity_edges: [
        {
            source: '.\\backend\\api\\main.py:load_data',
            target: '.\\backend\\api\\main.py:get_condensed_graph',
        },
    ],
};

const fullData: FullGraphResponse = {
    nodes: [],
    edges: [],
};

vi.mock('../src/lib/hooks', () => ({
    useFullGraph: () => ({
        data: fullData,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
    }),
    useCondensedGraph: () => ({
        data: condensedData,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
    }),
}));

vi.mock('@xyflow/react', () => {
    const useNodesState = (initial: unknown[]) => {
        const [nodes, setNodes] = React.useState(initial);
        return [nodes, setNodes, vi.fn()] as const;
    };

    const useEdgesState = (initial: unknown[]) => {
        const [edges, setEdges] = React.useState(initial);
        return [edges, setEdges, vi.fn()] as const;
    };

    return {
        ReactFlow: ({ nodes, onNodeClick, onNodeDoubleClick, children }: any) => (
            <div>
                {nodes.map((node: any) => (
                    <button
                        key={node.id}
                        data-testid={`node-${node.id}`}
                        data-node-type={node.type}
                        onClick={(event) => onNodeClick?.(event, node)}
                        onDoubleClick={(event) => onNodeDoubleClick?.(event, node)}
                    >
                        {node.id}
                    </button>
                ))}
                {children}
            </div>
        ),
        Background: () => null,
        Controls: () => null,
        MiniMap: () => null,
        useNodesState,
        useEdgesState,
        MarkerType: { ArrowClosed: 'arrow' },
        BackgroundVariant: { Dots: 'dots' },
    };
});

describe('BlastRadiusGraph hierarchy interactions', () => {
    it('expands and collapses layers deterministically', async () => {
        const onNodeSelect = vi.fn();
        render(<BlastRadiusGraph onNodeSelect={onNodeSelect} viewMode="hierarchy" />);

        await waitFor(() => {
            const directoryNodes = document.querySelectorAll('[data-node-type="directory"]');
            expect(directoryNodes.length).toBe(2);
        });

        fireEvent.click(screen.getByText('backend/api'));
        await waitFor(() => {
            const fileNodes = document.querySelectorAll('[data-node-type="file"]');
            expect(fileNodes.length).toBe(1);
        });

        fireEvent.doubleClick(screen.getByText('backend/api/main.py'));
        await waitFor(() => {
            const entityNodes = document.querySelectorAll('[data-node-type="custom"]');
            expect(entityNodes.length).toBe(2);
        });

        fireEvent.doubleClick(screen.getByText('backend/api/main.py'));
        await waitFor(() => {
            const entityNodes = document.querySelectorAll('[data-node-type="custom"]');
            expect(entityNodes.length).toBe(0);
        });

        fireEvent.click(screen.getByText('backend/api'));
        await waitFor(() => {
            const fileNodes = document.querySelectorAll('[data-node-type="file"]');
            expect(fileNodes.length).toBe(0);
        });
    });
});
