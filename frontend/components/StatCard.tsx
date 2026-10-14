"use client";

import { LucideIcon } from "lucide-react";
import { motion } from "framer-motion";
import clsx from "clsx";

const ACCENT_STYLES = {
  signal: { chip: "bg-signal/10", icon: "text-signal" },
  intel: { chip: "bg-intel/10", icon: "text-intel" },
  violet: { chip: "bg-violet-soft", icon: "text-violet" },
  amber: { chip: "bg-amber-soft", icon: "text-amber" },
  rose: { chip: "bg-rose-soft", icon: "text-rose" },
  white: { chip: "bg-ink-800", icon: "text-ink_text-500" },
} as const;

export default function StatCard({
  icon: Icon,
  label,
  value,
  accent = "signal",
  index = 0,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number;
  accent?: keyof typeof ACCENT_STYLES;
  index?: number;
}) {
  const style = ACCENT_STYLES[accent];
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: index * 0.05, ease: "easeOut" }}
      whileHover={{ y: -3 }}
      className="glass-card p-5 transition-shadow duration-200 hover:shadow-card-hover"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-ink_text-500">{label}</span>
        <div className={clsx("flex h-8 w-8 items-center justify-center rounded-xl", style.chip)}>
          <Icon className={clsx("h-4 w-4", style.icon)} />
        </div>
      </div>
      <div className="mt-3 font-display text-2xl text-ink_text-900">{value}</div>
    </motion.div>
  );
}
