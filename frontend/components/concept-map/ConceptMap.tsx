"use client";

import "@xyflow/react/dist/style.css";
import {
  Handle,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import { useReducedMotion } from "framer-motion";
import { Maximize2 } from "lucide-react";
import { memo, useEffect, useMemo, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { ConceptMapData } from "@/lib/api";
import { cn } from "@/lib/utils";

// layout coordinates from the API are in [0, 1]; this is the canvas they are scaled to
const WIDTH = 560;
const HEIGHT = 420;

type ConceptNodeData = { label: string; weight: number; active: boolean; dimmed: boolean };
type ConceptFlowNode = Node<ConceptNodeData, "concept">;

// edges attach to one hidden handle in the centre of each node (a free-form concept map)
const hiddenHandle = { top: "50%", left: "50%", opacity: 0, width: 1, height: 1, minWidth: 0, minHeight: 0, border: 0 };

const ConceptNodeView = memo(function ConceptNodeView({ data }: NodeProps<ConceptFlowNode>) {
  return (
    <div
      className={cn(
        "max-w-[9rem] rounded-2xl border px-2.5 py-1 text-center leading-tight shadow-sm transition-[opacity,border-color,background-color] duration-300",
        data.active ? "border-signal bg-[color-mix(in_srgb,var(--signal)_16%,var(--card))]" : "border-rule bg-card",
        data.dimmed && "opacity-40",
      )}
      style={{ fontSize: 12 + Math.round(data.weight * 4), fontWeight: data.weight > 0.6 ? 600 : 400 }}
    >
      <Handle type="target" position={Position.Top} style={hiddenHandle} isConnectable={false} />
      {data.label}
      <Handle type="source" position={Position.Bottom} style={hiddenHandle} isConnectable={false} />
    </div>
  );
});

const nodeTypes = { concept: ConceptNodeView };

interface Props {
  data: ConceptMapData;
  /** node ids to highlight and zoom to (e.g. the concepts of the paragraph being read) */
  focus: string[];
  onNodeClick?: (id: string) => void;
  className?: string;
}

function Inner({ data, focus, onNodeClick, zoomToFocus }: Props & { zoomToFocus: boolean }) {
  const flow = useReactFlow();
  const reduce = useReducedMotion();
  const focusSet = useMemo(() => new Set(focus), [focus]);

  const nodes: ConceptFlowNode[] = useMemo(
    () =>
      data.nodes.map((n) => ({
        id: n.id,
        type: "concept",
        position: { x: n.x * WIDTH, y: n.y * HEIGHT },
        origin: [0.5, 0.5] as [number, number],
        data: { label: n.label, weight: n.weight, active: focusSet.has(n.id), dimmed: focusSet.size > 0 && !focusSet.has(n.id) },
        selectable: false,
      })),
    [data.nodes, focusSet],
  );

  const edges: Edge[] = useMemo(
    () =>
      data.edges.map((e) => {
        const on = focusSet.has(e.source) && focusSet.has(e.target);
        return {
          id: `${e.source}__${e.target}`,
          source: e.source,
          target: e.target,
          type: "straight",
          label: on || !zoomToFocus ? (e.label ?? undefined) : undefined,
          labelStyle: { fontSize: 11, fill: "var(--muted-foreground)" },
          labelBgStyle: { fill: "var(--card)" },
          style: {
            stroke: on ? "var(--signal)" : "var(--muted-foreground)",
            strokeOpacity: on ? 0.9 : focusSet.size ? 0.15 : 0.4,
            strokeWidth: Math.min(1 + e.weight * 0.5, 3),
          },
        };
      }),
    [data.edges, focusSet, zoomToFocus],
  );

  // zoom to the concepts of the paragraph being read (plus the concepts they link to)
  useEffect(() => {
    const ids = new Set(focus);
    if (zoomToFocus)
      for (const e of data.edges) {
        if (focusSet.has(e.source)) ids.add(e.target);
        if (focusSet.has(e.target)) ids.add(e.source);
      }
    const t = setTimeout(() => {
      void flow.fitView({
        nodes: zoomToFocus && ids.size ? [...ids].map((id) => ({ id })) : undefined,
        padding: 0.15,
        maxZoom: 1,
        duration: reduce ? 0 : 500,
      });
    }, 50);
    return () => clearTimeout(t);
  }, [focus, focusSet, data.edges, flow, reduce, zoomToFocus]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      minZoom={0.3}
      maxZoom={2}
      nodesConnectable={false}
      elementsSelectable={false}
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, n) => onNodeClick?.(n.id)}
      aria-label="Concept map"
    />
  );
}

/** Concept map: key concepts sized by centrality, linked when they share a sentence. */
export function ConceptMap(props: Props) {
  const [expanded, setExpanded] = useState(false);
  if (!props.data.nodes.length) {
    return <p className="text-sm text-muted-foreground">Not enough repeated concepts to draw a map yet.</p>;
  }
  return (
    <>
      <div className={cn("relative grid-paper h-80 overflow-hidden rounded-lg border border-rule", props.className)}>
        <ReactFlowProvider>
          <Inner {...props} zoomToFocus />
        </ReactFlowProvider>
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="absolute top-2 right-2 z-10 inline-flex items-center gap-1 rounded-md border border-rule bg-card/90 px-2 py-1 text-xs hover:bg-secondary"
          aria-label="Open the full concept map"
        >
          <Maximize2 className="size-3" /> Expand
        </button>
      </div>
      <Dialog open={expanded} onOpenChange={setExpanded}>
        <DialogContent className="sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle className="font-display text-3xl font-normal">Concept map</DialogTitle>
            <DialogDescription>
              Bigger concepts are more central to your document. Lines join concepts used in the same sentence, labelled with the verb that links them.
            </DialogDescription>
          </DialogHeader>
          <div className="grid-paper h-[70vh] overflow-hidden rounded-lg border border-rule">
            <ReactFlowProvider>
              <Inner
                {...props}
                zoomToFocus={false}
                onNodeClick={(id) => {
                  setExpanded(false);
                  props.onNodeClick?.(id);
                }}
              />
            </ReactFlowProvider>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
