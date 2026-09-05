"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts";
import { api, AnalyticsResponse } from "@/lib/api";
import { formatINR, pct, actionLabel } from "@/lib/utils";
import {
  PageHeader,
  Section,
  Card,
  StatCard,
  Loading,
  ErrorState,
  KV,
  Divider,
} from "@/components/ui";

const ACTION_COLORS: Record<string, string> = {
  payment_link: "#e11d48",
  delayed_retry: "#2563eb",
  reminder: "#d97706",
  no_action: "#9ca3af",
};

const BASELINE_COLOR = "#d1d5db";
const RECOVERAI_COLOR = "#e11d48";

export default function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getAnalytics()
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Loading label="Loading analytics…" />;
  if (error) return <ErrorState message={error} />;
  if (!data) return null;

  const bb = data.baseline_benchmark;

  // Comparison bar data
  const comparisonData = [
    {
      label: "Recovery Rate",
      baseline: +(bb.baseline_recovery_rate * 100).toFixed(1),
      recoverai: +(data.recovery_rate * 100).toFixed(1),
    },
    {
      label: "Recovered GMV",
      baseline: +(bb.baseline_recovered_gmv_inr / 1000).toFixed(1),
      recoverai: +(data.total_recovered_gmv_inr / 1000).toFixed(1),
    },
  ];

  // Action pie data
  const pieData = Object.entries(data.action_breakdown)
    .map(([k, v]) => ({ name: actionLabel(k), value: v, key: k }))
    .filter((d) => d.value > 0);

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="RecoverAI vs. Baseline — performance deep dive"
      />

      {/* Top KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginBottom: 28 }}>
        <StatCard
          label="Total Opportunities"
          value={data.total_opportunities.toLocaleString()}
          sub={`${data.open_opportunities} open, ${data.recovered_opportunities} recovered`}
        />
        <StatCard
          label="Net Revenue Recovered"
          value={formatINR(data.net_revenue_inr)}
          sub={`Gross ${formatINR(data.total_recovered_gmv_inr)} − cost ${formatINR(data.total_action_cost_inr)}`}
          accent
        />
        <StatCard
          label="AI Uplift vs Baseline"
          value={`+${bb.uplift_percentage.toFixed(1)}%`}
          sub={`+${formatINR(bb.incremental_recovered_gmv_inr)} incremental`}
          accent
        />
      </div>

      {/* Baseline vs RecoverAI */}
      <Section title="Baseline vs. RecoverAI">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
          <Card>
            <h3 style={{ marginBottom: 16 }}>Recovery Rate Comparison</h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={[comparisonData[0]]} margin={{ top: 0, right: 8, bottom: 0, left: -16 }}>
                <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                <Tooltip
                  formatter={(v: any) => [`${v}%`]}
                  contentStyle={{ border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }}
                />
                <Bar dataKey="baseline" name="Baseline" fill={BASELINE_COLOR} radius={[3, 3, 0, 0]} />
                <Bar dataKey="recoverai" name="RecoverAI" fill={RECOVERAI_COLOR} radius={[3, 3, 0, 0]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <h3 style={{ marginBottom: 16 }}>Recovered GMV (₹K)</h3>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={[comparisonData[1]]} margin={{ top: 0, right: 8, bottom: 0, left: -16 }}>
                <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} unit="K" />
                <Tooltip
                  formatter={(v: any) => [`₹${v}K`]}
                  contentStyle={{ border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }}
                />
                <Bar dataKey="baseline" name="Baseline" fill={BASELINE_COLOR} radius={[3, 3, 0, 0]} />
                <Bar dataKey="recoverai" name="RecoverAI" fill={RECOVERAI_COLOR} radius={[3, 3, 0, 0]} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </Section>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        {/* Action Distribution */}
        <Section title="Action Distribution">
          <Card>
            {pieData.length === 0 ? (
              <div style={{ padding: 32, textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
                No actions recorded yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    dataKey="value"
                    paddingAngle={2}
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.key} fill={ACTION_COLORS[entry.key] ?? "#9ca3af"} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ border: "1px solid var(--border)", borderRadius: 6, fontSize: 12 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Section>

        {/* Benchmark Table */}
        <Section title="Detailed Benchmark">
          <Card>
            <KV label="Baseline Recovery Rate" value={pct(bb.baseline_recovery_rate)} />
            <KV label="RecoverAI Recovery Rate" value={pct(data.recovery_rate)} />
            <Divider />
            <KV label="Baseline Recovered GMV" value={formatINR(bb.baseline_recovered_gmv_inr)} />
            <KV label="RecoverAI Recovered GMV" value={formatINR(data.total_recovered_gmv_inr)} />
            <KV label="Incremental GMV" value={<strong style={{ color: "var(--accent)" }}>{formatINR(bb.incremental_recovered_gmv_inr)}</strong>} />
            <KV label="Uplift %" value={<strong style={{ color: "var(--accent)" }}>+{bb.uplift_percentage.toFixed(2)}%</strong>} />
            <Divider />
            <KV label="Total Action Cost" value={formatINR(data.total_action_cost_inr)} />
            <KV label="Net Revenue" value={formatINR(data.net_revenue_inr)} />
            <KV label="Pending Approvals" value={data.pending_approvals_count} />
          </Card>
        </Section>
      </div>
    </div>
  );
}
