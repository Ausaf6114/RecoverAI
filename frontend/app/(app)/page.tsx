"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, TrendingUp, Clock, CheckCircle2, AlertTriangle } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
  LabelList,
} from "recharts";
import { api, AnalyticsResponse, OpportunitySummary } from "@/lib/api";
import { formatINR, pct, relativeTime, actionLabel } from "@/lib/utils";
import {
  StatCard,
  Badge,
  statusVariant,
  Loading,
  ErrorState,
  PageHeader,
  Section,
  Card,
  Table,
  Th,
  Td,
  Button,
} from "@/components/ui";

// Canonical color map — matches Analytics page exactly
const ACTION_COLORS: Record<string, string> = {
  payment_link: "#3395FF",   // Razorpay blue
  delayed_retry: "#00C48C",  // Razorpay green (was #192839 — FIXED)
  reminder: "#f59e0b",       // Amber
  no_action: "#94a3b8",      // Neutral slate
};

export default function OverviewPage() {
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [opps, setOpps] = useState<OpportunitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getAnalytics(), api.listOpportunities({ limit: 8 })])
      .then(([a, o]) => {
        setAnalytics(a);
        setOpps(o);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading overview…" />;
  if (error) return <ErrorState message={error} />;
  if (!analytics) return null;

  const actionBreakdownData = Object.entries(analytics.action_breakdown).map(
    ([k, v]) => ({ name: actionLabel(k), count: v, key: k })
  );

  const bb = analytics.baseline_benchmark;

  return (
    <div>
      {/* Top Banner with Soft Organic Gradient Blob Accent */}
      <div style={{ position: "relative", marginBottom: 28 }}>
        <div className="organic-blob-header" aria-hidden="true" />
        
        <div style={{ position: "relative", zIndex: 1 }}>
          <PageHeader
            title="Overview"
            subtitle="Live revenue recovery performance & autonomous interventions"
            action={
              <Link href="/opportunities">
                <Button variant="primary" size="sm">
                  View Opportunities <ArrowRight size={13} />
                </Button>
              </Link>
            }
          />

          {/* Top KPI Strip */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, 1fr)",
              gap: 16,
            }}
          >
            <StatCard
              label="Revenue at Risk"
              value={formatINR(analytics.total_at_risk_gmv_inr)}
              sub={`${analytics.total_opportunities} opportunities`}
            />
            <StatCard
              label="Recovered Revenue"
              value={formatINR(analytics.total_recovered_gmv_inr)}
              sub={`${analytics.recovered_opportunities} recovered`}
              accent
            />
            <StatCard
              label="Net Revenue"
              value={formatINR(analytics.net_revenue_inr)}
              sub={`After ₹${analytics.total_action_cost_inr.toFixed(0)} action cost`}
            />
            <StatCard
              label="Recovery Rate"
              value={pct(analytics.recovery_rate)}
              sub={`Baseline ${pct(bb.baseline_recovery_rate)}`}
            />
          </div>
        </div>
      </div>

      {/* AI Uplift Banner */}
      <Card
        padding="16px 20px"
        style={{
          marginBottom: 28,
          borderLeft: "3px solid var(--success)",
          background: "linear-gradient(90deg, #f0fdf9 0%, #ffffff 70%)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "var(--success-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <TrendingUp size={18} color="var(--success-dark)" />
            </div>
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--navy)" }}>
                RecoverAI Uplift vs. Baseline
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                Additional {formatINR(bb.incremental_recovered_gmv_inr)} recovered beyond the 35% fixed-policy baseline
              </div>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div
              style={{
                fontSize: "1.375rem",
                fontWeight: 600,
                color: "var(--success-dark)",
                letterSpacing: "-0.02em",
              }}
            >
              +{bb.uplift_percentage.toFixed(1)}%
            </div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              uplift
            </div>
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 28 }}>
        <Section title="Action Breakdown">
          <Card>
            {actionBreakdownData.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
                No actions yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart
                  data={actionBreakdownData}
                  margin={{ top: 28, right: 16, bottom: 8, left: -16 }}
                  barSize={54}
                >
                  <CartesianGrid
                    vertical={false}
                    stroke="#f1f5f9"
                    strokeDasharray="0"
                  />
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "#6b7280", fontWeight: 500 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "#9ca3af" }}
                    axisLine={false}
                    tickLine={false}
                    allowDecimals={false}
                  />
                  <Tooltip
                    cursor={{ fill: "rgba(51,149,255,0.06)", radius: 6 }}
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                      boxShadow: "0 4px 12px rgba(25,40,57,0.08)",
                      padding: "8px 12px",
                    }}
                    formatter={(value: any, name: any) => [value, "Actions"]}
                    labelStyle={{ fontWeight: 600, color: "var(--navy)", marginBottom: 2 }}
                  />
                  <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                    <LabelList
                      dataKey="count"
                      position="top"
                      style={{ fontSize: 11, fontWeight: 600, fill: "var(--text-secondary)" }}
                    />
                    {actionBreakdownData.map((entry) => (
                      <Cell
                        key={entry.key}
                        fill={ACTION_COLORS[entry.key] ?? "#94a3b8"}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Section>

        {/* Quick Stats */}
        <Section title="Pipeline Status">
          <Card>
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {[
                {
                  icon: <Clock size={14} color="var(--accent)" />,
                  label: "Open Opportunities",
                  value: analytics.open_opportunities,
                  link: "/opportunities?status=open",
                },
                {
                  icon: <AlertTriangle size={14} color="var(--warning)" />,
                  label: "Pending Approvals",
                  value: analytics.pending_approvals_count,
                  link: "/approvals",
                },
                {
                  icon: <CheckCircle2 size={14} color="var(--success)" />,
                  label: "Recovered",
                  value: analytics.recovered_opportunities,
                  link: "/opportunities?status=recovered",
                },
              ].map((item) => (
                <Link
                  key={item.label}
                  href={item.link}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 0",
                    borderBottom: "1px solid var(--border-subtle)",
                    textDecoration: "none",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text-secondary)", fontSize: "0.875rem" }}>
                    {item.icon}
                    {item.label}
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: "1rem", color: "var(--text-primary)" }}>
                      {item.value}
                    </span>
                    <ArrowRight size={13} color="var(--text-muted)" />
                  </div>
                </Link>
              ))}
            </div>
          </Card>
        </Section>
      </div>

      {/* Recent Opportunities */}
      <Section
        title="Recent Opportunities"
        action={
          <Link href="/opportunities" style={{ fontSize: "0.75rem", color: "var(--accent)", textDecoration: "none" }}>
            View all →
          </Link>
        }
      >
        <Card padding={0}>
          <Table>
            <thead>
              <tr>
                <Th>Payment ID</Th>
                <Th>Merchant</Th>
                <Th>Status</Th>
                <Th right>At Risk</Th>
                <Th right>Recovered</Th>
                <Th>Detected</Th>
              </tr>
            </thead>
            <tbody>
              {opps.map((o) => (
                <tr key={o.id} style={{ cursor: "pointer" }}>
                  <Td mono>
                    <Link
                      href={`/opportunities/${o.id}`}
                      style={{ color: "var(--accent)", textDecoration: "none" }}
                    >
                      {o.payment_id.slice(0, 18)}…
                    </Link>
                  </Td>
                  <Td>{o.merchant_id.slice(0, 16)}</Td>
                  <Td>
                    <Badge variant={statusVariant(o.status)}>{o.status}</Badge>
                  </Td>
                  <Td right>₹{(o.amount_at_risk / 100).toFixed(2)}</Td>
                  <Td right>
                    {o.recovered_amount != null
                      ? `₹${(o.recovered_amount / 100).toFixed(2)}`
                      : "—"}
                  </Td>
                  <Td>{relativeTime(o.detected_at)}</Td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      </Section>
    </div>
  );
}
