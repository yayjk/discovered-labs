import { useState } from "react"
import { ChevronDown, ChevronRight, FileText, Network, ScanSearch, Search } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  useSidebar,
} from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { InputView } from "@/components/InputView"
import { EntityExplorerView } from "@/components/EntityExplorerView"
import { RelationshipGraphViewerView } from "@/components/RelationshipGraphViewerView"
import { useAppStore } from "@/store/useAppStore"
import { useReports } from "@/hooks/use-reports"

function SidebarHeaderContent() {
  const { state } = useSidebar()
  const isCollapsed = state === "collapsed"

  return (
    <SidebarHeader className="px-0">
      <h2 className="text-xl font-bold tracking-tight px-2 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:text-center">
        {isCollapsed ? "dl" : "discovered-labs"}
      </h2>
      {!isCollapsed && <Separator className="my-2" />}
    </SidebarHeader>
  )
}

function App() {
  const screenState = useAppStore((state) => state.screenState)
  const setScreenState = useAppStore((state) => state.setScreenState)
  const selectedReport = useAppStore((state) => state.selectedReport)
  const setSelectedReport = useAppStore((state) => state.setSelectedReport)

  const analysisScreenState = useAppStore((state) => state.analysisScreenState)
  const generatingSlug = useAppStore((state) => state.generatingSlug)

  const [reportsExpanded, setReportsExpanded] = useState(true)
  const [expandedReports, setExpandedReports] = useState<Record<string, boolean>>({})

  const { data: reports } = useReports()

  // Hide the currently-generating report from the sidebar until extraction is fully done
  const visibleReports = reports?.filter(
    (r) => !(r.name === generatingSlug && analysisScreenState !== "finish")
  )

  const toggleReport = (name: string) => {
    setExpandedReports((prev) => ({ ...prev, [name]: !prev[name] }))
  }

  const handleSubItemClick = (reportName: string, screen: typeof screenState) => {
    setSelectedReport(reportName)
    setScreenState(screen)
  }

  return (
    <div className="dark">
      <SidebarProvider>
        <Sidebar collapsible="icon">
          <SidebarHeaderContent />
          <SidebarContent className="px-0">
            <SidebarMenu className="gap-3">
              {/* Search */}
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => {
                    setScreenState("input")
                    setSelectedReport(null)
                  }}
                  isActive={screenState === "input"}
                >
                  <Search />
                  <span>Search</span>
                </SidebarMenuButton>
              </SidebarMenuItem>

              {/* Reports — driven by GET /reports */}
              <SidebarMenuItem>
                <SidebarMenuButton onClick={() => setReportsExpanded(!reportsExpanded)}>
                  <FileText />
                  <span>Reports</span>
                  {reportsExpanded ? <ChevronDown className="ml-auto" /> : <ChevronRight className="ml-auto" />}
                </SidebarMenuButton>

                {reportsExpanded && (
                  <SidebarMenuSub>
                    {(!visibleReports || visibleReports.length === 0) && (
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton className="cursor-default opacity-50 pointer-events-none">
                          <span className="text-xs">No reports yet</span>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    )}

                    {visibleReports?.map((report) => (
                      <SidebarMenuSubItem key={report.name}>
                        <SidebarMenuSubButton onClick={() => toggleReport(report.name)}>
                          <span className="capitalize">{report.name.replace(/_/g, " ")}</span>
                          {expandedReports[report.name] ? (
                            <ChevronDown className="ml-auto" />
                          ) : (
                            <ChevronRight className="ml-auto" />
                          )}
                        </SidebarMenuSubButton>

                        {expandedReports[report.name] && (
                          <SidebarMenuSub>
                            <SidebarMenuSubItem>
                              <SidebarMenuSubButton
                                onClick={() => handleSubItemClick(report.name, "entity_explorer")}
                                isActive={selectedReport === report.name && screenState === "entity_explorer"}
                              >
                                <ScanSearch className="h-4 w-4" />
                                <span>Entity Explorer</span>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                            <SidebarMenuSubItem>
                              <SidebarMenuSubButton
                                onClick={() => handleSubItemClick(report.name, "relationship_graph_viewer")}
                                isActive={selectedReport === report.name && screenState === "relationship_graph_viewer"}
                              >
                                <Network className="h-4 w-4" />
                                <span>Relationship Viewer</span>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          </SidebarMenuSub>
                        )}
                      </SidebarMenuSubItem>
                    ))}
                  </SidebarMenuSub>
                )}
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarContent>
        </Sidebar>
        <SidebarInset>
          <header className="flex h-16 shrink-0 items-center gap-2 border-b-2 border-sidebar-border px-4">
            <SidebarTrigger className="-ml-1" />
            <div className="flex-1" />
          </header>
          <div className="flex flex-1 flex-col gap-4 p-4">
            {screenState === "input" && <InputView />}
            {screenState === "entity_explorer" && <EntityExplorerView />}
            {screenState === "relationship_graph_viewer" && <RelationshipGraphViewerView />}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  )
}

export default App
