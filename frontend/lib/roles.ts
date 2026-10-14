/**
 * Central place that defines which role can see which page, and where each
 * role lands right after login. Both the sidebar (what's shown) and the
 * dashboard layout (what's actually allowed, even via a typed-in URL) read
 * from this single source, so they can never drift out of sync.
 */

export type Role =
  | "administrator"
  | "paper_setter"
  | "moderator"
  | "examination_centre"
  | "security_auditor";

export const ROLE_LABELS: Record<Role, string> = {
  administrator: "Administrator",
  paper_setter: "Paper Setter",
  moderator: "Moderator",
  examination_centre: "Examination Centre",
  security_auditor: "Security Auditor",
};

// Where each role is sent immediately after logging in.
export const ROLE_HOME: Record<Role, string> = {
  administrator: "/dashboard",
  paper_setter: "/dashboard/papers",
  moderator: "/dashboard/papers",
  examination_centre: "/dashboard/papers",
  security_auditor: "/dashboard/audit-logs",
};

// Which roles may view each page. Settings has every role because it's
// just account info -- no sensitive data lives there.
export const PAGE_ACCESS: Record<string, Role[]> = {
  "/dashboard": ["administrator"],
  "/dashboard/papers": ["administrator", "paper_setter", "moderator", "examination_centre"],
  "/dashboard/alerts": ["administrator", "security_auditor"],
  "/dashboard/audit-logs": ["administrator", "security_auditor"],
  "/dashboard/reports": ["administrator", "security_auditor"],
  "/dashboard/users": ["administrator"],
  "/dashboard/settings": [
    "administrator",
    "paper_setter",
    "moderator",
    "examination_centre",
    "security_auditor",
  ],
};

export function isRole(value: string): value is Role {
  return value in ROLE_LABELS;
}
