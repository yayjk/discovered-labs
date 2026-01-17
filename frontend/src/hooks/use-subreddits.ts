import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000";

export interface Subreddit {
  subreddit_name: string;
  engagement_score: number | null;
  freshness_score: number | null;
  frequency_score: number | null;
  relevance_score: number | null;
}

async function fetchSubreddits(report: string): Promise<Subreddit[]> {
  const response = await fetch(`${API_BASE_URL}/subreddits?report=${report}`);
  if (!response.ok) {
    throw new Error("Failed to fetch subreddits");
  }
  return response.json();
}

export function useSubreddits(report: string = "tesla") {
  return useQuery({
    queryKey: ["subreddits", report],
    queryFn: () => fetchSubreddits(report),
  });
}
