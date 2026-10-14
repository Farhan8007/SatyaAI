"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText, Clock, ShieldAlert, LogIn, XCircle, Activity, Sparkles } from "lucide-react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";
import StatCard from "@/components/StatCard";
import RiskBadge from "@/components/RiskBadge";
import ErrorState from "@/components/ErrorState";
import { getDashboardSummary, getAlerts, DashboardSummary, AlertItem, ApiError } from "@/lib/api";

const RISK_COLORS: Record<string, string> = {
  Low: "#18B8A1",
  Medium: "#E8A73D",
  High: "#F2793C",
  Critical: "#E8465B",
};

const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [allAlerts, setAllAlerts] = useState<AlertItem[]>([]);
  const [role, setRole] = useState<string>("");
  const [name, setName] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([getDashboardSummary(), getAlerts()])
      .then(([summary, alerts]) => {
        setData(summary);
        setAllAlerts(alerts);
      })
      .catch((err: ApiError) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setRole(window.localStorage.getItem("satya_role") || "");
    setName(window.localStorage.getItem("satya_name") || "");
    load();
  }, [load]);

  if (loading) {
    return <div className="p-8 text-ink_text-500">Loading dashboard…</div>;
  }

  if (error || !data) {
    return (
      <div className="p-6 sm:p-8">
        <ErrorState message={error ?? "Couldn't load the dashboard."} onRetry={load} />
      </div>
    );
  }

  const riskDistribution = ["Low", "Medium", "High", "Critical"].map((level) => ({
    name: level,
    value: allAlerts.filter((a) => a.risk_level === level).length,
    color: RISK_COLORS[level],
  }));
  const hasAnyAlerts = allAlerts.length > 0;

  return (
    <div className="p-6 sm:p-8">
      <motion.header
        initial="hidden"
        animate="show"
        variants={fadeUp}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="mb-8 flex flex-wrap items-center justify-between gap-4"
      >
        <div>
          <h1 className="font-display text-2xl text-ink_text-900">Security Dashboard</h1>
          <p className="mt-1 text-sm text-ink_text-500">
            Welcome back, {name} · <span className="capitalize">{role.replace("_", " ")}</span>
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-2xl bg-hero-gradient px-4 py-2.5 text-sm text-white shadow-card">
          <Sparkles className="h-3.5 w-3.5" />
          Overall risk score:{" "}
          <span className="font-mono font-semibold">{data.overall_risk_score}</span>/100
        </div>
      </motion.header>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard icon={FileText} label="Total Papers" value={data.total_papers} accent="intel" index={0} />
        <StatCard icon={Clock} label="Pending Approvals" value={data.pending_approvals} accent="amber" index={1} />
        <StatCard icon={LogIn} label="Today's Logins" value={data.todays_logins} accent="violet" index={2} />
        <StatCard icon={XCircle} label="Failed Logins" value={data.failed_logins_today} accent="rose" index={3} />
        <StatCard icon={ShieldAlert} label="Open Alerts" value={data.open_alerts} accent="signal" index={4} />
        <StatCard icon={Activity} label="Risk Score" value={`${data.overall_risk_score}`} accent="intel" index={5} />
      </div>

      {/* Chart + alerts */}
      <motion.div
        initial="hidden"
        animate="show"
        variants={fadeUp}
        transition={{ duration: 0.4, delay: 0.15, ease: "easeOut" }}
        className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3"
      >
        <div className="glass-card p-6 lg:col-span-2">
          <h2 className="font-display text-sm text-ink_text-700">Recent AI Alerts</h2>
          <div className="mt-4 space-y-3">
            {data.recent_alerts.length === 0 && (
              <p className="py-6 text-center text-sm text-ink_text-300">No alerts yet -- everything looks normal.</p>
            )}
            {data.recent_alerts.map((a, i) => (
              <motion.div
                key={a.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: 0.2 + i * 0.06 }}
                className="rounded-xl border border-ink-700 bg-ink-800 p-4 transition-colors duration-200 hover:border-signal/30 hover:bg-white"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-ink_text-900">{a.user_name}</span>
                  <RiskBadge level={a.risk_level} />
                </div>
                <p className="mt-1.5 text-xs text-ink_text-500">{a.reasons[0]}</p>
                <p className="mt-1 font-mono text-[11px] text-ink_text-300">Risk score: {a.risk_score}/100</p>
              </motion.div>
            ))}
          </div>
        </div>

        <div className="glass-card p-6">
          <h2 className="font-display text-sm text-ink_text-700">Risk Distribution</h2>
          {hasAnyAlerts ? (
            <>
              <div className="mt-2 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={riskDistribution}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={45}
                      outerRadius={72}
                      paddingAngle={4}
                      animationDuration={700}
                      animationEasing="ease-out"
                    >
                      {riskDistribution.map((entry) => (
                        <Cell key={entry.name} fill={entry.color} stroke="none" />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ background: "#FFFFFF", border: "1px solid #E3E7F1", borderRadius: 12, color: "#1B2233" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 flex flex-wrap justify-center gap-3 text-xs text-ink_text-500">
                {riskDistribution.map((r) => (
                  <span key={r.name} className="flex items-center gap-1.5">
                    <span className="h-2 w-2 rounded-full" style={{ background: r.color }} />
                    {r.name} ({r.value})
                  </span>
                ))}
              </div>
            </>
          ) : (
            <p className="flex h-56 items-center justify-center text-center text-sm text-ink_text-300">
              No AI alerts yet -- this chart fills in once activity starts happening.
            </p>
          )}
        </div>
      </motion.div>

      {/* Activity timeline */}
      <motion.div
        initial="hidden"
        animate="show"
        variants={fadeUp}
        transition={{ duration: 0.4, delay: 0.28, ease: "easeOut" }}
        className="mt-6 glass-card p-6"
      >
        <h2 className="font-display text-sm text-ink_text-700">Live Activity Feed</h2>
        <div className="mt-4 space-y-3">
          {data.activity_timeline.length === 0 && (
            <p className="py-6 text-center text-sm text-ink_text-300">
              No activity yet -- actions like logins, uploads, and approvals will show up here.
            </p>
          )}
          {data.activity_timeline.map((t, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <span
                className={`h-2 w-2 shrink-0 rounded-full ${
                  t.status === "SUCCESS" ? "bg-intel" : "bg-risk-critical"
                }`}
              />
              <span className="text-ink_text-700">{t.user_name}</span>
              <span className="text-ink_text-300">·</span>
              <span className="text-ink_text-500">{t.action.replaceAll("_", " ").toLowerCase()}</span>
              <span className="ml-auto font-mono text-[11px] text-ink_text-300">
                {new Date(t.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
