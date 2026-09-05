import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

/** Format paise → INR with ₹ symbol */
export function formatINR(inr: number): string {
  if (inr >= 100_000) return `₹${(inr / 100_000).toFixed(1)}L`;
  if (inr >= 1_000) return `₹${(inr / 1_000).toFixed(1)}K`;
  return `₹${inr.toFixed(2)}`;
}

/** Format paise (integer) → INR */
export function paiseToINR(paise: number): string {
  return formatINR(paise / 100);
}

/** Format percentage */
export function pct(n: number, decimals = 1): string {
  return `${(n * 100).toFixed(decimals)}%`;
}

/** Relative time formatter */
export function relativeTime(isoStr: string | null): string {
  if (!isoStr) return "—";
  const diff = Date.now() - new Date(isoStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/** Status badge color map */
export const statusColors: Record<string, string> = {
  open: "badge-blue",
  pending: "badge-yellow",
  approved: "badge-purple",
  completed: "badge-green",
  recovered: "badge-green",
  failed: "badge-red",
  blocked: "badge-red",
  no_action: "badge-gray",
  train: "badge-gray",
  test: "badge-blue",
};

export function actionLabel(s: string): string {
  const map: Record<string, string> = {
    payment_link: "Payment Link",
    delayed_retry: "Delayed Retry",
    reminder: "Reminder",
    no_action: "No Action",
  };
  return map[s] ?? s;
}
