/**
 * Fetch wrapper around the SATYA AI FastAPI backend.
 *
 * IMPORTANT: this file used to fall back to hardcoded "mock" data whenever
 * a request failed, so the UI would always show *something*. That was
 * misleading for a security product -- it meant a failed or expired login
 * could silently show fake records that looked real. This version never
 * does that: failures throw a real error (which pages display), and an
 * expired/invalid session (401) clears local storage and sends you back
 * to /login instead of pretending to have data.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("satya_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function clearSessionAndRedirect() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("satya_token");
  window.localStorage.removeItem("satya_role");
  window.localStorage.removeItem("satya_name");
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...authHeaders(), ...(init?.headers || {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      "Can't reach the backend. Make sure it's running (uvicorn app.main:app --reload).",
      0
    );
  }

  if (res.status === 401) {
    clearSessionAndRedirect();
    throw new ApiError("Your session expired. Please sign in again.", 401);
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // response wasn't JSON -- keep the generic message
    }
    throw new ApiError(detail, res.status);
  }

  return (await res.json()) as T;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface LoginResponse {
  access_token: string;
  token_type: string;
  role: string;
  name: string;
}

export async function login(
  email: string,
  password: string
): Promise<{ ok: true; data: LoginResponse } | { ok: false; error: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, error: body?.detail || "Incorrect email or password. Please try again." };
    }
    return { ok: true, data: (await res.json()) as LoginResponse };
  } catch {
    return { ok: false, error: "Can't reach the backend. Make sure it's running." };
  }
}

export async function verifyEmail(token: string): Promise<{ ok: true; message: string } | { ok: false; error: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/verify-email?token=${encodeURIComponent(token)}`);
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      return { ok: false, error: body?.detail || "Verification failed." };
    }
    return { ok: true, message: body?.detail || "Email verified." };
  } catch {
    return { ok: false, error: "Can't reach the backend. Make sure it's running." };
  }
}

// Public self-registration -- always creates an Administrator account.
// This is meant for the first person setting up the system; everyone else
// gets invited by that Administrator from the User Management page.
export async function signUp(payload: {
  name: string;
  email: string;
  institution?: string;
  password: string;
}): Promise<{ ok: true } | { ok: false; error: string }> {
  try {
    const res = await fetch(`${API_BASE}/api/auth/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, role: "administrator" }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      return { ok: false, error: body?.detail || "Could not create account." };
    }
    return { ok: true };
  } catch {
    return { ok: false, error: "Could not reach the server. Is the backend running?" };
  }
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export interface DashboardSummary {
  total_papers: number;
  pending_approvals: number;
  todays_logins: number;
  failed_logins_today: number;
  open_alerts: number;
  overall_risk_score: number;
  recent_alerts: Array<{
    id: string;
    user_name: string;
    risk_level: "Low" | "Medium" | "High" | "Critical";
    risk_score: number;
    reasons: string[];
  }>;
  activity_timeline: Array<{
    timestamp: string;
    user_name: string;
    action: string;
    status: string;
  }>;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return authFetch("/api/dashboard/summary");
}

// ---------------------------------------------------------------------------
// Question Papers
// ---------------------------------------------------------------------------

export interface Paper {
  id: string;
  title: string;
  subject: string;
  exam_date: string;
  exam_centre: string | null;
  setter_id: string;
  setter_name: string;
  status: "pending" | "approved" | "rejected";
  sha256_hash: string;
  signature: string;
  is_encrypted: boolean;
  unlock_time: string | null;
  created_at: string;
  remarks: string | null;
}

export async function getPapers(): Promise<Paper[]> {
  return authFetch("/api/papers/");
}

export async function approvePaper(id: string, remarks = ""): Promise<Paper> {
  return authFetch(`/api/papers/${id}/approve?remarks=${encodeURIComponent(remarks)}`, { method: "POST" });
}

export async function rejectPaper(id: string, remarks = ""): Promise<Paper> {
  return authFetch(`/api/papers/${id}/reject?remarks=${encodeURIComponent(remarks)}`, { method: "POST" });
}

export async function uploadPaper(formData: FormData): Promise<Paper> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/papers/upload`, {
      method: "POST",
      headers: authHeaders(), // no Content-Type -- browser sets multipart boundary
      body: formData,
    });
  } catch {
    throw new ApiError("Can't reach the backend. Make sure it's running.", 0);
  }
  if (res.status === 401) {
    clearSessionAndRedirect();
    throw new ApiError("Your session expired. Please sign in again.", 401);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail || `Upload failed (${res.status})`, res.status);
  }
  return (await res.json()) as Paper;
}

export async function unlockPaper(id: string): Promise<{ detail: string; sha256_hash: string }> {
  return authFetch(`/api/papers/${id}/unlock`, { method: "POST" });
}

// ---------------------------------------------------------------------------
// Audit Logs
// ---------------------------------------------------------------------------

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user_name: string;
  role: string;
  ip_address: string;
  location: string;
  device: string;
  action: string;
  status: "SUCCESS" | "FAILED";
  paper_id: string | null;
  hash: string;
}

export async function getAuditLogs(limit = 100): Promise<AuditLogEntry[]> {
  return authFetch(`/api/audit-logs/?limit=${limit}`);
}

export interface IntegrityCheck {
  intact: boolean;
  entries_checked: number;
}

export async function verifyIntegrity(): Promise<IntegrityCheck> {
  return authFetch("/api/audit-logs/verify-integrity");
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

export interface AlertItem {
  id: string;
  created_at: string;
  user_id: string;
  user_name: string;
  risk_score: number;
  risk_level: "Low" | "Medium" | "High" | "Critical";
  reasons: string[];
  confidence: number;
  recommended_action: string;
  related_paper_id: string | null;
  resolved: boolean;
}

export async function getAlerts(resolved?: boolean): Promise<AlertItem[]> {
  const query = resolved === undefined ? "" : `?resolved=${resolved}`;
  return authFetch(`/api/alerts/${query}`);
}

export async function resolveAlert(id: string): Promise<void> {
  await authFetch(`/api/alerts/${id}/resolve`, { method: "POST" });
}

// ---------------------------------------------------------------------------
// Investigation Reports
// ---------------------------------------------------------------------------

export interface IncidentReport {
  incident_id: string;
  generated_at: string;
  summary: string;
  timeline: Array<{ timestamp: string; actor: string; action: string; status: string }>;
  users_involved: string[];
  risk_level: string;
  contributing_factors: string[];
  recommended_action: string;
}

export async function generateReport(alertId: string): Promise<IncidentReport> {
  return authFetch(`/api/reports/incident/${alertId}`, { method: "POST" });
}

export async function getReport(incidentId: string): Promise<IncidentReport> {
  return authFetch(`/api/reports/incident/${incidentId}`);
}

export async function listReports(): Promise<IncidentReport[]> {
  return authFetch("/api/reports/");
}

export function reportPdfUrl(incidentId: string): string {
  return `${API_BASE}/api/reports/incident/${incidentId}/pdf`;
}

// ---------------------------------------------------------------------------
// User Management
// ---------------------------------------------------------------------------

export type UserRole = "administrator" | "paper_setter" | "moderator" | "examination_centre" | "security_auditor";

export interface AppUser {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  institution: string | null;
  created_at: string;
  last_login: string | null;
  is_active: boolean;
}

export async function getUsers(): Promise<AppUser[]> {
  return authFetch("/api/users/");
}

export async function updateUserRole(id: string, role: UserRole): Promise<AppUser> {
  return authFetch(`/api/users/${id}/role`, { method: "PATCH", body: JSON.stringify({ role }) });
}

export async function updateUserStatus(id: string, isActive: boolean): Promise<AppUser> {
  return authFetch(`/api/users/${id}/status?is_active=${isActive}`, { method: "PATCH" });
}

export async function createUser(payload: {
  name: string;
  email: string;
  role: UserRole;
  institution?: string;
  password: string;
}): Promise<AppUser> {
  return authFetch("/api/auth/signup", { method: "POST", body: JSON.stringify(payload) });
}

export async function deleteUser(id: string): Promise<{ detail: string }> {
  return authFetch(`/api/users/${id}`, { method: "DELETE" });
}
