import { create } from 'zustand'

export type ScreenState = "input" | "communities" | "entity_explorer" | "relationship_graph_viewer"

export type AnalysisScreenState = "start" | "running" | "finish"

export type ReportType = "openai" | "tesla" | null

export interface AnalysisEvent {
  stage: string
  message: string
  timestamp: number
}

interface AppState {
  // Navigation state
  screenState: ScreenState
  setScreenState: (state: ScreenState) => void
  
  // Report selection
  selectedReport: ReportType
  setSelectedReport: (report: ReportType) => void
  
  // Analysis state
  analysisScreenState: AnalysisScreenState
  setAnalysisScreenState: (state: AnalysisScreenState) => void
  
  // Analysis events
  analysisEvents: AnalysisEvent[]
  addAnalysisEvent: (event: AnalysisEvent) => void
  clearAnalysisEvents: () => void
  
  // Loading dots for animation
  loadingDots: number
  setLoadingDots: (dots: number | ((prev: number) => number)) => void
}

export const useAppStore = create<AppState>((set) => ({
  // Navigation state
  screenState: "input",
  setScreenState: (state) => set({ screenState: state }),
  
  // Report selection
  selectedReport: null,
  setSelectedReport: (report) => set({ selectedReport: report }),
  
  // Analysis state
  analysisScreenState: "start",
  setAnalysisScreenState: (state) => set({ analysisScreenState: state }),
  
  // Analysis events
  analysisEvents: [],
  addAnalysisEvent: (event) => 
    set((state) => ({ 
      analysisEvents: [...state.analysisEvents, event] 
    })),
  clearAnalysisEvents: () => set({ analysisEvents: [] }),
  
  // Loading dots
  loadingDots: 1,
  setLoadingDots: (dots) => 
    set((state) => ({ 
      loadingDots: typeof dots === 'function' ? dots(state.loadingDots) : dots 
    })),
}))
