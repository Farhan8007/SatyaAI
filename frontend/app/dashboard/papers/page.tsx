"use client";

import { useEffect, useState } from "react";
import { Upload, Shield, Check, X, Loader2, FileText, Unlock, Download } from "lucide-react";
import StatusBadge from "@/components/StatusBadge";
import ErrorState from "@/components/ErrorState";
import { getPapers, approvePaper, rejectPaper, uploadPaper, unlockPaper, downloadPaper, Paper, ApiError } from "@/lib/api";

const ROLE_CAN_APPROVE = ["moderator", "administrator"];
const ROLE_CAN_UPLOAD = ["paper_setter", "administrator"];
const ROLE_CAN_UNLOCK = ["examination_centre", "administrator"];

export default function PapersPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [role, setRole] = useState("");
  const [filter, setFilter] = useState<"all" | "pending" | "approved" | "rejected">("all");
  const [showUpload, setShowUpload] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [unlockedIds, setUnlockedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    setRole(window.localStorage.getItem("satya_role") || "");
    refresh();
  }, []);

  function refresh() {
    setLoading(true);
    setError(null);
    getPapers()
      .then(setPapers)
      .catch((err: ApiError) => setError(err.message))
      .finally(() => setLoading(false));
  }

  async function handleDecision(id: string, decision: "approve" | "reject") {
    setBusyId(id);
    setActionError(null);
    try {
      const fn = decision === "approve" ? approvePaper : rejectPaper;
      const updated = await fn(id);
      setPapers((prev) => prev.map((p) => (p.id === id ? updated : p)));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleUnlock(id: string) {
    setBusyId(id);
    setActionError(null);
    try {
      await unlockPaper(id);
      setUnlockedIds((prev) => new Set(prev).add(id));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't unlock this paper.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDownload(paper: Paper) {
    setBusyId(paper.id);
    setActionError(null);
    try {
      const blob = await downloadPaper(paper.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${paper.title.replace(/\s+/g, "_")}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't download this paper.");
    } finally {
      setBusyId(null);
    }
  }

  const filtered = filter === "all" ? papers : papers.filter((p) => p.status === filter);

  if (loading) {
    return <div className="p-8 text-ink_text-500">Loading papers…</div>;
  }

  return (
    <div className="p-6 sm:p-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl text-ink_text-900">Question Papers</h1>
          <p className="mt-1 text-sm text-ink_text-500">Encrypted, signed, and tracked from creation to unlock.</p>
        </div>
        {ROLE_CAN_UPLOAD.includes(role) && (
          <button onClick={() => setShowUpload(true)} className="btn-primary text-sm">
            <Upload className="h-4 w-4" /> Upload Paper
          </button>
        )}
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
      {/* Filters */}
      <div className="mb-5 flex gap-2">
        {(["all", "pending", "approved", "rejected"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
              filter === f ? "bg-signal/15 text-signal" : "text-ink_text-500 hover:text-ink_text-900"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Papers list */}
      <div className="space-y-3">
        {filtered.length === 0 && (
          <div className="glass-card p-10 text-center text-ink_text-500">
            {papers.length === 0 ? "No papers uploaded yet." : "No papers match this filter."}
          </div>
        )}
        {filtered.map((paper) => (
          <div key={paper.id} className="glass-card p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-signal/10">
                  <FileText className="h-4 w-4 text-signal" />
                </div>
                <div>
                  <p className="font-medium text-ink_text-900">{paper.title}</p>
                  <p className="text-xs text-ink_text-500">{paper.subject}</p>
                  <p className="mt-1 flex items-center gap-1.5 font-mono text-[11px] text-ink_text-300">
                    <Shield className="h-3 w-3" /> {paper.sha256_hash.slice(0, 24)}…
                  </p>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <StatusBadge status={paper.status} />
                <span className="text-xs text-ink_text-500">
                  Set by {paper.setter_name} · {paper.exam_centre ?? "Centre TBD"}
                </span>
              </div>
            </div>

            {paper.remarks && (
              <p className="mt-3 rounded-lg border border-ink-700 bg-ink-800 px-3 py-2 text-xs text-ink_text-500">
                Remarks: {paper.remarks}
              </p>
            )}

            {paper.status === "pending" && ROLE_CAN_APPROVE.includes(role) && (
              <div className="mt-4 flex gap-2">
                <button
                  onClick={() => handleDecision(paper.id, "approve")}
                  disabled={busyId === paper.id}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-intel/15 px-3 py-1.5 text-xs font-medium text-intel hover:bg-intel/25"
                >
                  {busyId === paper.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}
                  Approve
                </button>
                <button
                  onClick={() => handleDecision(paper.id, "reject")}
                  disabled={busyId === paper.id}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-risk-critical/15 px-3 py-1.5 text-xs font-medium text-risk-critical hover:bg-risk-critical/25"
                >
                  <X className="h-3 w-3" /> Reject
                </button>
              </div>
            )}

            {paper.status === "approved" && ROLE_CAN_UNLOCK.includes(role) && (
              <div className="mt-4 flex items-center gap-2">
                {paper.unlock_time || unlockedIds.has(paper.id) ? (
                  <button
                    onClick={() => handleDownload(paper)}
                    disabled={busyId === paper.id}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-intel/15 px-3 py-1.5 text-xs font-medium text-intel hover:bg-intel/25 transition-colors"
                  >
                    {busyId === paper.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                    Download Decrypted Paper
                  </button>
                ) : (
                  <button
                    onClick={() => handleUnlock(paper.id)}
                    disabled={busyId === paper.id}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-signal/15 px-3 py-1.5 text-xs font-medium text-signal hover:bg-signal/25"
                  >
                    {busyId === paper.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <Unlock className="h-3 w-3" />}
                    Unlock for Exam Centre
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      </>
      )}

      {showUpload && (
        <UploadModal
          onClose={() => setShowUpload(false)}
          onUploaded={(p) => {
            setPapers((prev) => [p, ...prev]);
            setShowUpload(false);
          }}
        />
      )}
    </div>
  );
}

function UploadModal({ onClose, onUploaded }: { onClose: () => void; onUploaded: (p: Paper) => void }) {
  const [title, setTitle] = useState("");
  const [subject, setSubject] = useState("");
  const [examDate, setExamDate] = useState("");
  const [examCentre, setExamCentre] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalError, setModalError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setModalError("");
    const formData = new FormData();
    formData.append("title", title);
    formData.append("subject", subject);
    formData.append("exam_date", new Date(examDate).toISOString());
    if (examCentre.trim()) {
      formData.append("exam_centre", examCentre.trim());
    }
    formData.append("file", file);
    try {
      const result = await uploadPaper(formData);
      onUploaded(result);
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4" onClick={onClose}>
      <form
        onClick={(e) => e.stopPropagation()}
        onSubmit={handleSubmit}
        className="glass-card w-full max-w-md bg-ink-900 p-6"
      >
        <h2 className="font-display text-lg text-ink_text-900">Upload Question Paper</h2>
        <p className="mt-1 text-xs text-ink_text-500">Encrypted with AES-256 and signed on submission.</p>

        <div className="mt-5 space-y-3">
          <input
            required
            placeholder="Title (e.g. Data Structures - Mid Sem)"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50"
          />
          <input
            required
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50"
          />
          <input
            required
            type="date"
            value={examDate}
            onChange={(e) => setExamDate(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 outline-none focus:border-signal/50"
          />
          <input
            placeholder="Assigned Exam Centre (e.g. Centre-Mumbai-01)"
            value={examCentre}
            onChange={(e) => setExamCentre(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50"
          />
          <input
            required
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full text-sm text-ink_text-500 file:mr-3 file:rounded-lg file:border-0 file:bg-signal/15 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-signal"
          />
        </div>

        {modalError && <p className="mt-3 text-sm text-risk-critical">{modalError}</p>}

        <div className="mt-6 flex gap-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 text-sm">
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn-primary flex-1 text-sm">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Upload & Encrypt"}
          </button>
        </div>
      </form>
    </div>
  );
}
