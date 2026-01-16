import { useState } from "react"
import { Network, ScanSearch, Search, Users } from "lucide-react"
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
  useSidebar,
} from "@/components/ui/sidebar"
import { Separator } from "@/components/ui/separator"
import { InputView } from "@/components/InputView"
import { CommunitiesView } from "@/components/CommunitiesView"
import { EntityExplorerView } from "@/components/EntityExplorerView"
import { RelationshipGraphViewerView } from "@/components/RelationshipGraphViewerView"

type ScreenState = "input" | "communities" | "entity_explorer" | "relationship_graph_viewer"

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
  const [screenState, setScreenState] = useState<ScreenState>("input")

  return (
    <div className="dark">
      <SidebarProvider>
        <Sidebar collapsible="icon">
          <SidebarHeaderContent />
          <SidebarContent className="px-0">
            <SidebarMenu className="gap-3">
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => setScreenState("input")}
                  isActive={screenState === "input"}
                >
                  <Search />
                  <span>Search</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => setScreenState("communities")}
                  isActive={screenState === "communities"}
                >
                  <Users />
                  <span>Communities</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => setScreenState("entity_explorer")}
                  isActive={screenState === "entity_explorer"}
                >
                  <ScanSearch />
                  <span>Entity Explorer</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => setScreenState("relationship_graph_viewer")}
                  isActive={screenState === "relationship_graph_viewer"}
                >
                  <Network />
                  <span>Relationship Viewer</span>
                </SidebarMenuButton>
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
