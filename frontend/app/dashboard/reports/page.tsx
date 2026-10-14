"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Download, FileSearch, Users, Clock } from "lucide-react";
import ErrorState from "@/components/ErrorState";
import { getReport, listReports, reportPdfUrl, IncidentReport, ApiError } from "@/lib/api";

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-ink_text-500">Loading report…</div>}>
      <ReportsPageContent />
    </Suspense>
  );
}

function ReportsPageContent() {
  const searchParams = useSearchParams();
  const incidentParam = searchParams.get("incident");

  const [report, setReport] = useState<IncidentReport | null>(null);
  const [allReports, setAllReports] = useState<IncidentReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);

    if (incidentParam) {
      getReport(incidentParam)
        .then(setReport)
        .catch((err: ApiError) => setError(err.message))
        .finally(() => setLoading(false));
    } else {
      listReports()
        .then((reports) => {
          setAllReports(reports);
          if (reports.length > 0) setReport(reports[0]);
        })
        .catch((err: ApiError) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }

  useEffect(load, [incidentParam]);

  if (loading) {
    return <div className="p-8 text-ink_text-500">Loading report…</div>;
  }

  if (error) {
    return (
      <div className="p-6 sm:p-8">
        <header className="mb-6">
          <h1 className="font-display text-2xl text-ink_text-900">Investigation Reports</h1>
        </header>
        <ErrorState message={error} onRetry={load} />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-6 sm:p-8">
        <header className="mb-6">
          <h1 className="font-display text-2xl text-ink_text-900">Investigation Reports</h1>
          <p className="mt-1 text-sm text-ink_text-500">
            AI-narrated summaries of confirmed facts already in the audit log -- never invented, only explained.
          </p>
        </header>
        <div className="glass-card p-10 text-center text-ink_text-500">
          No reports generated yet. Go to AI Alerts and click "Generate Investigation Report" on any alert.
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 sm:p-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl text-ink_text-900">Investigation Reports</h1>
          <p className="mt-1 text-sm text-ink_text-500">
            AI-narrated summaries of confirmed facts already in the audit log -- never invented, only explained.
          </p>
        </div>
        <a href={reportPdfUrl(report.incident_id)} className="btn-primary text-sm" download>
          <Download className="h-4 w-4" /> Download PDF
        </a>
      </header>

      {allReports.length > 1 && (
        <div className="mb-5 flex flex-wrap gap-2">
          {allReports.map((r) => (
            <button
              key={r.incident_id}
              onClick={() => setReport(r)}
              className={`rounded-lg px-3 py-1.5 font-mono text-xs transition-colors ${
                report.incident_id === r.incident_id
                  ? "bg-signal/15 text-signal"
                  : "text-ink_text-500 hover:text-ink_text-900"
              }`}
            >
              {r.incident_id}
            </button>
          ))}
        </div>
      )}

      <div className="glass-card p-6 sm:p-8">
        <div className="flex items-center gap-2 text-signal">
          <FileSearch className="h-5 w-5" />
          <span className="font-mono text-xs uppercase tracking-wide">Incident {report.incident_id}</span>
        </div>
        <p className="mt-3 text-sm leading-relaxed text-ink_text-700">{report.summary}</p>

        <div className="mt-5 flex flex-wrap gap-4 text-xs text-ink_text-500">
          <span className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5" /> {report.users_involved.join(", ")}
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" /> Generated {new Date(report.generated_at).toLocaleString()}
          </span>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink_text-500">Contributing factors</p>
            <ul className="mt-2 space-y-1.5">
              {report.contributing_factors.map((f, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-ink_text-700">
                  <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-signal" />
                  {f}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-ink_text-500">Recommended action</p>
            <p className="mt-2 rounded-lg border border-signal/20 bg-signal/[0.06] px-4 py-3 text-sm text-signal-light">
              {report.recommended_action}
            </p>
          </div>
        </div>

        <div className="mt-8">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-ink_text-500">Reconstructed timeline</p>
          <div className="space-y-0">
            {report.timeline.map((event, i) => (
              <div key={i} className="flex gap-4 border-l border-ink-700 pb-5 pl-4 last:pb-0">
                <div className="-ml-[21px] mt-0.5 h-2.5 w-2.5 shrink-0 rounded-full bg-signal" />
                <div>
                  <p className="text-sm text-ink_text-700">
                    {event.actor} · {event.action.replaceAll("_", " ")}
                  </p>
                  <p className="font-mono text-[11px] text-ink_text-300">{new Date(event.timestamp).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
