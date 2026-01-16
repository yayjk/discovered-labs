import { Input } from "@/components/ui/input"

export function InputView() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8">
      <h1 className="text-4xl font-bold text-center text-foreground">
        Discover communities & build a relationship graph
      </h1>
      <Input
        type="search"
        placeholder="Search communities..."
        className="w-full max-w-md text-lg h-12 border-4 border-muted shadow-lg bg-sidebar text-foreground placeholder-muted-foreground"
      />
    </div>
  )
}
