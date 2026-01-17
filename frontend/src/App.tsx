import { useState } from "react"
import { ChevronDown, ChevronRight, FileText, Network, ScanSearch, Search, Users } from "lucide-react"
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
import { CommunitiesView } from "@/components/CommunitiesView"
import { EntityExplorerView } from "@/components/EntityExplorerView"
import { RelationshipGraphViewerView } from "@/components/RelationshipGraphViewerView"
import { useAppStore, type ReportType } from "@/store/useAppStore"

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
  
  const [reportsExpanded, setReportsExpanded] = useState(false)
  const [openAIExpanded, setOpenAIExpanded] = useState(false)
  const [teslaExpanded, setTeslaExpanded] = useState(false)

  const handleReportSubItemClick = (report: ReportType, screen: typeof screenState) => {
    setSelectedReport(report)
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

              {/* Reports */}
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => setReportsExpanded(!reportsExpanded)}
                >
                  <FileText />
                  <span>Reports</span>
                  {reportsExpanded ? <ChevronDown className="ml-auto" /> : <ChevronRight className="ml-auto" />}
                </SidebarMenuButton>
                
                {reportsExpanded && (
                  <SidebarMenuSub>
                    {/* OpenAI Report - only show if analysis is finished */}
                    {analysisScreenState === "finish" && (
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton
                          onClick={() => setOpenAIExpanded(!openAIExpanded)}
                        >
                          <span>OpenAI</span>
                          {openAIExpanded ? <ChevronDown className="ml-auto" /> : <ChevronRight className="ml-auto" />}
                        </SidebarMenuSubButton>
                        
                        {openAIExpanded && (
                          <SidebarMenuSub>
                            <SidebarMenuSubItem>
                              <SidebarMenuSubButton
                                onClick={() => handleReportSubItemClick("openai", "communities")}
                                isActive={selectedReport === "openai" && screenState === "communities"}
                              >
                                <Users className="h-4 w-4" />
                                <span>Communities</span>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                            <SidebarMenuSubItem>
                              <SidebarMenuSubButton
                                onClick={() => handleReportSubItemClick("openai", "entity_explorer")}
                                isActive={selectedReport === "openai" && screenState === "entity_explorer"}
                              >
                                <ScanSearch className="h-4 w-4" />
                                <span>Entity Explorer</span>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                            <SidebarMenuSubItem>
                              <SidebarMenuSubButton
                                onClick={() => handleReportSubItemClick("openai", "relationship_graph_viewer")}
                                isActive={selectedReport === "openai" && screenState === "relationship_graph_viewer"}
                              >
                                <Network className="h-4 w-4" />
                                <span>Relationship Viewer</span>
                              </SidebarMenuSubButton>
                            </SidebarMenuSubItem>
                          </SidebarMenuSub>
                        )}
                      </SidebarMenuSubItem>
                    )}

                    {/* Tesla Report */}
                    <SidebarMenuSubItem>
                      <SidebarMenuSubButton
                        onClick={() => setTeslaExpanded(!teslaExpanded)}
                      >
                        <span>Tesla</span>
                        {teslaExpanded ? <ChevronDown className="ml-auto" /> : <ChevronRight className="ml-auto" />}
                      </SidebarMenuSubButton>
                      
                      {teslaExpanded && (
                        <SidebarMenuSub>
                          <SidebarMenuSubItem>
                            <SidebarMenuSubButton
                              onClick={() => handleReportSubItemClick("tesla", "communities")}
                              isActive={selectedReport === "tesla" && screenState === "communities"}
                            >
                              <Users className="h-4 w-4" />
                              <span>Communities</span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                          <SidebarMenuSubItem>
                            <SidebarMenuSubButton
                              onClick={() => handleReportSubItemClick("tesla", "entity_explorer")}
                              isActive={selectedReport === "tesla" && screenState === "entity_explorer"}
                            >
                              <ScanSearch className="h-4 w-4" />
                              <span>Entity Explorer</span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                          <SidebarMenuSubItem>
                            <SidebarMenuSubButton
                              onClick={() => handleReportSubItemClick("tesla", "relationship_graph_viewer")}
                              isActive={selectedReport === "tesla" && screenState === "relationship_graph_viewer"}
                            >
                              <Network className="h-4 w-4" />
                              <span>Relationship Viewer</span>
                            </SidebarMenuSubButton>
                          </SidebarMenuSubItem>
                        </SidebarMenuSub>
                      )}
                    </SidebarMenuSubItem>
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
          {screenState === "communities" && <CommunitiesView />}
          {screenState === "entity_explorer" && <EntityExplorerView />}
          {screenState === "relationship_graph_viewer" && <RelationshipGraphViewerView />}
        </div>
      </SidebarInset>
        </SidebarProvider>
      </div>
    )
}

export default App
