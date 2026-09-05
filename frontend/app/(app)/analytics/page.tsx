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
  CartesianGrid,
  LabelList,
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
  payment_link: "#3395FF",   // Razorpay blue
  delayed_retry: "#00C48C",  // Razorpay green
  reminder: "#f59e0b",       // Amber
  no_action: "#94a3b8",      // Slate
};

const BASELINE_COLOR = "#cbd5e1";      // Neutral slate
const RECOVERAI_COLOR = "#3395FF";    // Razorpay blue

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
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, marginBottom: 32 }}>
        <StatCard
          label="Total Opportunities"
          value={data.total_opportunities.toLocaleString()}
          sub={`${data.open_opportunities} open · ${data.recovered_opportunities} recovered`}
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
          sub={`+${formatINR(bb.incremental_recovered_gmv_inr)} incremental GMV`}
          accent
        />
      </div>

      {/* Baseline vs RecoverAI */}
      <Section title="Baseline vs. RecoverAI">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          <Card>
            <h3 style={{ marginBottom: 4, fontSize: "0.875rem", fontWeight: 600, color: "var(--navy)" }}>
              Recovery Rate Comparison
            </h3>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 16 }}>
              Baseline algorithm vs. RecoverAI model
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={[comparisonData[0]]}
                margin={{ top: 24, right: 12, bottom: 4, left: -12 }}
                barSize={44}
                barCategoryGap="40%"
              >
                <CartesianGrid vertical={false} stroke="#f1f5f9" strokeDasharray="0" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} unit="%" />
                <Tooltip
                  formatter={(v: any, name: any) => [`${v}%`, name === "recoverai" ? "RecoverAI" : "Baseline"]}
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                    boxShadow: "0 4px 12px rgba(25,40,57,0.08)",
                    padding: "8px 12px",
                  }}
                  cursor={{ fill: "rgba(51,149,255,0.05)" }}
                />
                <Bar dataKey="baseline" name="Baseline" fill={BASELINE_COLOR} radius={[5, 5, 0, 0]}>
                  <LabelList dataKey="baseline" position="top" formatter={(v: any) => `${v}%`} style={{ fontSize: 11, fontWeight: 600, fill: "#64748b" }} />
                </Bar>
                <Bar dataKey="recoverai" name="RecoverAI" fill={RECOVERAI_COLOR} radius={[5, 5, 0, 0]}>
                  <LabelList dataKey="recoverai" position="top" formatter={(v: any) => `${v}%`} style={{ fontSize: 11, fontWeight: 600, fill: RECOVERAI_COLOR }} />
                </Bar>
                <Legend
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                  formatter={(value) => <span style={{ color: "var(--text-secondary)" }}>{value}</span>}
                />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <h3 style={{ marginBottom: 4, fontSize: "0.875rem", fontWeight: 600, color: "var(--navy)" }}>
              Recovered GMV
            </h3>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 16 }}>
              In ₹ thousands (K)
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart
                data={[comparisonData[1]]}
                margin={{ top: 24, right: 12, bottom: 4, left: -12 }}
                barSize={44}
                barCategoryGap="40%"
              >
                <CartesianGrid vertical={false} stroke="#f1f5f9" strokeDasharray="0" />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: "#6b7280" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} unit="K" />
                <Tooltip
                  formatter={(v: any, name: any) => [`₹${v}K`, name === "recoverai" ? "RecoverAI" : "Baseline"]}
                  contentStyle={{
                    background: "#fff",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    fontSize: 12,
                    boxShadow: "0 4px 12px rgba(25,40,57,0.08)",
                    padding: "8px 12px",
                  }}
                  cursor={{ fill: "rgba(51,149,255,0.05)" }}
                />
                <Bar dataKey="baseline" name="Baseline" fill={BASELINE_COLOR} radius={[5, 5, 0, 0]}>
                  <LabelList dataKey="baseline" position="top" formatter={(v: any) => `₹${v}K`} style={{ fontSize: 11, fontWeight: 600, fill: "#64748b" }} />
                </Bar>
                <Bar dataKey="recoverai" name="RecoverAI" fill={RECOVERAI_COLOR} radius={[5, 5, 0, 0]}>
                  <LabelList dataKey="recoverai" position="top" formatter={(v: any) => `₹${v}K`} style={{ fontSize: 11, fontWeight: 600, fill: RECOVERAI_COLOR }} />
                </Bar>
                <Legend
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                  formatter={(value) => <span style={{ color: "var(--text-secondary)" }}>{value}</span>}
                />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      </Section>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <Section title="Action Distribution">
          <Card>
            {pieData.length === 0 ? (
              <div style={{ padding: 32, textAlign: "center", color: "var(--text-muted)", fontSize: "0.875rem" }}>
                No actions recorded yet.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={58}
                    outerRadius={90}
                    dataKey="value"
                    paddingAngle={3}
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.key} fill={ACTION_COLORS[entry.key] ?? "#94a3b8"} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#fff",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      fontSize: 12,
                      boxShadow: "0 4px 12px rgba(25,40,57,0.08)",
                      padding: "8px 12px",
                    }}
                    formatter={(value: any, name: any) => [value, name]}
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
