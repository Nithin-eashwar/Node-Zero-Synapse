import { createContext, useContext, useMemo, useRef, useState, useCallback, type ReactNode } from 'react';

interface Adjacency {
    parents: Record<string, Set<string>>;
    children: Record<string, Set<string>>;
}

interface HoverContextValue {
    hoveredNodeId: string | null;
    adjacency: Adjacency;
    /** Returns true if this node should be dimmed given current hover state */
    isDimmed: (nodeId: string) => boolean;
    /** Returns true if this node is a direct neighbour of the hovered node */
    isHighlighted: (nodeId: string) => boolean;
    /** Returns true if this edge should be dimmed */
    isEdgeDimmed: (sourceId: string, targetId: string) => boolean;
}

const HoverContext = createContext<HoverContextValue>({
    hoveredNodeId: null,
    adjacency: { parents: {}, children: {} },
    isDimmed: () => false,
    isHighlighted: () => false,
    isEdgeDimmed: () => false,
});

export function useHover() {
    return useContext(HoverContext);
}

interface HoverProviderProps {
    adjacency: Adjacency;
    children: ReactNode;
}

export function HoverProvider({ adjacency, children }: HoverProviderProps) {
    const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
    // Store the connected set for the current hover in a ref so helper fns
    // don't need to recompute on every call — O(1) Set.has() lookups.
    const connectedRef = useRef<Set<string>>(new Set());
    const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Exposed setter with debounce — call this from onNodeMouseEnter / Leave
    const setHover = useCallback((id: string | null) => {
        if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
        hoverTimerRef.current = setTimeout(() => {
            if (!id) {
                connectedRef.current = new Set();
                setHoveredNodeId(null);
                return;
            }
            const parentSet = adjacency.parents[id] ?? new Set();
            const childSet = adjacency.children[id] ?? new Set();
            connectedRef.current = new Set([id, ...parentSet, ...childSet]);
            setHoveredNodeId(id);
        }, 60);
    }, [adjacency]);

    const isDimmed = useCallback((nodeId: string) => {
        if (!hoveredNodeId) return false;
        return !connectedRef.current.has(nodeId);
    }, [hoveredNodeId]);

    const isHighlighted = useCallback((nodeId: string) => {
        if (!hoveredNodeId) return false;
        return connectedRef.current.has(nodeId) && nodeId !== hoveredNodeId;
    }, [hoveredNodeId]);

    const isEdgeDimmed = useCallback((source: string, target: string) => {
        if (!hoveredNodeId) return false;
        return !(
            (source === hoveredNodeId && connectedRef.current.has(target)) ||
            (target === hoveredNodeId && connectedRef.current.has(source))
        );
    }, [hoveredNodeId]);

    const value = useMemo<HoverContextValue>(() => ({
        hoveredNodeId,
        adjacency,
        isDimmed,
        isHighlighted,
        isEdgeDimmed,
    }), [hoveredNodeId, adjacency, isDimmed, isHighlighted, isEdgeDimmed]);

    return (
        <HoverContext.Provider value={value}>
            {/* Attach setHover to the context so graph component can call it */}
            <SetHoverContext.Provider value={setHover}>
                {children}
            </SetHoverContext.Provider>
        </HoverContext.Provider>
    );
}

// Separate context for the setter so consumers that only set don't re-render on hover changes
const SetHoverContext = createContext<(id: string | null) => void>(() => {});
export function useSetHover() {
    return useContext(SetHoverContext);
}
