import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { JobCard } from "@/components/JobCard";
import type { MatchJob } from "@/types/match";

function makeJob(overrides: Partial<MatchJob> = {}): MatchJob {
  return {
    id: "test-job",
    batch_id: "test-batch",
    status: "pending",
    raw_input: "Senior Python Engineer with FastAPI experience needed.",
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
    enqueued_at: "2025-01-01T00:00:00Z",
    started_at: null,
    completed_at: null,
    duration_seconds: null,
    ...overrides,
  };
}

describe("JobCard — pending state", () => {
  it("shows the pending label", () => {
    render(<JobCard job={makeJob({ status: "pending" })} />);
    expect(screen.getByText("Pending")).toBeInTheDocument();
  });

  it("shows a waiting message", () => {
    render(<JobCard job={makeJob({ status: "pending" })} />);
    expect(screen.getByText(/waiting in queue/i)).toBeInTheDocument();
  });

  it("does not show a score", () => {
    render(<JobCard job={makeJob({ status: "pending" })} />);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });
});

describe("JobCard — processing state", () => {
  it("shows the processing label", () => {
    render(<JobCard job={makeJob({ status: "processing" })} />);
    expect(screen.getByText("Processing")).toBeInTheDocument();
  });

  it("shows a scoring-in-progress message", () => {
    render(<JobCard job={makeJob({ status: "processing" })} />);
    expect(screen.getByText(/scoring in progress/i)).toBeInTheDocument();
  });

  it("does not show a score", () => {
    render(<JobCard job={makeJob({ status: "processing" })} />);
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });
});

describe("JobCard — completed state", () => {
  const completedJob = makeJob({
    status: "completed",
    job_title: "Senior Python Engineer",
    required_seniority: "senior",
    overall_score: 82,
    dimension_scores: { skills: 90, experience: 80, location: 70 },
    matched_skills: ["Python", "FastAPI", "PostgreSQL"],
    missing_skills: ["Kubernetes", "AWS"],
    recommendation: "Strong match — apply with confidence.",
    started_at: "2025-01-01T00:00:01Z",
    completed_at: "2025-01-01T00:00:03Z",
    duration_seconds: 2.1,
  });

  it("shows the completed label", () => {
    render(<JobCard job={completedJob} />);
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("shows the overall score", () => {
    render(<JobCard job={completedJob} />);
    expect(screen.getByText("82")).toBeInTheDocument();
  });

  it("shows all three dimension labels", () => {
    render(<JobCard job={completedJob} />);
    expect(screen.getByText("Skills")).toBeInTheDocument();
    expect(screen.getByText("Experience")).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
  });

  it("shows matched skills", () => {
    render(<JobCard job={completedJob} />);
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("FastAPI")).toBeInTheDocument();
  });

  it("shows missing skills", () => {
    render(<JobCard job={completedJob} />);
    expect(screen.getByText("Kubernetes")).toBeInTheDocument();
    expect(screen.getByText("AWS")).toBeInTheDocument();
  });

  it("shows the recommendation", () => {
    render(<JobCard job={completedJob} />);
    expect(screen.getByText(/strong match/i)).toBeInTheDocument();
  });

  it("shows the job title when available", () => {
    render(<JobCard job={completedJob} />);
    expect(screen.getByText("Senior Python Engineer")).toBeInTheDocument();
  });
});

describe("JobCard — failed state", () => {
  const failedJob = makeJob({
    status: "failed",
    error_message: "Task timed out after 120 seconds.",
    retry_count: 3,
  });

  it("shows the failed label", () => {
    render(<JobCard job={failedJob} />);
    expect(screen.getByText("Failed")).toBeInTheDocument();
  });

  it("shows the error message", () => {
    render(<JobCard job={failedJob} />);
    expect(screen.getByText(/timed out/i)).toBeInTheDocument();
  });

  it("shows the retry count", () => {
    render(<JobCard job={failedJob} />);
    expect(screen.getByText(/3 attempt/i)).toBeInTheDocument();
  });

  it("does not show a score", () => {
    render(<JobCard job={failedJob} />);
    expect(screen.queryByText("overall")).not.toBeInTheDocument();
  });
});

describe("JobCard — fallback title", () => {
  it("truncates raw_input as title when job_title is null", () => {
    const longInput = "A".repeat(80);
    render(<JobCard job={makeJob({ raw_input: longInput, job_title: null })} />);
    const heading = screen.getByRole("heading");
    expect(heading.textContent?.length).toBeLessThan(80);
  });
});
