"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import AnimatedOrbs from "@/components/AnimatedOrbs";
import { ShieldCheck, Loader2, CheckCircle2 } from "lucide-react";
import { login } from "@/lib/api";
import { ROLE_HOME, isRole } from "@/lib/roles";

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginPageContent />
    </Suspense>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const justSignedUp = searchParams.get("justSignedUp") === "1";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    const result = await login(email, password);
    setLoading(false);

    if (result.ok) {
      window.localStorage.setItem("satya_token", result.data.access_token);
      window.localStorage.setItem("satya_role", result.data.role);
      window.localStorage.setItem("satya_name", result.data.name);
      const role = result.data.role;
      router.push(isRole(role) ? ROLE_HOME[role] : "/dashboard");
    } else {
      setError(result.error);
    }
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-ink-950 px-6">
      <AnimatedOrbs />

      <div className="relative z-10 w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-2">
          <ShieldCheck className="h-6 w-6 text-signal" />
          <span className="font-display text-xl tracking-tight">SATYA AI</span>
        </div>

        {justSignedUp && (
          <div className="mb-4 flex items-center gap-2 rounded-xl border border-intel/20 bg-intel/10 px-4 py-3 text-sm text-intel">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            Account created. Check your inbox for a verification link before signing in.
          </div>
        )}

        <form onSubmit={handleSubmit} className="glass-card p-8">
          <h1 className="font-display text-xl text-ink_text-900">Sign in</h1>
          <p className="mt-1 text-sm text-ink_text-500">Access your role-based security dashboard.</p>

          <div className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink_text-500">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@institution.edu"
                className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50 focus:ring-2 focus:ring-signal/20"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink_text-500">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 outline-none focus:border-signal/50 focus:ring-2 focus:ring-signal/20"
              />
            </div>
          </div>

          {error && <p className="mt-3 text-sm text-risk-critical">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary mt-6 w-full">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign in"}
          </button>

          <p className="mt-5 text-center text-sm text-ink_text-500">
            Setting this up for the first time?{" "}
            <Link href="/signup" className="text-signal hover:text-signal-light">
              Create an Administrator account
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
