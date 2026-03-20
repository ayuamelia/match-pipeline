"use client";

import { useState } from "react";
import { CandidateProfile } from "@/components/CandidateProfile";
import { SubmitForm } from "@/components/SubmitForm";
import { ResultsList } from "@/components/ResultsList";

export default function Home() {
  const [batchId, setBatchId] = useState<string | null>(null);

  return (
    <main className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-900">Pelgo Match Pipeline</h1>
            <p className="text-xs text-gray-500">Score job descriptions against your profile</p>
          </div>
        </div>
      </header>

      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        {/* Profile card — collapsed by default, user opens it to inspect */}
        <CandidateProfile />
        <SubmitForm onBatchSubmitted={(id) => setBatchId(id)} />
        <ResultsList batchId={batchId} />
      </div>
    </main>
  );
}