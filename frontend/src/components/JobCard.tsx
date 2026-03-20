"use client";

import type { MatchJob } from "@/types/match";

interface Props {
  job: MatchJob;
}

const STATUS_CONFIG = {
  pending: {
    badge: "bg-gray-100 text-gray-600 border border-gray-200",
    card: "border-gray-200 bg-white",
    label: "Pending",
    icon: "⏳",
  },
  processing: {
    badge: "bg-blue-100 text-blue-700 border border-blue-200",
    card: "border-blue-200 bg-blue-50",
    label: "Processing",
    icon: "⚙️",
  },
  completed: {
    badge: "bg-green-100 text-green-700 border border-green-200",
    card: "border-green-200 bg-white",
    label: "Completed",
    icon: "✓",
  },
  failed: {
    badge: "bg-red-100 text-red-700 border border-red-200",
    card: "border-red-200 bg-red-50",
    label: "Failed",
    icon: "✕",
  },
};

function ScoreCircle({ score }: { score: number }) {
  const color =
    score >= 80
      ? "text-green-600"
      : score >= 60
      ? "text-amber-600"
      : score >= 40
      ? "text-orange-600"
      : "text-red-600";

  return (
    <div className={`text-4xl font-bold ${color}`}>
      {score}
      <span className="text-lg font-normal text-gray-500">%</span>
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score: number | null }) {
  if (score === null) return null;
  const width = `${score}%`;
  const color =
    score >= 80
      ? "bg-green-500"
      : score >= 60
      ? "bg-amber-400"
      : score >= 40
      ? "bg-orange-400"
      : "bg-red-500";

  return (
    <div>
      <div className="flex justify-between text-xs text-gray-600 mb-1">
        <span className="capitalize">{label}</span>
        <span>{score}%</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color}`}
          style={{ width }}
        />
      </div>
    </div>
  );
}

function SkillBadge({ label, variant }: { label: string; variant: "matched" | "missing" }) {
  const styles =
    variant === "matched"
      ? "bg-green-100 text-green-800 border border-green-200"
      : "bg-red-100 text-red-700 border border-red-200";
  return (
    <span className={`inline-block text-xs px-2 py-0.5 rounded-full ${styles}`}>
      {label}
    </span>
  );
}

export function JobCard({ job }: Props) {
  const cfg = STATUS_CONFIG[job.status];
  const title = job.job_title ?? truncate(job.raw_input, 60);

  return (
    <article
      className={`rounded-xl border p-5 transition-all duration-300 ${cfg.card}`}
      aria-label={`Job match: ${title}`}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{title}</h3>
          {job.required_seniority && (
            <p className="text-xs text-gray-500 mt-0.5 capitalize">
              {job.required_seniority} level
            </p>
          )}
        </div>
        <span
          className={`shrink-0 inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full ${cfg.badge}`}
        >
          <span>{cfg.icon}</span>
          {cfg.label}
        </span>
      </div>

      {/* Pending state */}
      {job.status === "pending" && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="flex gap-0.5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
              />
            ))}
          </span>
          Waiting in queue…
        </div>
      )}

      {/* Processing state */}
      {job.status === "processing" && (
        <div className="flex items-center gap-2 text-sm text-blue-600">
          <svg
            className="w-4 h-4 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
          Scoring in progress…
        </div>
      )}

      {/* Completed state */}
      {job.status === "completed" && job.overall_score !== null && (
        <div className="space-y-4">
          {/* Score + dimensions */}
          <div className="flex gap-6 items-start">
            <div className="text-center min-w-16">
              <ScoreCircle score={job.overall_score} />
              <p className="text-xs text-gray-500 mt-1">overall</p>
            </div>
            <div className="flex-1 space-y-2">
              <ScoreBar label="Skills" score={job.dimension_scores.skills} />
              <ScoreBar label="Experience" score={job.dimension_scores.experience} />
              <ScoreBar label="Location" score={job.dimension_scores.location} />
            </div>
          </div>

          {/* Skills */}
          {(job.matched_skills.length > 0 || job.missing_skills.length > 0) && (
            <div className="space-y-2">
              {job.matched_skills.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Matched skills</p>
                  <div className="flex flex-wrap gap-1">
                    {job.matched_skills.map((s) => (
                      <SkillBadge key={s} label={s} variant="matched" />
                    ))}
                  </div>
                </div>
              )}
              {job.missing_skills.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1">Missing skills</p>
                  <div className="flex flex-wrap gap-1">
                    {job.missing_skills.map((s) => (
                      <SkillBadge key={s} label={s} variant="missing" />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Recommendation */}
          {job.recommendation && (
            <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-700 border border-gray-100">
              <p className="text-xs font-medium text-gray-500 mb-1">Recommendation</p>
              {job.recommendation}
            </div>
          )}

          {/* Duration */}
          {job.duration_seconds !== null && (
            <p className="text-xs text-gray-400">
              Processed in {job.duration_seconds.toFixed(1)}s
            </p>
          )}
        </div>
      )}

      {/* Failed state */}
      {job.status === "failed" && (
        <div className="space-y-2">
          <p className="text-sm text-red-700">
            {job.error_message ?? "This job failed to process."}
          </p>
          {job.retry_count > 0 && (
            <p className="text-xs text-red-500">
              Failed after {job.retry_count} attempt{job.retry_count !== 1 ? "s" : ""}.
            </p>
          )}
        </div>
      )}
    </article>
  );
}

function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}
