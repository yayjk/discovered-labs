import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { useAppStore } from "@/store/useAppStore"

export function InputView() {
  const analysisScreenState = useAppStore((state) => state.analysisScreenState)
  const setAnalysisScreenState = useAppStore((state) => state.setAnalysisScreenState)
  const analysisEvents = useAppStore((state) => state.analysisEvents)
  const addAnalysisEvent = useAppStore((state) => state.addAnalysisEvent)
  const clearAnalysisEvents = useAppStore((state) => state.clearAnalysisEvents)
  const loadingDots = useAppStore((state) => state.loadingDots)
  const setLoadingDots = useAppStore((state) => state.setLoadingDots)
  const setScreenState = useAppStore((state) => state.setScreenState)
  const setSelectedReport = useAppStore((state) => state.setSelectedReport)

  // Animated loading indicator
  useEffect(() => {
    if (analysisScreenState === "running") {
      const interval = setInterval(() => {
        setLoadingDots((prev) => (prev >= 5 ? 1 : prev + 1))
      }, 300)
      return () => clearInterval(interval)
    }
  }, [analysisScreenState, setLoadingDots])

  const handleSearchOpenAI = async () => {
    setAnalysisScreenState("running")
    clearAnalysisEvents()

    try {
      const response = await fetch("http://localhost:8000/analysis/analyze")
      
      if (!response.body) {
        throw new Error("No response body")
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split("\n")

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6))
              addAnalysisEvent({
                stage: data.stage,
                message: data.message,
                timestamp: Date.now(),
              })

              // Stop if complete or error
              if (data.stage === "complete" || data.stage === "error") {
                setAnalysisScreenState("finish")
              }
            } catch (e) {
              console.error("Failed to parse SSE data:", e)
            }
          }
        }
      }
    } catch (error) {
      console.error("Error connecting to analysis endpoint:", error)
      addAnalysisEvent({
        stage: "error",
        message: `Connection error: ${error}`,
        timestamp: Date.now(),
      })
      setAnalysisScreenState("finish")
    }
  }

  const handleViewReport = () => {
    setSelectedReport("openai")
    setScreenState("communities")
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 p-8">
      <h1 className="text-4xl font-bold text-center text-foreground">
        Discover communities & build a relationship graph
      </h1>
      
      {analysisScreenState === "start" && (
        <Button
          onClick={handleSearchOpenAI}
          className="w-full max-w-md text-lg h-12 shadow-lg"
        >
          Search OpenAI
        </Button>
      )}

      {analysisScreenState === "running" && (
        <div className="text-lg font-medium text-foreground">
          Building Report for OpenAI{".".repeat(loadingDots)}
        </div>
      )}

      {analysisScreenState === "finish" && (
        <Button
          onClick={handleViewReport}
          className="w-full max-w-md text-lg h-12 shadow-lg"
        >
          View Report
        </Button>
      )}

      {analysisEvents.length > 0 && (
        <div className="w-full max-w-2xl max-h-96 overflow-y-auto bg-black p-4 rounded-lg space-y-2">
          {analysisEvents.map((event, index) => (
            <div
              key={`${event.stage}-${event.timestamp}-${index}`}
              className="text-gray-500 font-bold italic text-sm"
            >
              {event.message}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
