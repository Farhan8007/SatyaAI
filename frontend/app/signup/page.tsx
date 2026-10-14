"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AnimatedOrbs from "@/components/AnimatedOrbs";
import { ShieldCheck, Loader2 } from "lucide-react";
import { signUp } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [institution, setInstitution] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords don't match.");
      return;
    }
    if (password.length < 6) {
      setError("Password should be at least 6 characters.");
      return;
    }

    setLoading(true);
    const result = await signUp({ name, email, institution, password });
    setLoading(false);

    if (result.ok) {
      router.push("/login?justSignedUp=1");
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

        <form onSubmit={handleSubmit} className="glass-card p-8">
          <h1 className="font-display text-xl text-ink_text-900">Create your Administrator account</h1>
          <p className="mt-1 text-sm text-ink_text-500">
            This sets up SATYA AI for your institution. Once you're in, you can invite Paper
            Setters, Moderators, Examination Centres, and Security Auditors from the User
            Management page -- they'll log in directly with whatever email and password you give
            them.
          </p>

          <div className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink_text-500">Full name</label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 placeholder:text-ink_text-300 outline-none focus:border-signal/50 focus:ring-2 focus:ring-signal/20"
              />
            </div>
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
              <label className="mb-1.5 block text-xs font-medium text-ink_text-500">
                Institution <span className="text-ink_text-300">(optional)</span>
              </label>
              <input
                value={institution}
                onChange={(e) => setInstitution(e.target.value)}
                placeholder="Your college / institute"
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
            <div>
              <label className="mb-1.5 block text-xs font-medium text-ink_text-500">Confirm password</label>
              <input
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-ink-700 bg-ink-800 px-4 py-2.5 text-sm text-ink_text-900 outline-none focus:border-signal/50 focus:ring-2 focus:ring-signal/20"
              />
            </div>
          </div>

          {error && <p className="mt-3 text-sm text-risk-critical">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary mt-6 w-full">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Create account"}
          </button>

          <p className="mt-5 text-center text-sm text-ink_text-500">
            Already have an account?{" "}
            <Link href="/login" className="text-signal hover:text-signal-light">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </main>
  );
}
