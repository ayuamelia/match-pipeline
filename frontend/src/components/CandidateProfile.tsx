"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface Profile {
  name: string;
  location: string | null;
  seniority_level: string;
  years_of_experience: number;
  willing_to_relocate: boolean;
  skills: string[];
  summary: string | null;
}

const SENIORITY_LABEL: Record<string, string> = {
  intern: "Intern",
  junior: "Junior",
  mid: "Mid-level",
  senior: "Senior",
  lead: "Lead",
  principal: "Principal",
  staff: "Staff",
  director: "Director",
};

export function CandidateProfile() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    api.getProfile().then(setProfile).catch(() => null);
  }, []);

  if (!profile) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header row — always visible, click to expand */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-sm font-semibold shrink-0">
            {profile.name.charAt(0)}
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-gray-900">{profile.name}</p>
            <p className="text-xs text-gray-500">
              {SENIORITY_LABEL[profile.seniority_level] ?? profile.seniority_level}
              {" · "}
              {profile.years_of_experience} years exp
              {profile.location ? ` · ${profile.location}` : ""}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400 hidden sm:block">
            {profile.skills.length} skills
          </span>
          <svg
            className={`w-4 h-4 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="px-6 pb-5 border-t border-gray-100 space-y-4 pt-4">
          {/* Summary */}
          {profile.summary && (
            <p className="text-sm text-gray-600 leading-relaxed">{profile.summary}</p>
          )}

          {/* Stats row */}
          <div className="flex flex-wrap gap-3">
            <Pill label="Seniority" value={SENIORITY_LABEL[profile.seniority_level] ?? profile.seniority_level} />
            <Pill label="Experience" value={`${profile.years_of_experience} years`} />
            {profile.location && <Pill label="Location" value={profile.location} />}
            <Pill
              label="Relocation"
              value={profile.willing_to_relocate ? "Open to relocate" : "Not looking to relocate"}
              highlight={profile.willing_to_relocate}
            />
          </div>

          {/* Skills */}
          <div>
            <p className="text-xs font-medium text-gray-500 mb-2">
              Skills ({profile.skills.length})
            </p>
            <div className="flex flex-wrap gap-1.5">
              {profile.skills.map((skill) => (
                <span
                  key={skill}
                  className="text-xs px-2.5 py-1 bg-blue-50 text-blue-700 border border-blue-100 rounded-full"
                >
                  {skill}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Pill({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5 bg-gray-50 border border-gray-100 rounded-lg px-3 py-1.5">
      <span className="text-xs text-gray-400">{label}</span>
      <span className={`text-xs font-medium ${highlight ? "text-green-600" : "text-gray-700"}`}>
        {value}
      </span>
    </div>
  );
}