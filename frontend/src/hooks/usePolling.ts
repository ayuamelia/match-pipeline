import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { MatchJob } from "@/types/match";

const POLL_INTERVAL_MS = 3000;

const isTerminal = (job: MatchJob) =>
  job.status === "completed" || job.status === "failed";

interface UsePollingResult {
  jobs: MatchJob[];
  isPolling: boolean;
  error: string | null;
}

export function usePolling(batchId: string | null): UsePollingResult {
  const [jobs, setJobs] = useState<MatchJob[]>([]);
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchJobs = useCallback(async () => {
    if (!batchId) return;
    try {
      const res = await api.listJobs({ batch_id: batchId, limit: 10 });
      setJobs(res.data);
      setError(null);

      if (res.data.length > 0 && res.data.every(isTerminal)) {
        setIsPolling(false);
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch results.");
    }
  }, [batchId]);

  useEffect(() => {
    if (!batchId) return;

    setIsPolling(true);
    fetchJobs();

    intervalRef.current = setInterval(fetchJobs, POLL_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      setIsPolling(false);
    };
  }, [batchId, fetchJobs]);

  return { jobs, isPolling, error };
}
