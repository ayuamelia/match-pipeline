export type JobStatus = "pending" | "processing" | "completed" | "failed";

export interface JobSubmission {
  content: string;
  title?: string;
}

export interface DimensionScores {
  skills: number | null;
  experience: number | null;
  location: number | null;
}

export interface ScoreExplanation {
  skills: string | null;
  experience: string | null;
  location: string | null;
}

export interface MatchJob {
  id: string;
  batch_id: string;
  status: JobStatus;
  raw_input: string;
  job_title: string | null;
  required_seniority: string | null;
  required_skills: string[];
  overall_score: number | null;
  dimension_scores: DimensionScores;
  matched_skills: string[];
  missing_skills: string[];
  recommendation: string | null;
  score_explanation: ScoreExplanation | null;
  error_message: string | null;
  retry_count: number;
  enqueued_at: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
}

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface MatchListResponse {
  data: MatchJob[];
  pagination: PaginationMeta;
}

export interface SubmitResponse {
  batch_id: string;
  jobs: { id: string; status: string }[];
  total_submitted: number;
  message: string;
}