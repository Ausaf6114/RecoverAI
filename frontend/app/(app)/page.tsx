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

const ACTION_COLORS: Record<string, string> = {
  payment_link: "#e11d48",
  delayed_retry: "#2563eb",
  reminder: "#d97706",
  no_action: "#9ca3af",
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
      <PageHeader
        title="Overview"
        subtitle="Live revenue recovery performance"
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
          marginBottom: 28,
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

      {/* AI Uplift Banner */}
      <Card padding="16px 20px" style={{ marginBottom: 28, borderLeft: "3px solid var(--accent)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <TrendingUp size={18} color="var(--accent)" />
            <div>
              <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>
                RecoverAI Uplift vs. Baseline
              </div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2 }}>
                Additional {formatINR(bb.incremental_recovered_gmv_inr)} recovered beyond the 35% fixed-policy baseline
              </div>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "1.25rem", fontWeight: 600, color: "var(--accent)" }}>
              +{bb.uplift_percentage.toFixed(1)}%
            </div>
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>uplift</div>
          </div>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 28 }}>
        {/* Action Breakdown */}
        <Section title="Action Breakdown">
          <Card>
            {actionBreakdownData.length === 0 ? (
              <div style={{ padding: 24, textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
                No actions yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={actionBreakdownData} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
                  <XAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fill: "#6b7280" }}
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
                    contentStyle={{
                      border: "1px solid var(--border)",
                      borderRadius: 6,
                      fontSize: 12,
                      boxShadow: "var(--shadow)",
                    }}
                    cursor={{ fill: "var(--background)" }}
                  />
                  <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                    {actionBreakdownData.map((entry) => (
                      <Cell
                        key={entry.key}
                        fill={ACTION_COLORS[entry.key] ?? "#9ca3af"}
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
                  icon: <Clock size={14} color="#2563eb" />,
                  label: "Open Opportunities",
                  value: analytics.open_opportunities,
                  link: "/opportunities?status=open",
                },
                {
                  icon: <AlertTriangle size={14} color="#d97706" />,
                  label: "Pending Approvals",
                  value: analytics.pending_approvals_count,
                  link: "/approvals",
                },
                {
                  icon: <CheckCircle2 size={14} color="#059669" />,
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
