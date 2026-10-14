"use client";

import { useEffect, useState } from "react";
import { Settings as SettingsIcon, User, Shield } from "lucide-react";

export default function SettingsPage() {
  const [name, setName] = useState("");
  const [role, setRole] = useState("");

  useEffect(() => {
    setName(window.localStorage.getItem("satya_name") || "Demo User");
    setRole(window.localStorage.getItem("satya_role") || "administrator");
  }, []);

  return (
    <div className="p-6 sm:p-8">
      <header className="mb-6">
        <h1 className="font-display text-2xl text-ink_text-900">Settings</h1>
        <p className="mt-1 text-sm text-ink_text-500">Account and session details for this checkpoint.</p>
      </header>

      <div className="glass-card max-w-lg p-6">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-signal/15">
            <User className="h-5 w-5 text-signal" />
          </div>
          <div>
            <p className="font-medium text-ink_text-900">{name}</p>
            <p className="text-xs capitalize text-ink_text-500">{role.replaceAll("_", " ")}</p>
          </div>
        </div>

        <div className="mt-6 flex items-center gap-2 text-xs text-ink_text-500">
          <Shield className="h-3.5 w-3.5" /> Session secured with a JWT bearer token.
        </div>

        <div className="mt-6 flex items-center gap-2 rounded-lg border border-ink-700 bg-ink-800 px-4 py-3 text-xs text-ink_text-500">
          <SettingsIcon className="h-3.5 w-3.5" /> Full profile, notification, and theme preferences arrive in a
          later checkpoint.
        </div>
      </div>
    </div>
  );
}
