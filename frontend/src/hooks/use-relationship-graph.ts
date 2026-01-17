import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000";

export interface RelationshipDetail {
  related_entity: string;
  evidences: string[];
  post_urls: string[];
}

export interface GroupedRelationship {
  relationship_type: string;
  details: RelationshipDetail[];
}

export interface Entity {
  entity_name: string;
  left_relationships: GroupedRelationship[];
  right_relationships: GroupedRelationship[];
}

async function fetchRelationshipGraph(report: string): Promise<Entity[]> {
  const response = await fetch(`${API_BASE_URL}/relationships/graph?report=${report}`);
  if (!response.ok) {
    throw new Error("Failed to fetch relationship graph");
  }
  return response.json();
}

export function useRelationshipGraph(report: string = "tesla") {
  return useQuery({
    queryKey: ["relationship-graph", report],
    queryFn: () => fetchRelationshipGraph(report),
  });
}

// Helper to count total relationships
export function countRelationships(relationships: GroupedRelationship[]): number {
  return relationships.reduce((sum, group) => sum + group.details.length, 0);
}
