import clsx from "clsx";
import { Check, Clock, X } from "lucide-react";

const STATUS_CONFIG: Record<string, { style: string; icon: typeof Check; label: string }> = {
  approved: { style: "bg-intel/15 text-intel", icon: Check, label: "Approved" },
  pending: { style: "bg-risk-medium/15 text-risk-medium", icon: Clock, label: "Pending" },
  rejected: { style: "bg-risk-critical/15 text-risk-critical", icon: X, label: "Rejected" },
};

export default function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending;
  const Icon = cfg.icon;
  return (
    <span className={clsx("risk-pill", cfg.style)}>
      <Icon className="h-3 w-3" />
      {cfg.label}
    </span>
  );
}
