import { useState, useCallback, useMemo, useEffect } from "react";
import {
  ReactFlow,
  Background,
  useNodesState,
  useEdgesState,
  MarkerType,
  getBezierPath,
  BaseEdge,
} from "@xyflow/react";
import type { Node, Edge, EdgeProps } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { useForceGraph, type GraphLink } from "@/hooks/use-force-graph";
import { Skeleton } from "@/components/ui/skeleton";

// Color palette for node groups
const GROUP_COLORS = [
  "#ef4444", "#f97316", "#eab308", "#22c55e", "#14b8a6",
  "#3b82f6", "#8b5cf6", "#ec4899", "#6366f1", "#84cc16"
];

interface SelectedEdge {
  source: string;
  target: string;
  relationships: string[];
  evidences: string[];
  post_urls: string[];
}

// Custom clickable edge component
function ClickableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style,
  markerEnd,
  data,
}: EdgeProps) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const handleClick = data?.onClick as (() => void) | undefined;

  return (
    <>
      {/* Invisible wider path for easier clicking */}
      <path
        id={`${id}-hitarea`}
        d={edgePath}
        fill="none"
        strokeWidth={20}
        stroke="transparent"
        style={{ cursor: "pointer" }}
        onClick={() => handleClick?.()}
      />
      <BaseEdge id={id} path={edgePath} style={style} markerEnd={markerEnd} />
    </>
  );
}

const edgeTypes = {
  clickable: ClickableEdge,
};

// Layout nodes using dagre
function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction = "TB"
): { nodes: Node[]; edges: Edge[] } {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 120;
  const nodeHeight = 40;

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 100,
    ranksep: 150,
    edgesep: 50,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

function EdgeDetailsPanel({ edge, onClose }: { edge: SelectedEdge; onClose: () => void }) {
  return (
    <div className="h-full flex flex-col p-4">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-border">
        <div>
          <h3 className="text-lg font-bold text-foreground">
            {edge.source} → {edge.target}
          </h3>
          <div className="flex flex-wrap gap-1 mt-2">
            {edge.relationships.map((rel, i) => (
              <span key={i} className="text-xs font-medium px-2 py-1 rounded bg-primary/20 text-primary">
                {rel}
              </span>
            ))}
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground transition-colors text-2xl leading-none"
        >
          ×
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-4">
        {edge.evidences.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-2">
              Evidence ({edge.evidences.length})
            </h4>
            <ul className="space-y-2">
              {edge.evidences.map((evidence, i) => (
                <li key={i} className="text-sm text-muted-foreground pl-3 border-l-2 border-border">
                  {evidence}
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {edge.post_urls.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-foreground mb-2">
              Source Posts ({edge.post_urls.length})
            </h4>
            <ul className="space-y-2">
              {edge.post_urls.map((url, i) => (
                <li key={i}>
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-400 hover:text-blue-300 hover:underline transition-colors break-all"
                  >
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
        
        {edge.evidences.length === 0 && edge.post_urls.length === 0 && (
          <p className="text-muted-foreground text-sm">No evidence or sources available for this relationship.</p>
        )}
      </div>
    </div>
  );
}

export function RelationshipGraphViewerView() {
  const { data, isLoading, error } = useForceGraph();
  const [selectedEdge, setSelectedEdge] = useState<SelectedEdge | null>(null);

  const handleEdgeClick = useCallback((_event: React.MouseEvent, edge: Edge) => {
    const edgeData = edge.data as { link: GraphLink } | undefined;
    if (!edgeData?.link) return;
    
    const link = edgeData.link;
    const sourceId = typeof link.source === "object" ? link.source.id : link.source;
    const targetId = typeof link.target === "object" ? link.target.id : link.target;
    
    setSelectedEdge({
      source: sourceId,
      target: targetId,
      relationships: link.relationships,
      evidences: link.evidences,
      post_urls: link.post_urls
    });
  }, []);

  const { nodes: layoutedNodes, edges: layoutedEdges } = useMemo(() => {
    if (!data) return { nodes: [], edges: [] };

    // Create nodes
    const nodes: Node[] = data.nodes.map((node) => ({
      id: node.id,
      data: { label: node.name },
      position: { x: 0, y: 0 },
      style: {
        background: GROUP_COLORS[node.group ?? 0],
        color: "#ffffff",
        border: "1px solid #ffffff",
        borderRadius: "8px",
        padding: "8px 12px",
        fontSize: "12px",
        fontWeight: 500,
        width: "auto",
        minWidth: "80px",
        textAlign: "center" as const,
      },
      draggable: false,
      selectable: false,
      connectable: false,
    }));

    // Create edges
    const edges: Edge[] = data.links.map((link, index) => {
      const sourceId = typeof link.source === "object" ? link.source.id : link.source;
      const targetId = typeof link.target === "object" ? link.target.id : link.target;
      
      return {
        id: `edge-${index}`,
        source: sourceId,
        target: targetId,
        type: "clickable",
        animated: false,
        style: { stroke: "#666666", strokeWidth: 2, cursor: "pointer" },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: "#666666",
          width: 15,
          height: 15,
        },
        data: {
          link: link,
        },
      };
    });

    // Apply layout
    return getLayoutedElements(nodes, edges, "LR");
  }, [data]);

  const [nodes, setNodes] = useNodesState<Node>([]);
  const [edges, setEdges] = useEdgesState<Edge>([]);

  // Update nodes and edges when layout changes
  useEffect(() => {
    setNodes(layoutedNodes);
    setEdges(layoutedEdges);
  }, [layoutedNodes, layoutedEdges, setNodes, setEdges]);

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col items-center gap-4 p-4">
        <h2 className="text-3xl font-bold text-foreground">Relationship Graph</h2>
        <Skeleton className="w-full h-[500px]" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-4">
        <h2 className="text-3xl font-bold text-foreground">Relationship Graph</h2>
        <p className="text-destructive">Failed to load graph data. Please try again.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 h-full overflow-hidden" style={{ minHeight: "500px" }}>
      {/* Graph Container */}
      <div 
        className={`${selectedEdge ? 'w-3/5' : 'w-full'} h-full transition-all duration-300`}
        style={{ minHeight: "500px" }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          edgeTypes={edgeTypes}
          onEdgeClick={handleEdgeClick}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={true}
          panOnDrag={true}
          zoomOnScroll={true}
          zoomOnPinch={true}
          minZoom={0.1}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
          style={{ background: "#09090b" }}
        >
          <Background color="#333333" gap={20} />
        </ReactFlow>
      </div>

      {/* Edge Details Panel */}
      {selectedEdge && (
        <div className="w-2/5 border-l border-border overflow-y-auto h-full">
          <EdgeDetailsPanel edge={selectedEdge} onClose={() => setSelectedEdge(null)} />
        </div>
      )}
    </div>
  );
}
