import { useState } from "react"
import { ChevronDown, ChevronRight, FileText, Search } from "lucide-react"
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
import { useAppStore } from "@/store/useAppStore"
import { useReports } from "@/hooks/use-reports"

function SidebarHeaderContent() {
  const { state } = useSidebar()
  const isCollapsed = state === "collapsed"

  return (
    <SidebarHeader className="px-4 py-4 justify-center">
      <h2 className="text-xl font-bold tracking-tight group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:text-center">
        {isCollapsed ? "SG" : "Signal Graph"}
      </h2>
      {!isCollapsed && <Separator className="my-2" />}
    </SidebarHeader>
  )
}

function SidebarNav() {
  const { state } = useSidebar()
  const isCollapsed = state === "collapsed"

  const screenState = useAppStore((state) => state.screenState)
  const setScreenState = useAppStore((state) => state.setScreenState)
  const selectedReport = useAppStore((state) => state.selectedReport)
  const setSelectedReport = useAppStore((state) => state.setSelectedReport)
  const analysisScreenState = useAppStore((state) => state.analysisScreenState)
  const generatingSlug = useAppStore((state) => state.generatingSlug)

  const [reportsExpanded, setReportsExpanded] = useState(true)

  const { data: reports } = useReports()

  const visibleReports = reports?.filter(
    (r) => !(r.name === generatingSlug && analysisScreenState !== "finish")
  )

  const handleReportClick = (reportName: string) => {
    setSelectedReport(reportName)
    setScreenState("report")
  }

  return (
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
            tooltip="Search"
          >
            <Search />
            <span>Search</span>
          </SidebarMenuButton>
        </SidebarMenuItem>

        {/* Reports — driven by GET /reports */}
        <SidebarMenuItem>
          <SidebarMenuButton
            onClick={() => !isCollapsed && setReportsExpanded(!reportsExpanded)}
            tooltip="Reports"
          >
            <FileText />
            <span>Reports</span>
            {!isCollapsed && (reportsExpanded ? <ChevronDown className="ml-auto" /> : <ChevronRight className="ml-auto" />)}
          </SidebarMenuButton>

          {!isCollapsed && reportsExpanded && (
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
                  <SidebarMenuSubButton
                    onClick={() => handleReportClick(report.name)}
                    isActive={selectedReport === report.name && screenState === "report"}
                  >
                    <span className="capitalize">{report.name.replace(/_/g, " ")}</span>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              ))}
            </SidebarMenuSub>
          )}
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarContent>
  )
}

function App() {
  const screenState = useAppStore((state) => state.screenState)

  return (
    <div className="dark h-svh overflow-hidden">
      <SidebarProvider className="!max-h-svh">
        <Sidebar collapsible="icon">
          <SidebarHeaderContent />
          <SidebarNav />
        </Sidebar>
        <SidebarInset className="overflow-hidden">
          <header className="flex h-16 shrink-0 items-center gap-2 border-b-2 border-sidebar-border px-4">
            <SidebarTrigger className="-ml-1" />
            <div className="flex-1" />
          </header>
          <div className="flex flex-1 flex-col gap-4 p-4 min-h-0 overflow-hidden">
            {screenState === "input" && <InputView />}
            {screenState === "report" && <EntityExplorerView />}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </div>
  )
}

export default App
