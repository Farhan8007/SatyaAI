import Link from "next/link";
import AnimatedOrbs from "@/components/AnimatedOrbs";
import { ShieldCheck, Brain, Search, FileWarning, Lock, ScanEye, ArrowRight } from "lucide-react";

const pillars = [
  {
    icon: Lock,
    title: "Secure by Design",
    body: "Encryption, digital signatures, and role-based access across the entire paper lifecycle.",
  },
  {
    icon: Brain,
    title: "Intelligence Layer",
    body: "AI-driven anomaly detection replaces manual, reactive monitoring with continuous behavioural analysis.",
  },
  {
    icon: ScanEye,
    title: "Forensic Readiness",
    body: "Every action is explainable, traceable, and investigable long after it happens.",
  },
];

const workflow = [
  "Create & Encrypt",
  "Digital Signature",
  "Role-Based Approval",
  "Tamper-Evident Log",
  "AI Monitors Activity",
  "Secure Distribution",
];

const stats = [
  { value: "0-100", label: "Quantified risk score per action" },
  { value: "SHA-256", label: "Chained, tamper-evident audit trail" },
  { value: "9", label: "Behavioural signals scored per event" },
];

export default function LandingPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-ink-950">
      <AnimatedOrbs />

      {/* Nav */}
      <nav className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-signal" />
          <span className="font-display text-lg tracking-tight">SATYA AI</span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/login" className="text-sm text-ink_text-700 hover:text-ink_text-900">
            Sign in
          </Link>
          <Link href="/signup" className="btn-primary text-sm">
            Get started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative z-10 mx-auto max-w-4xl px-6 pt-16 text-center sm:pt-24">
        <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-ink-700 bg-ink-800 px-4 py-1.5 text-xs font-medium tracking-wide text-intel">
          FINAL YEAR PROJECT · CYBERSECURITY & DIGITAL FORENSICS
        </p>
        <h1 className="font-display text-4xl font-medium leading-tight tracking-tight sm:text-6xl">
          From preventing leaks to
          <span className="block text-signal">explaining, reconstructing, and proving them.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-balance text-ink_text-500 sm:text-lg">
          SATYA AI secures question papers across their entire lifecycle and gives investigators
          plain-language, AI-generated answers to the question every leak raises: what actually happened?
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link href="/signup" className="btn-primary">
            Get started <ArrowRight className="h-4 w-4" />
          </Link>
          <a href="#how-it-works" className="btn-secondary">
            How it works
          </a>
        </div>
      </section>

      {/* Stats strip */}
      <section className="relative z-10 mx-auto mt-20 grid max-w-4xl grid-cols-1 gap-4 px-6 sm:grid-cols-3">
        {stats.map((s) => (
          <div key={s.label} className="glass-card px-6 py-5 text-center">
            <div className="font-mono text-2xl font-semibold text-intel">{s.value}</div>
            <div className="mt-1 text-xs text-ink_text-500">{s.label}</div>
          </div>
        ))}
      </section>

      {/* Pillars */}
      <section className="relative z-10 mx-auto mt-24 max-w-6xl px-6">
        <h2 className="text-center font-display text-2xl text-ink_text-900 sm:text-3xl">
          Three pillars, one examination lifecycle
        </h2>
        <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-3">
          {pillars.map((p) => (
            <div key={p.title} className="glass-card p-6">
              <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-signal/15">
                <p.icon className="h-5 w-5 text-signal" />
              </div>
              <h3 className="font-display text-lg text-ink_text-900">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink_text-500">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="relative z-10 mx-auto mt-24 max-w-6xl px-6">
        <h2 className="text-center font-display text-2xl text-ink_text-900 sm:text-3xl">
          One workflow, fully monitored
        </h2>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          {workflow.map((step, i) => (
            <div key={step} className="flex items-center gap-3">
              <div className="glass-card px-4 py-2.5 text-sm text-ink_text-700">{step}</div>
              {i < workflow.length - 1 && <ArrowRight className="h-4 w-4 shrink-0 text-ink_text-300" />}
            </div>
          ))}
        </div>
      </section>

      {/* Explainable AI callout */}
      <section className="relative z-10 mx-auto mt-24 max-w-4xl px-6">
        <div className="glass-card overflow-hidden p-8 sm:p-10">
          <div className="flex items-center gap-2 text-signal">
            <FileWarning className="h-5 w-5" />
            <span className="text-xs font-semibold uppercase tracking-wide">Sample explainable alert</span>
          </div>
          <p className="mt-4 font-display text-xl text-ink_text-900">High Risk — Score 91/100</p>
          <ul className="mt-4 space-y-2 text-sm text-ink_text-500">
            <li>· User logged in at 2:18 AM from a new device</li>
            <li>· Downloaded the paper three times within 40 minutes</li>
            <li>· Approval workflow was skipped before distribution</li>
          </ul>
          <p className="mt-5 rounded-lg border border-signal/20 bg-signal/10 px-4 py-3 text-sm text-signal-light">
            Recommended action: suspend account and escalate to Security Auditor.
          </p>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 mx-auto mb-24 mt-24 max-w-2xl px-6 text-center">
        <h2 className="font-display text-2xl text-ink_text-900 sm:text-3xl">Set this up for your institution</h2>
        <p className="mt-3 text-ink_text-500">
          Create your Administrator account, then invite Paper Setters, Moderators, Examination
          Centres, and Security Auditors with the credentials you choose for them.
        </p>
        <Link href="/signup" className="btn-primary mt-6 inline-flex">
          Get started <ArrowRight className="h-4 w-4" />
        </Link>
      </section>

      <footer className="relative z-10 border-t border-ink-700 py-8 text-center text-xs text-ink_text-300">
        SATYA AI — B.Tech Final Year Project · Domain: Cybersecurity · Application: Examination Security
      </footer>
    </main>
  );
}
