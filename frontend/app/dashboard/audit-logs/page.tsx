"use client";

import { useEffect, useState } from "react";
import { ScrollText, ShieldCheck, ShieldAlert, Loader2 } from "lucide-react";
import ErrorState from "@/components/ErrorState";
import { getAuditLogs, verifyIntegrity, AuditLogEntry, IntegrityCheck, ApiError } from "@/lib/api";

const ACTION_FILTERS = ["ALL", "LOGIN", "UPLOAD_PAPER", "APPROVE_PAPER", "REJECT_PAPER", "DOWNLOAD_PAPER", "UNLOCK_PAPER"];

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [actionFilter, setActionFilter] = useState("ALL");
  const [integrity, setIntegrity] = useState<IntegrityCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    setError(null);
    getAuditLogs(200)
      .then(setLogs)
      .catch((err: ApiError) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleVerify() {
    setChecking(true);
    setVerifyError(null);
    try {
      const result = await verifyIntegrity();
      setIntegrity(result);
    } catch (err) {
      setVerifyError(err instanceof ApiError ? err.message : "Couldn't verify the chain.");
    } finally {
      setChecking(false);
    }
  }

  const filtered = actionFilter === "ALL" ? logs : logs.filter((l) => l.action === actionFilter);

  if (loading) {
    return <div className="p-8 text-ink_text-500">Loading audit logs…</div>;
  }

  return (
    <div className="p-6 sm:p-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl text-ink_text-900">Audit Logs</h1>
          <p className="mt-1 text-sm text-ink_text-500">
            Every action, hash-chained to the one before it -- tamper with any entry and the chain breaks.
          </p>
        </div>
        <button onClick={handleVerify} disabled={checking} className="btn-secondary text-sm">
          {checking ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
          Verify Chain Integrity
        </button>
      </header>

      {error && (
        <div className="mb-5">
          <ErrorState message={error} onRetry={load} />
        </div>
      )}

      {verifyError && (
        <div className="mb-5 rounded-xl border border-risk-critical/20 bg-risk-critical/10 px-4 py-3 text-sm text-risk-critical">
          {verifyError}
        </div>
      )}

      {!error && (
      <>
      {integrity && (
        <div
          className={`mb-5 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm ${
            integrity.intact
              ? "border-intel/20 bg-intel/10 text-intel"
              : "border-risk-critical/20 bg-risk-critical/10 text-risk-critical"
          }`}
        >
          {integrity.intact ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
          {integrity.intact
            ? `Chain intact -- ${integrity.entries_checked} entries verified, no tampering detected.`
            : `Tampering detected across ${integrity.entries_checked} entries checked.`}
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        {ACTION_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setActionFilter(f)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              actionFilter === f ? "bg-signal/15 text-signal" : "text-ink_text-500 hover:text-ink_text-900"
            }`}
          >
            {f.replaceAll("_", " ")}
          </button>
        ))}
      </div>

      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink-700 text-xs text-ink_text-500">
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">IP / Location</th>
                <th className="px-4 py-3 font-medium">Device</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Hash</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((log) => (
                <tr key={log.id} className="border-b border-ink-700 hover:bg-ink-800">
                  <td className="whitespace-nowrap px-4 py-3 font-mono text-[11px] text-ink_text-500">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-ink_text-700">{log.user_name}</td>
                  <td className="px-4 py-3 capitalize text-ink_text-500">{log.role.replaceAll("_", " ")}</td>
                  <td className="px-4 py-3 text-ink_text-700">{log.action.replaceAll("_", " ")}</td>
                  <td className="px-4 py-3 text-ink_text-500">
                    {log.ip_address} <span className="text-ink_text-300">· {log.location}</span>
                  </td>
                  <td className="px-4 py-3 text-ink_text-500">{log.device}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        log.status === "SUCCESS" ? "bg-intel/15 text-intel" : "bg-risk-critical/15 text-risk-critical"
                      }`}
                    >
                      {log.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-[11px] text-ink_text-300">{log.hash.slice(0, 12)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="flex items-center justify-center gap-2 p-10 text-ink_text-500">
            <ScrollText className="h-4 w-4" />
            {logs.length === 0 ? "No activity recorded yet." : "No log entries match this filter."}
          </div>
        )}
      </div>
      </>
      )}
    </div>
  );
}
