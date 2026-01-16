import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000";

export interface GraphNode {
  id: string;
  name: string;
  val: number;
  group: number | null;
  // Added by react-force-graph at runtime
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  relationships: string[];
  evidences: string[];
  post_urls: string[];
  curvature: number;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

async function fetchForceGraph(): Promise<GraphData> {
  const response = await fetch(`${API_BASE_URL}/relationships/graph/force`);
  if (!response.ok) {
    throw new Error("Failed to fetch force graph data");
  }
  return response.json();
}

export function useForceGraph() {
  return useQuery({
    queryKey: ["force-graph"],
    queryFn: fetchForceGraph,
  });
}
