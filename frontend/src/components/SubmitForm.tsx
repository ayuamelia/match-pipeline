"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface Props {
  onBatchSubmitted: (batchId: string) => void;
}

const EMPTY_JOB = { title: "", content: "" };

export function SubmitForm({ onBatchSubmitted }: Props) {
  const [jobs, setJobs] = useState([{ ...EMPTY_JOB }]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const addJob = () => {
    if (jobs.length < 10) setJobs((prev) => [...prev, { ...EMPTY_JOB }]);
  };

  const removeJob = (idx: number) => {
    if (jobs.length > 1) setJobs((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateField = (idx: number, field: "title" | "content", value: string) => {
    setJobs((prev) =>
      prev.map((j, i) => (i === idx ? { ...j, [field]: value } : j))
    );
  };

  const handleSubmit = async () => {
    const validJobs = jobs.filter((j) => j.content.trim().length >= 10);
    if (validJobs.length === 0) {
      setError("Add at least one job description (minimum 10 characters).");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      // Send title alongside content — backend stores it as job_title override
      const res = await api.submitBatch(
        validJobs.map((j) => ({
          content: j.content,
          ...(j.title.trim() ? { title: j.title.trim() } : {}),
        }))
      );
      onBatchSubmitted(res.batch_id);
      setJobs([{ ...EMPTY_JOB }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const urlCount = jobs.filter(
    (j) =>
      j.content.trim().startsWith("http://") ||
      j.content.trim().startsWith("https://")
  ).length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-gray-900 mb-1">Submit job descriptions</h2>
      <p className="text-sm text-gray-500 mb-5">
        Paste up to 10 job descriptions or URLs. Add a label so you can tell them apart in the results.
      </p>

      <div className="space-y-4 mb-4">
        {jobs.map((job, idx) => (
          <div key={idx} className="flex items-start gap-2">
            <span className="mt-3 text-xs font-medium text-gray-400 w-4 shrink-0 text-right">
              {idx + 1}
            </span>

            <div className="flex-1 space-y-2">
              {/* Job title — optional label */}
              <input
                type="text"
                value={job.title}
                onChange={(e) => updateField(idx, "title", e.target.value)}
                placeholder="Job title (optional) — e.g. Senior Backend Engineer at Stripe"
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2
                           placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500
                           focus:border-transparent transition-shadow"
                disabled={submitting}
                maxLength={120}
              />

              {/* Job description or URL */}
              <textarea
                value={job.content}
                onChange={(e) => updateField(idx, "content", e.target.value)}
                placeholder="Paste the full job description or a URL…"
                rows={3}
                className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2.5 resize-y
                           placeholder-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500
                           focus:border-transparent transition-shadow"
                disabled={submitting}
              />

              {/* Per-field URL warning */}
              {(job.content.trim().startsWith("http://") ||
                job.content.trim().startsWith("https://")) && (
                <p className="text-xs text-amber-600 px-1">
                  URL detected — paste the job description text directly for accurate skill matching.
                  Scoring a URL alone returns default scores.
                </p>
              )}
            </div>

            {jobs.length > 1 && (
              <button
                type="button"
                onClick={() => removeJob(idx)}
                disabled={submitting}
                className="mt-2.5 text-gray-300 hover:text-red-400 transition-colors text-lg leading-none"
                aria-label="Remove this job"
              >
                ×
              </button>
            )}
          </div>
        ))}
      </div>

      {urlCount >= 2 && (
        <div className="mb-4 px-3 py-2.5 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-700">
          {urlCount} URLs detected. For best results, paste the actual job description text instead.
        </div>
      )}

      {error && (
        <div className="mb-4 px-3 py-2.5 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex items-center gap-3">
        {jobs.length < 10 && (
          <button
            type="button"
            onClick={addJob}
            disabled={submitting}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium disabled:opacity-40 transition-colors"
          >
            + Add another
          </button>
        )}
        <span className="text-xs text-gray-300">{jobs.length}/10</span>
        <div className="flex-1" />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={submitting}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg
                     hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed
                     transition-colors flex items-center gap-2"
        >
          {submitting ? (
            <>
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
              Submitting…
            </>
          ) : (
            "Score jobs"
          )}
        </button>
      </div>
    </div>
  );
}