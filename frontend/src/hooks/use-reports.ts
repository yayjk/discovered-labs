import { useQuery } from "@tanstack/react-query";

const API_BASE_URL = "http://localhost:8000";

export interface Report {
  name: string;
  db_path: string;
}

async function fetchReports(): Promise<Report[]> {
  const response = await fetch(`${API_BASE_URL}/reports`);
  if (!response.ok) {
    throw new Error("Failed to fetch reports");
  }
  return response.json();
}

export function useReports() {
  return useQuery({
    queryKey: ["reports"],
    queryFn: fetchReports,
  });
}
