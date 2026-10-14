import { AlertCircle, RefreshCw } from "lucide-react";

export default function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="glass-card flex flex-col items-center gap-3 p-10 text-center">
      <AlertCircle className="h-6 w-6 text-risk-critical" />
      <p className="max-w-sm text-sm text-ink_text-500">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-1 inline-flex items-center gap-1.5 rounded-lg border border-ink-700 bg-ink-800 px-3 py-1.5 text-xs text-ink_text-700 hover:border-signal/40"
        >
          <RefreshCw className="h-3 w-3" /> Try again
        </button>
      )}
    </div>
  );
}
