import { useState, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useRelationshipGraph, countRelationships, type Entity, type GroupedRelationship } from "@/hooks/use-relationship-graph";
import { RelationshipGraphViewerView } from "@/components/RelationshipGraphViewerView";
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
  const dbPath = selectedReport ? `${selectedReport}.db` : "";
  const { data: entities, isLoading, error } = useRelationshipGraph(dbPath);
  const [selectedEntity, setSelectedEntity] = useState<Entity | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [showGraph, setShowGraph] = useState(false);
  const PAGE_SIZE = 15;

  const sortedEntities = useMemo(() => {
    return [...(entities || [])].sort((a, b) => {
      const totalA = countRelationships(a.left_relationships) + countRelationships(a.right_relationships);
      const totalB = countRelationships(b.left_relationships) + countRelationships(b.right_relationships);
      return totalB - totalA;
    });
  }, [entities]);

  const totalPages = Math.max(1, Math.ceil(sortedEntities.length / PAGE_SIZE));
  const paginatedEntities = sortedEntities.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  if (showGraph) {
    return (
      <div className="flex flex-1 flex-col min-h-0 overflow-hidden relative">
        <RelationshipGraphViewerView />
        <div className="sticky bottom-0 w-full py-3 px-4 bg-background border-t border-border flex justify-center z-10">
          <Button
            onClick={() => setShowGraph(false)}
            className="bg-blue-600 hover:bg-blue-700 text-white text-lg h-12 px-8 shadow-lg"
          >
            Show Entity Table
          </Button>
        </div>
      </div>
    );
  }

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

  return (
    <div className="flex flex-1 flex-col min-h-0 overflow-hidden relative">
      <div className="flex flex-1 gap-4 p-4 min-h-0 overflow-hidden">
        {/* Left Section - Entity Table */}
        <div className={`flex flex-col ${selectedEntity ? 'w-1/2' : 'w-full'} transition-all duration-300 min-h-0 overflow-y-auto justify-center`}>
          <h2 className="text-3xl font-bold text-foreground mb-4 text-center shrink-0">Entity Explorer</h2>
          <div className="flex flex-col items-center">
            <div className="w-full max-w-3xl">
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
                  {paginatedEntities.map((entity) => {
                    const leftCount = countRelationships(entity.left_relationships);
                    const rightCount = countRelationships(entity.right_relationships);
                    const isSelected = selectedEntity?.entity_name === entity.entity_name;
                    return (
                      <TableRow
                        key={entity.entity_name}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-blue-500/20 hover:bg-blue-500/30 text-blue-300'
                            : 'hover:bg-muted/50'
                        }`}
                        onClick={() => setSelectedEntity(entity)}
                      >
                        <TableCell className={`font-medium ${isSelected ? 'text-blue-300' : ''}`}>{entity.entity_name}</TableCell>
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

            {/* Pagination controls */}
            {totalPages > 1 && (
              <div className="flex items-center gap-2 mt-4 py-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="text-foreground hover:!text-blue-400 hover:!border-blue-400"
                >
                  Previous
                </Button>
                <span className="text-sm text-muted-foreground">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="text-foreground hover:!text-blue-400 hover:!border-blue-400"
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Right Section - Entity Details */}
        {selectedEntity && (
          <div className="w-1/2 border-l border-border pl-4 min-h-0 overflow-y-auto">
            <EntityDetails entity={selectedEntity} onClose={() => setSelectedEntity(null)} />
          </div>
        )}
      </div>

      {/* Sticky bottom button */}
      <div className="sticky bottom-0 w-full py-3 px-4 bg-background border-t border-border flex justify-center z-10">
        <Button
          onClick={() => setShowGraph(true)}
          className="bg-blue-600 hover:bg-blue-700 text-white text-lg h-12 px-8 shadow-lg"
        >
          Show Relationship Graph
        </Button>
      </div>
    </div>
  );
}
