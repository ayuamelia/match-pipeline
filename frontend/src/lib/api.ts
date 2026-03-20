import type { MatchJob, MatchListResponse, SubmitResponse } from "@/types/match";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  submitBatch: (jobs: { content: string; title?: string }[]): Promise<SubmitResponse> =>
    request("/api/v1/matches", {
      method: "POST",
      body: JSON.stringify({ jobs }),
    }),

  getJob: (id: string): Promise<MatchJob> =>
    request(`/api/v1/matches/${id}`),

  listJobs: (params: {
    batch_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<MatchListResponse> => {
    const qs = new URLSearchParams();
    if (params.batch_id) qs.set("batch_id", params.batch_id);
    if (params.status) qs.set("status", params.status);
    if (params.limit !== undefined) qs.set("limit", String(params.limit));
    if (params.offset !== undefined) qs.set("offset", String(params.offset));
    return request(`/api/v1/matches?${qs.toString()}`);
  },

  getProfile: (): Promise<{
    name: string;
    location: string | null;
    seniority_level: string;
    years_of_experience: number;
    willing_to_relocate: boolean;
    skills: string[];
    summary: string | null;
  }> => request("/api/v1/me"),
};