/**
 * Tests for usePolling hook.
 *
 * What we test here:
 * 1. Hook starts polling when given a batchId
 * 2. Jobs are returned and rendered correctly per status
 * 3. Polling stops automatically when all jobs are terminal
 * 4. Cleanup happens on unmount (no memory leaks)
 *
 * We mock the api module entirely — we are testing the hook's
 * behaviour, not the network layer. The API client has its own
 * integration tests on the backend side.
 */

import { renderHook, act, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach, afterEach } from "vitest";
import { usePolling } from "@/hooks/usePolling";
import type { MatchJob } from "@/types/match";

vi.mock("@/lib/api", () => ({
  api: {
    listJobs: vi.fn(),
  },
}));

import { api } from "@/lib/api";

const mockApi = api as { listJobs: ReturnType<typeof vi.fn> };

function makeJob(overrides: Partial<MatchJob> = {}): MatchJob {
  return {
    id: "job-1",
    batch_id: "batch-1",
    status: "pending",
    raw_input: "Senior Python Engineer role",
    job_title: null,
    required_seniority: null,
    required_skills: [],
    overall_score: null,
    dimension_scores: { skills: null, experience: null, location: null },
    matched_skills: [],
    missing_skills: [],
    recommendation: null,
    score_explanation: null,
    error_message: null,
    retry_count: 0,
    enqueued_at: new Date().toISOString(),
    started_at: null,
    completed_at: null,
    duration_seconds: null,
    ...overrides,
  };
}

function makeListResponse(jobs: MatchJob[]) {
  return {
    data: jobs,
    pagination: { total: jobs.length, limit: 10, offset: 0, has_more: false },
  };
}

beforeEach(() => {
  vi.useFakeTimers();
  mockApi.listJobs.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("usePolling", () => {
  it("returns empty jobs and isPolling=false when batchId is null", () => {
    const { result } = renderHook(() => usePolling(null));
    expect(result.current.jobs).toEqual([]);
    expect(result.current.isPolling).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("fetches immediately when batchId is provided", async () => {
    const job = makeJob({ status: "pending" });
    mockApi.listJobs.mockResolvedValue(makeListResponse([job]));

    const { result } = renderHook(() => usePolling("batch-1"));

    await waitFor(() => {
      expect(result.current.jobs).toHaveLength(1);
    });

    expect(mockApi.listJobs).toHaveBeenCalledWith({
      batch_id: "batch-1",
      limit: 10,
    });
    expect(result.current.isPolling).toBe(true);
  });

  it("polls at 3-second intervals while jobs are non-terminal", async () => {
    const job = makeJob({ status: "processing" });
    mockApi.listJobs.mockResolvedValue(makeListResponse([job]));

    renderHook(() => usePolling("batch-1"));

    // Initial fetch
    await act(async () => {});
    expect(mockApi.listJobs).toHaveBeenCalledTimes(1);

    // Advance 3 seconds → second poll
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockApi.listJobs).toHaveBeenCalledTimes(2);

    // Advance 3 more seconds → third poll
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(mockApi.listJobs).toHaveBeenCalledTimes(3);
  });

  it("stops polling when all jobs are completed", async () => {
    const pendingJob = makeJob({ status: "pending" });
    const completedJob = makeJob({
      status: "completed",
      overall_score: 85,
    });

    // First call: pending; second call: completed
    mockApi.listJobs
      .mockResolvedValueOnce(makeListResponse([pendingJob]))
      .mockResolvedValue(makeListResponse([completedJob]));

    const { result } = renderHook(() => usePolling("batch-1"));

    // Initial fetch — pending, still polling
    await waitFor(() => expect(result.current.jobs[0].status).toBe("pending"));
    expect(result.current.isPolling).toBe(true);

    // Advance interval — completed, polling should stop
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    await waitFor(() => expect(result.current.jobs[0].status).toBe("completed"));
    expect(result.current.isPolling).toBe(false);

    const callCountAfterStop = mockApi.listJobs.mock.calls.length;

    // Advance more time — no more calls expected
    await act(async () => {
      vi.advanceTimersByTime(9000);
    });
    expect(mockApi.listJobs).toHaveBeenCalledTimes(callCountAfterStop);
  });

  it("stops polling when all jobs are failed", async () => {
    const failedJob = makeJob({
      status: "failed",
      error_message: "Task timed out.",
    });
    mockApi.listJobs.mockResolvedValue(makeListResponse([failedJob]));

    const { result } = renderHook(() => usePolling("batch-1"));

    await waitFor(() => expect(result.current.jobs[0].status).toBe("failed"));
    expect(result.current.isPolling).toBe(false);
  });

  it("handles mixed batch: keeps polling until ALL jobs are terminal", async () => {
    const completedJob = makeJob({ id: "job-1", status: "completed", overall_score: 72 });
    const processingJob = makeJob({ id: "job-2", status: "processing" });
    const allDoneJob = makeJob({ id: "job-2", status: "completed", overall_score: 55 });

    mockApi.listJobs
      .mockResolvedValueOnce(makeListResponse([completedJob, processingJob]))
      .mockResolvedValue(makeListResponse([completedJob, allDoneJob]));

    const { result } = renderHook(() => usePolling("batch-1"));

    await waitFor(() => expect(result.current.jobs).toHaveLength(2));
    // One is processing — still polling
    expect(result.current.isPolling).toBe(true);

    await act(async () => { vi.advanceTimersByTime(3000); });
    await waitFor(() =>
      expect(result.current.jobs.every((j) => j.status === "completed")).toBe(true)
    );
    // Now all terminal — stopped
    expect(result.current.isPolling).toBe(false);
  });

  it("clears the interval and stops polling on unmount", async () => {
    const job = makeJob({ status: "processing" });
    mockApi.listJobs.mockResolvedValue(makeListResponse([job]));

    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");
    const { unmount } = renderHook(() => usePolling("batch-1"));

    await act(async () => {});
    unmount();

    // clearInterval must have been called during cleanup
    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });

  it("sets error state when API call fails", async () => {
    mockApi.listJobs.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => usePolling("batch-1"));

    await waitFor(() => {
      expect(result.current.error).toBe("Network error");
    });
  });

  it("passes batch_id as query param", async () => {
    mockApi.listJobs.mockResolvedValue(makeListResponse([]));

    renderHook(() => usePolling("my-specific-batch"));

    await waitFor(() => {
      expect(mockApi.listJobs).toHaveBeenCalledWith(
        expect.objectContaining({ batch_id: "my-specific-batch" })
      );
    });
  });
});
