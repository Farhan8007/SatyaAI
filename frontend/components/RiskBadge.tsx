import clsx from "clsx";

const RISK_STYLES: Record<string, string> = {
  Low: "bg-risk-low/15 text-risk-low",
  Medium: "bg-risk-medium/15 text-risk-medium",
  High: "bg-risk-high/15 text-risk-high",
  Critical: "bg-risk-critical/15 text-risk-critical",
};

export default function RiskBadge({ level }: { level: string }) {
  return (
    <span className={clsx("risk-pill", RISK_STYLES[level] ?? "bg-ink-700 text-ink_text-500")}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {level}
    </span>
  );
}
