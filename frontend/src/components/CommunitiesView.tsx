import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSubreddits } from "@/hooks/use-subreddits";
import { Skeleton } from "@/components/ui/skeleton";

function formatScore(score: number | null): string {
  if (score === null || score === undefined) return "N/A";
  return score.toFixed(2);
}

export function CommunitiesView() {
  const { data: subreddits, isLoading, error } = useSubreddits();

  if (isLoading) {
    return (
      <div className="flex flex-1 flex-col items-center gap-4 p-4">
        <h2 className="text-3xl font-bold text-foreground">Communities</h2>
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
        <h2 className="text-3xl font-bold text-foreground">Communities</h2>
        <p className="text-destructive">Failed to load communities. Please try again.</p>
      </div>
    );
  }

  const sortedSubreddits = [...(subreddits || [])].sort(
    (a, b) => (b.relevance_score ?? 0) - (a.relevance_score ?? 0)
  );

  return (
    <div className="flex flex-1 flex-col items-center gap-4 p-4">
      <h2 className="text-3xl font-bold text-foreground">Communities</h2>
      <div className="w-full max-w-4xl">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Subreddit</TableHead>
              <TableHead className="text-right">Relevance</TableHead>
              <TableHead className="text-right">Engagement</TableHead>
              <TableHead className="text-right">Freshness</TableHead>
              <TableHead className="text-right">Frequency</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedSubreddits.map((subreddit) => (
              <TableRow key={subreddit.subreddit_name}>
                <TableCell className="font-medium">
                  <a
                    href={`https://www.reddit.com/${subreddit.subreddit_name}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-400 hover:text-blue-300 hover:underline transition-colors"
                  >
                    {subreddit.subreddit_name}
                  </a>
                </TableCell>
                <TableCell className="text-right">{formatScore(subreddit.relevance_score)}</TableCell>
                <TableCell className="text-right">{formatScore(subreddit.engagement_score)}</TableCell>
                <TableCell className="text-right">{formatScore(subreddit.freshness_score)}</TableCell>
                <TableCell className="text-right">{formatScore(subreddit.frequency_score)}</TableCell>
              </TableRow>
            ))}
            {sortedSubreddits.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No communities found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
