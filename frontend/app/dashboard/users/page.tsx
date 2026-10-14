"use client";

import { useEffect, useState } from "react";
import { UserPlus, Loader2, ShieldOff, ShieldCheck, Trash2 } from "lucide-react";
import ErrorState from "@/components/ErrorState";
import {
  getUsers,
  updateUserRole,
  updateUserStatus,
  createUser,
  deleteUser,
  AppUser,
  UserRole,
  ApiError,
} from "@/lib/api";

const ROLES: UserRole[] = ["administrator", "paper_setter", "moderator", "examination_centre", "security_auditor"];

const ROLE_LABELS: Record<UserRole, string> = {
  administrator: "Administrator",
  paper_setter: "Paper Setter",
  moderator: "Moderator",
  examination_centre: "Examination Centre",
  security_auditor: "Security Auditor",
};

export default function UsersPage() {
  const [users, setUsers] = useState<AppUser[]>([]);
  const [myRole, setMyRole] = useState("");
  const [showInvite, setShowInvite] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    setMyRole(window.localStorage.getItem("satya_role") || "");
    refresh();
  }, []);

  function refresh() {
    setLoading(true);
    setError(null);
    getUsers()
      .then(setUsers)
      .catch((err: ApiError) => setError(err.message))
      .finally(() => setLoading(false));
  }

  async function handleRoleChange(id: string, role: UserRole) {
    setBusyId(id);
    setActionError(null);
    try {
      const updated = await updateUserRole(id, role);
      setUsers((prev) => prev.map((u) => (u.id === id ? updated : u)));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't update the role.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleToggleStatus(u: AppUser) {
    setBusyId(u.id);
    setActionError(null);
    try {
      const updated = await updateUserStatus(u.id, !u.is_active);
      setUsers((prev) => prev.map((x) => (x.id === u.id ? updated : x)));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't update this account's status.");
    } finally {
      setBusyId(null);
    }
  }

  async function handleDelete(u: AppUser) {
    const confirmed = window.confirm(
      `Remove ${u.name} (${u.email})? Their email will become available again to invite someone new.`
    );
    if (!confirmed) return;

    setBusyId(u.id);
    setActionError(null);
    try {
      await deleteUser(u.id);
      setUsers((prev) => prev.filter((x) => x.id !== u.id));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : "Couldn't remove this account.");
    } finally {
      setBusyId(null);
    }
  }

  const isAdmin = myRole === "administrator";

  if (loading) {
    return <div className="p-8 text-ink_text-500">Loading users…</div>;
  }

  return (
    <div className="p-6 sm:p-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl text-ink_text-900">User Management</h1>
          <p className="mt-1 text-sm text-ink_text-500">
            Assign roles and control access across every stage of the examination lifecycle.
          </p>
        </div>
        {isAdmin && (
          <button onClick={() => setShowInvite(true)} className="btn-primary text-sm">
            <UserPlus className="h-4 w-4" /> Invite User
          </button>
        )}
      </header>

      {!isAdmin && (
        <div className="mb-5 rounded-xl border border-risk-medium/20 bg-risk-medium/10 px-4 py-3 text-sm text-risk-medium">
          User management is restricted to Administrators. You're viewing in read-only mode.
        </div>
      )}

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
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink-700 text-xs text-ink_text-500">
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Email</th>
                <th className="px-4 py-3 font-medium">Role</th>
                <th className="px-4 py-3 font-medium">Last Login</th>
                <th className="px-4 py-3 font-medium">Status</th>
                {isAdmin && <th className="px-4 py-3 font-medium">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-ink-700 hover:bg-ink-800">
                  <td className="px-4 py-3 text-ink_text-900">{u.name}</td>
                  <td className="px-4 py-3 font-mono text-[12px] text-ink_text-500">{u.email}</td>
                  <td className="px-4 py-3">
                    {isAdmin ? (
                      <select
                        value={u.role}
                        disabled={busyId === u.id}
                        onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                        className="rounded-lg border border-ink-700 bg-ink-800 px-2 py-1 text-xs text-ink_text-900 outline-none focus:border-signal/50"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r} className="bg-ink-900">
                            {ROLE_LABELS[r]}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-ink_text-500">{ROLE_LABELS[u.role]}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-ink_text-500">
                    {u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        u.is_active ? "bg-intel/15 text-intel" : "bg-risk-critical/15 text-risk-critical"
                      }`}
                    >
                      {u.is_active ? "Active" : "Suspended"}
                    </span>
                  </td>
                  {isAdmin && (
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleToggleStatus(u)}
                          disabled={busyId === u.id}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-ink-700 bg-ink-800 px-2.5 py-1 text-xs text-ink_text-500 hover:border-signal/40"
                        >
                          {busyId === u.id ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : u.is_active ? (
                            <ShieldOff className="h-3 w-3" />
                          ) : (
                            <ShieldCheck className="h-3 w-3" />
                          )}
                          {u.is_active ? "Suspend" : "Reactivate"}
                        </button>
                        {u.role !== "administrator" && (
                          <button
                            onClick={() => handleDelete(u)}
                            disabled={busyId === u.id}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-ink-700 bg-ink-800 px-2.5 py-1 text-xs text-ink_text-500 hover:border-risk-critical/30 hover:text-risk-critical"
                          >
                            <Trash2 className="h-3 w-3" />
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={isAdmin ? 6 : 5} className="px-4 py-10 text-center text-ink_text-500">
                    No other users yet -- invite one from the button above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {showInvite && (
        <InviteModal
          onClose={() => setShowInvite(false)}
          onCreated={(u) => {
            setUsers((prev) => [u, ...prev]);
            setShowInvite(false);
          }}
        />
      )}
    </div>
  );
}

function InviteModal({ onClose, onCreated }: { onClose: () => void; onCreated: (u: AppUser) => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [institution, setInstitution] = useState("");
  const [role, setRole] = useState<UserRole>("paper_setter");
  const [loading, setLoading] = useState(false);
  const [modalError, setModalError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setModalError("");
    try {
      const result = await createUser({ name, email, role, institution, password });
      onCreated(result);
    } catch (err) {
      setModalError(err instanceof ApiError ? err.message : "Couldn't create this account.");
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
        <h2 className="font-display text-lg text-ink_text-900">Invite User</h2>
        <p className="mt-1 text-xs text-ink_text-500">
          Set their login email and password here -- share these with them directly.
        </p>

        <div className="mt-5 space-y-3">
          <input
            required
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50"
          />
          <input
            required
            type="email"
            placeholder="Email (this is their login)"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50"
          />
          <input
            required
            type="text"
            placeholder="Password (this is their login password)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50"
          />
          <input
            placeholder="Institution (optional)"
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 outline-none focus:border-signal/50"
          >
            {ROLES.map((r) => (
              <option key={r} value={r} className="bg-ink-900">
                {ROLE_LABELS[r]}
              </option>
            ))}
          </select>
        </div>

        {modalError && <p className="mt-3 text-sm text-risk-critical">{modalError}</p>}

        <div className="mt-6 flex gap-2">
          <button type="button" onClick={onClose} className="btn-secondary flex-1 text-sm">
            Cancel
          </button>
          <button type="submit" disabled={loading} className="btn-primary flex-1 text-sm">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send Invite"}
          </button>
        </div>
      </form>
    </div>
  );
}
