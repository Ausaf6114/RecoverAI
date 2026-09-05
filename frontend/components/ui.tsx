import React from "react";
import { cn } from "@/lib/utils";

// ─── Card ──────────────────────────────────────────────────────────────────

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  padding?: number | string;
}

export function Card({ children, padding = 20, className, style, ...props }: CardProps) {
  return (
    <div
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        boxShadow: "var(--shadow-sm)",
        padding,
        ...style,
      }}
      {...props}
    >
      {children}
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  accent?: boolean;
}

export function StatCard({ label, value, sub, accent }: StatCardProps) {
  return (
    <Card>
      <div
        style={{
          fontSize: "0.75rem",
          fontWeight: 500,
          color: "var(--text-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "1.5rem",
          fontWeight: 600,
          letterSpacing: "-0.03em",
          color: accent ? "var(--accent)" : "var(--text-primary)",
          lineHeight: 1,
          marginBottom: sub ? 6 : 0,
        }}
      >
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{sub}</div>
      )}
    </Card>
  );
}

// ─── Badge ────────────────────────────────────────────────────────────────

type BadgeVariant = "green" | "red" | "yellow" | "blue" | "purple" | "gray";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
}

const BADGE_STYLES: Record<BadgeVariant, React.CSSProperties> = {
  green: { background: "#ecfdf5", color: "#065f46", border: "1px solid #a7f3d0" },
  red: { background: "#fef2f2", color: "#991b1b", border: "1px solid #fca5a5" },
  yellow: { background: "#fffbeb", color: "#92400e", border: "1px solid #fde68a" },
  blue: { background: "#eff6ff", color: "#1e40af", border: "1px solid #bfdbfe" },
  purple: { background: "#faf5ff", color: "#6b21a8", border: "1px solid #d8b4fe" },
  gray: { background: "#f9fafb", color: "#374151", border: "1px solid #e5e7eb" },
};

export function Badge({ children, variant = "gray" }: BadgeProps) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        borderRadius: 4,
        padding: "2px 7px",
        fontSize: "0.6875rem",
        fontWeight: 500,
        whiteSpace: "nowrap",
        ...BADGE_STYLES[variant],
      }}
    >
      {children}
    </span>
  );
}

export function statusVariant(status: string): BadgeVariant {
  const map: Record<string, BadgeVariant> = {
    open: "blue",
    pending: "yellow",
    approved: "purple",
    completed: "green",
    recovered: "green",
    failed: "red",
    blocked: "red",
    no_action: "gray",
  };
  return map[status] ?? "gray";
}

// ─── Button ───────────────────────────────────────────────────────────────

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  loading?: boolean;
}

const BTN_STYLES: Record<string, React.CSSProperties> = {
  primary: {
    background: "var(--accent)",
    color: "#fff",
    border: "1px solid transparent",
  },
  secondary: {
    background: "#fff",
    color: "var(--text-primary)",
    border: "1px solid var(--border)",
  },
  ghost: {
    background: "transparent",
    color: "var(--text-secondary)",
    border: "1px solid transparent",
  },
  danger: {
    background: "#fef2f2",
    color: "#991b1b",
    border: "1px solid #fca5a5",
  },
};

export function Button({
  children,
  variant = "secondary",
  size = "md",
  loading,
  disabled,
  style,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        borderRadius: "var(--radius)",
        fontWeight: 500,
        cursor: disabled || loading ? "not-allowed" : "pointer",
        opacity: disabled ? 0.6 : 1,
        fontSize: size === "sm" ? "0.75rem" : "0.8125rem",
        padding: size === "sm" ? "4px 10px" : "6px 14px",
        transition: "opacity 0.1s",
        ...BTN_STYLES[variant],
        ...style,
      }}
      {...props}
    >
      {loading ? "Loading…" : children}
    </button>
  );
}

// ─── Table ────────────────────────────────────────────────────────────────

export function Table({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table
        style={{
          width: "100%",
          borderCollapse: "collapse",
          fontSize: "0.8125rem",
        }}
      >
        {children}
      </table>
    </div>
  );
}

export function Th({ children, right }: { children?: React.ReactNode; right?: boolean }) {
  return (
    <th
      style={{
        padding: "8px 12px",
        textAlign: right ? "right" : "left",
        fontWeight: 500,
        color: "var(--text-muted)",
        fontSize: "0.6875rem",
        textTransform: "uppercase",
        letterSpacing: "0.04em",
        borderBottom: "1px solid var(--border)",
        background: "var(--background)",
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </th>
  );
}

export function Td({ children, right, mono }: { children: React.ReactNode; right?: boolean; mono?: boolean }) {
  return (
    <td
      style={{
        padding: "9px 12px",
        textAlign: right ? "right" : "left",
        borderBottom: "1px solid var(--border-subtle)",
        color: "var(--text-primary)",
        fontFamily: mono ? "'SF Mono', 'Fira Code', monospace" : undefined,
        fontSize: mono ? "0.75rem" : undefined,
        whiteSpace: "nowrap",
      }}
    >
      {children}
    </td>
  );
}

// ─── Loading / Error / Empty ───────────────────────────────────────────────

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      style={{
        padding: "48px 24px",
        textAlign: "center",
        color: "var(--text-muted)",
        fontSize: "0.875rem",
      }}
    >
      {label}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div
      style={{
        padding: "24px",
        background: "#fef2f2",
        border: "1px solid #fca5a5",
        borderRadius: "var(--radius)",
        color: "#991b1b",
        fontSize: "0.8125rem",
      }}
    >
      <strong>Error:</strong> {message}
    </div>
  );
}

export function EmptyState({ message = "No data found." }: { message?: string }) {
  return (
    <div
      style={{
        padding: "48px 24px",
        textAlign: "center",
        color: "var(--text-muted)",
        fontSize: "0.875rem",
      }}
    >
      {message}
    </div>
  );
}

// ─── Page header ─────────────────────────────────────────────────────────

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        marginBottom: 24,
      }}
    >
      <div>
        <h1 style={{ marginBottom: subtitle ? 4 : 0 }}>{title}</h1>
        {subtitle && (
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
            {subtitle}
          </p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// ─── Section ─────────────────────────────────────────────────────────────

export function Section({
  title,
  children,
  action,
}: {
  title?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 28 }}>
      {title && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: 12,
          }}
        >
          <h2>{title}</h2>
          {action}
        </div>
      )}
      {children}
    </div>
  );
}

// ─── Divider ──────────────────────────────────────────────────────────────

export function Divider() {
  return (
    <hr
      style={{ border: "none", borderTop: "1px solid var(--border)", margin: "20px 0" }}
    />
  );
}

// ─── Key-value row ────────────────────────────────────────────────────────

export function KV({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-start",
        padding: "6px 0",
        borderBottom: "1px solid var(--border-subtle)",
        gap: 16,
        fontSize: "0.8125rem",
      }}
    >
      <span style={{ color: "var(--text-secondary)", flexShrink: 0 }}>{label}</span>
      <span style={{ color: "var(--text-primary)", textAlign: "right", wordBreak: "break-all" }}>
        {value}
      </span>
    </div>
  );
}
