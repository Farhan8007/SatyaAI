"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, FileSearch, Gauge, Loader2 } from "lucide-react";
import RiskBadge from "@/components/RiskBadge";
import ErrorState from "@/components/ErrorState";
import { getAlerts, resolveAlert, generateReport, AlertItem, ApiError } from "@/lib/api";

export default function AlertsPage() {
  const router = useRouter();
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [tab, setTab] = useState<"open" | "resolved">("open");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  function refresh() {
    setLoading(true);
    setError(null);
    getAlerts(tab === "resolved")
      .then(setAlerts)
      .catch((err: ApiError) => setError(err.message))
      .finally(() => setLoading(false));
  }

  async function handleResolve(id: string) {
    setBusyId(id);
    setActionError(null);
    try {
      await resolveAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't resolve this alert.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleGenerateReport(id: string) {
    setBusyId(id);
    setActionError(null);
    try {
      const report = await generateReport(id);
      router.push(`/dashboard/reports?incident=${report.incident_id}`);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't generate the report.");
      setBusyId(null);
    }
  }

  if (loading) {
    return <div className="p-8 text-ink_text-500">Loading alerts…</div>;
  }

  return (
    <div className="p-6 sm:p-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl text-ink_text-900">AI Alerts</h1>
        <p className="mt-1 text-sm text-ink_text-500">
          Every alert explains why it fired -- which factors contributed, how confident the model is, and what to do next.
        </p>
      </header>

      {error && (
        <div className="mb-5">
          <ErrorState message={error} onRetry={refresh} />
        </div>
      )}

      {actionError && (
        <div className="mb-5 rounded-xl border border-risk-critical/20 bg-risk-critical/10 px-4 py-3 text-sm text-risk-critical">
          {actionError}
        </div>
      )}

      {!error && (
      <>
      <div className="mb-5 flex gap-2">
        {(["open", "resolved"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
              tab === t ? "bg-signal/15 text-signal" : "text-ink_text-500 hover:text-ink_text-900"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {alerts.length === 0 && (
          <div className="glass-card p-10 text-center text-ink_text-500">No {tab} alerts right now.</div>
        )}

        {alerts.map((alert) => (
          <div key={alert.id} className="glass-card p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-display text-lg text-ink_text-900">{alert.user_name}</span>
                  <RiskBadge level={alert.risk_level} />
                </div>
                <p className="mt-1 flex items-center gap-1.5 text-xs text-ink_text-500">
                  <Gauge className="h-3 w-3" /> Risk score {alert.risk_score}/100 · Confidence{" "}
                  {Math.round(alert.confidence * 100)}%
                </p>
              </div>
              <span className="text-xs text-ink_text-300">{new Date(alert.created_at).toLocaleString()}</span>
            </div>

            <div className="mt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink_text-500">Contributing factors</p>
              <ul className="mt-2 space-y-1.5">
                {alert.reasons.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-ink_text-700">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-signal" />
                    {r}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-4 rounded-lg border border-signal/20 bg-signal/[0.06] px-4 py-3 text-sm text-signal-light">
              Recommended action: {alert.recommended_action}
            </div>

            {tab === "open" && (
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  onClick={() => handleGenerateReport(alert.id)}
                  disabled={busyId === alert.id}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-intel/15 px-3 py-1.5 text-xs font-medium text-intel hover:bg-intel/25"
                >
                  {busyId === alert.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <FileSearch className="h-3 w-3" />}
                  Generate Investigation Report
                </button>
                <button
                  onClick={() => handleResolve(alert.id)}
                  disabled={busyId === alert.id}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-ink-700 bg-ink-800 px-3 py-1.5 text-xs font-medium text-ink_text-700 hover:border-signal/40"
                >
                  <CheckCircle2 className="h-3 w-3" /> Mark Resolved
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
      </>
      )}
    </div>
  );
}
