"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertCircle,
  CheckSquare,
  BarChart2,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/opportunities", label: "Opportunities", icon: AlertCircle },
  { href: "/approvals", label: "Approvals", icon: CheckSquare },
  { href: "/analytics", label: "Analytics", icon: BarChart2 },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      style={{
        width: 220,
        minHeight: "100vh",
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: "20px 20px 16px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "center",
          gap: 10,
        }}
      >
        <div
          style={{
            width: 30,
            height: 30,
            background: "var(--navy)",
            borderRadius: 7,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 2px 5px rgba(25, 40, 57, 0.15)",
          }}
        >
          <Zap size={16} color="var(--accent)" strokeWidth={2.5} />
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: "0.875rem", letterSpacing: "-0.01em" }}>
            RecoverAI
          </div>
          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
            Revenue Recovery
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "12px 8px" }}>
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "7px 12px",
                borderRadius: "var(--radius)",
                marginBottom: 2,
                fontWeight: active ? 500 : 400,
                fontSize: "0.875rem",
                color: active ? "var(--accent)" : "var(--text-secondary)",
                background: active ? "var(--accent-light)" : "transparent",
                textDecoration: "none",
                transition: "background 0.12s, color 0.12s",
              }}
            >
              <Icon size={16} strokeWidth={active ? 2 : 1.75} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div
        style={{
          padding: "12px 20px",
          borderTop: "1px solid var(--border-subtle)",
          fontSize: "0.6875rem",
          color: "var(--text-muted)",
        }}
      >
        Test Mode • v0.1.0
      </div>
    </aside>
  );
}
