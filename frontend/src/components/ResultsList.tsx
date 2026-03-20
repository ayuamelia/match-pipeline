"use client";

import { usePolling } from "@/hooks/usePolling";
import { JobCard } from "@/components/JobCard";

interface Props {
  batchId: string | null;
}

export function ResultsList({ batchId }: Props) {
  const { jobs, isPolling, error } = usePolling(batchId);

  if (!batchId) return null;

  const total = jobs.length;
  const done = jobs.filter((j) => j.status === "completed" || j.status === "failed").length;

  return (
    <div>
      {/* Progress header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Results</h2>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          {isPolling && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              Live
            </span>
          )}
          {total > 0 && (
            <span>
              {done}/{total} complete
            </span>
          )}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error} — retrying automatically.
        </div>
      )}

      {/* Job cards */}
      {jobs.length > 0 ? (
        <div className="space-y-4">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-400 text-sm">
          Waiting for results…
        </div>
      )}

      {/* All done banner */}
      {!isPolling && total > 0 && done === total && (
        <div className="mt-4 px-4 py-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700 text-center">
          All {total} job{total !== 1 ? "s" : ""} scored.
        </div>
      )}
    </div>
  );
}
