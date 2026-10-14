"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import AnimatedOrbs from "@/components/AnimatedOrbs";
import { ShieldCheck, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { verifyEmail } from "@/lib/api";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<"checking" | "success" | "error">("checking");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("This verification link is missing its token.");
      return;
    }
    verifyEmail(token).then((result) => {
      if (result.ok) {
        setStatus("success");
        setMessage(result.message);
      } else {
        setStatus("error");
        setMessage(result.error);
      }
    });
  }, [token]);

  return (
    <main className="relative flex min-h-screen items-center justify-center overflow-hidden bg-ink-950 px-6">
      <AnimatedOrbs />

      <div className="relative z-10 w-full max-w-md text-center">
        <div className="mb-8 flex items-center justify-center gap-2">
          <ShieldCheck className="h-6 w-6 text-signal" />
          <span className="font-display text-xl tracking-tight">SATYA AI</span>
        </div>

        <div className="glass-card p-8">
          {status === "checking" && (
            <>
              <Loader2 className="mx-auto h-8 w-8 animate-spin text-ink_text-500" />
              <p className="mt-4 text-sm text-ink_text-500">Verifying your email…</p>
            </>
          )}

          {status === "success" && (
            <>
              <CheckCircle2 className="mx-auto h-8 w-8 text-intel" />
              <h1 className="mt-4 font-display text-lg text-ink_text-900">Email verified</h1>
              <p className="mt-2 text-sm text-ink_text-500">{message}</p>
              <Link href="/login" className="btn-primary mt-6 inline-flex">
                Go to sign in
              </Link>
            </>
          )}

          {status === "error" && (
            <>
              <XCircle className="mx-auto h-8 w-8 text-risk-critical" />
              <h1 className="mt-4 font-display text-lg text-ink_text-900">Verification failed</h1>
              <p className="mt-2 text-sm text-ink_text-500">{message}</p>
              <Link href="/login" className="btn-secondary mt-6 inline-flex">
                Back to sign in
              </Link>
            </>
          )}
        </div>
      </div>
    </main>
  );
}
