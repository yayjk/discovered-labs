import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { useRelationshipGraph, countRelationships, type Entity, type GroupedRelationship } from "@/hooks/use-relationship-graph";
import { useAppStore } from "@/store/useAppStore";

function RelationshipGroup({ group }: { group: GroupedRelationship }) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-semibold px-3 py-1 rounded bg-primary/20 text-primary">
          {group.relationship_type}
        </span>
        <span className="text-xs text-muted-foreground">({group.details.length})</span>
      </div>
      <div className="space-y-2 ml-2">
        {group.details.map((detail, idx) => (
          <div key={idx} className="border border-border rounded-lg p-3 bg-card">
            <p className="text-foreground font-medium mb-2">{detail.related_entity}</p>
            {detail.evidences.length > 0 && (
              <div className="mb-2">
                <p className="text-xs font-medium text-muted-foreground mb-1">Evidence:</p>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {detail.evidences.map((evidence, i) => (
                    <li key={i} className="pl-2 border-l-2 border-border">{evidence}</li>
                  ))}
                </ul>
              </div>
            )}
            {detail.post_urls.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {detail.post_urls.map((url, i) => (
                  <a
                    key={i}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-400 hover:text-blue-300 hover:underline transition-colors"
                  >
                    Post {i + 1} →
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function RelationshipList({ relationships }: { relationships: GroupedRelationship[] }) {
  if (relationships.length === 0) {
    return (
      <p className="text-muted-foreground text-sm py-4">No relationships found.</p>
    );
  }

  return (
    <div className="space-y-4">
      {relationships.map((group, index) => (
        <RelationshipGroup key={index} group={group} />
      ))}
    </div>
  );
}

type RelationshipTab = "referenced-by" | "references";

function EntityDetails({ entity, onClose }: { entity: Entity; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState<RelationshipTab>("referenced-by");
  
  const referencedByCount = countRelationships(entity.left_relationships);
  const referencesCount = countRelationships(entity.right_relationships);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-4 pb-4 border-b border-border">
        <h3 className="text-xl font-bold text-foreground">{entity.entity_name}</h3>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground transition-colors text-2xl leading-none"
        >
          ×
        </button>
      </div>
      
      {/* Tabs */}
      <div className="flex gap-1 mb-4 p-1 bg-muted rounded-lg">
        <button
          onClick={() => setActiveTab("referenced-by")}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "referenced-by"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Referenced By ({referencedByCount})
        </button>
        <button
          onClick={() => setActiveTab("references")}
          className={`flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors ${
            activeTab === "references"
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          References ({referencesCount})
        </button>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === "referenced-by" ? (
          <RelationshipList relationships={entity.left_relationships} />
        ) : (
          <RelationshipList relationships={entity.right_relationships} />
        )}
      </div>
    </div>
  );
}

export function EntityExplorerView() {
  const selectedReport = useAppStore((state) => state.selectedReport);
  const { data: entities, isLoading, error } = useRelationshipGraph(selectedReport || "tesla");
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col items-center gap-4 p-4">
        <h2 className="text-3xl font-bold text-foreground">Entity Explorer</h2>
        <div className="w-full max-w-4xl space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 p-4">
        <h2 className="text-3xl font-bold text-foreground">Entity Explorer</h2>
        <p className="text-destructive">Failed to load entities. Please try again.</p>
      </div>
    );
  }

  const sortedEntities = [...(entities || [])].sort((a, b) => {
    const totalA = countRelationships(a.left_relationships) + countRelationships(a.right_relationships);
    const totalB = countRelationships(b.left_relationships) + countRelationships(b.right_relationships);
    return totalB - totalA;
  });

  return (
    <div className="flex flex-1 gap-4 p-4 h-full">
      {/* Left Section - Entity Table */}
      <div className={`flex flex-col ${selectedEntity ? 'w-1/2' : 'w-full'} transition-all duration-300`}>
        <h2 className="text-3xl font-bold text-foreground mb-4 text-center">Entity Explorer</h2>
        <div className="flex-1 overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Entity</TableHead>
                <TableHead className="text-right">Incoming</TableHead>
                <TableHead className="text-right">Outgoing</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedEntities.map((entity) => {
                const leftCount = countRelationships(entity.left_relationships);
                const rightCount = countRelationships(entity.right_relationships);
                return (
                  <TableRow
                    key={entity.entity_name}
                    className={`cursor-pointer hover:bg-muted/50 ${
                      selectedEntity?.entity_name === entity.entity_name ? 'bg-muted' : ''
                    }`}
                    onClick={() => setSelectedEntity(entity)}
                  >
                    <TableCell className="font-medium">{entity.entity_name}</TableCell>
                    <TableCell className="text-right">{leftCount}</TableCell>
                    <TableCell className="text-right">{rightCount}</TableCell>
                    <TableCell className="text-right">{leftCount + rightCount}</TableCell>
                  </TableRow>
                );
              })}
              {sortedEntities.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    No entities found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Right Section - Entity Details (collapsed by default) */}
      {selectedEntity && (
        <div className="w-1/2 border-l border-border pl-4 overflow-hidden">
          <EntityDetails entity={selectedEntity} onClose={() => setSelectedEntity(null)} />
        </div>
      )}
    </div>
  );
}
