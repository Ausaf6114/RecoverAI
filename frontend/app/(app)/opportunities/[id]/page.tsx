"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Clock,
  Zap,
  FileText,
} from "lucide-react";
import { api, OpportunityDetail, DecideResponse } from "@/lib/api";
import { relativeTime, actionLabel, pct } from "@/lib/utils";
import {
  Card,
  Badge,
  statusVariant,
  Button,
  Loading,
  ErrorState,
  KV,
  Divider,
  Section,
} from "@/components/ui";

interface TimelineEvent {
  icon: React.ReactNode;
  label: string;
  detail?: string;
  time?: string;
  color?: string;
}

function Timeline({ events }: { events: TimelineEvent[] }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      {events.map((ev, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            gap: 14,
            paddingBottom: 20,
            position: "relative",
          }}
        >
          {/* Line */}
          {i < events.length - 1 && (
            <div
              style={{
                position: "absolute",
                left: 13,
                top: 28,
                bottom: 0,
                width: 1,
                background: "var(--border)",
              }}
            />
          )}
          {/* Icon */}
          <div
            style={{
              width: 28,
              height: 28,
              borderRadius: "50%",
              background: ev.color ? `${ev.color}18` : "var(--background)",
              border: `1px solid ${ev.color ?? "var(--border)"}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {ev.icon}
          </div>
          {/* Content */}
          <div style={{ flex: 1, paddingTop: 4 }}>
            <div style={{ fontWeight: 500, fontSize: "0.8125rem", color: "var(--text-primary)" }}>
              {ev.label}
            </div>
            {ev.detail && (
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: 2, lineHeight: 1.5 }}>
                {ev.detail}
              </div>
            )}
          </div>
          {ev.time && (
            <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", paddingTop: 5 }}>
              {ev.time}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

export default function OpportunityDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [opp, setOpp] = useState<OpportunityDetail | null>(null);
  const [decision, setDecision] = useState<DecideResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decideError, setDecideError] = useState<string | null>(null);

  useEffect(() => {
    api.getOpportunity(id)
      .then(setOpp)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const handleDecide = () => {
    setDeciding(true);
    setDecideError(null);
    api.decideOpportunity(id)
      .then((d) => {
        setDecision(d);
        setOpp((prev) => prev ? {
          ...prev,
          selected_action: d.selected_action,
          requires_approval: d.requires_approval,
          diagnosis_summary: d.diagnosis_hypothesis,
          action_id: d.action_id || prev.action_id,
          action_status: d.requires_approval ? "pending" : (d.execution_status || "completed"),
          external_reference_id: d.external_reference_id,
          external_reference_url: d.external_reference_url,
        } : prev);
      })
      .catch((e) => setDecideError(e.message))
      .finally(() => setDeciding(false));
  };

  const handleApproveAndExecute = () => {
    const actId = decision?.action_id || opp?.action_id;
    if (!actId) return;
    setDeciding(true);
    setDecideError(null);
    api.approveAction(actId)
      .then(() => api.executeAction(actId))
      .then((res) => {
        setOpp((prev) => prev ? {
          ...prev,
          action_status: res.status,
          external_reference_id: res.external_reference_id,
          external_reference_url: res.external_reference_url,
          status: "in_progress",
        } : prev);
        if (decision) {
          setDecision((prev) => prev ? {
            ...prev,
            requires_approval: false,
            execution_status: res.status,
            external_reference_id: res.external_reference_id,
            external_reference_url: res.external_reference_url,
          } : prev);
        }
      })
      .catch((e) => setDecideError(e.message))
      .finally(() => setDeciding(false));
  };

  if (loading) return <div style={{ padding: 32 }}><Loading /></div>;
  if (error) return <div style={{ padding: 32 }}><ErrorState message={error} /></div>;
  if (!opp) return null;

  const timelineEvents: TimelineEvent[] = [
    {
      icon: <AlertCircle size={13} color="var(--accent)" />,
      label: "Opportunity Detected",
      detail: `Payment ${opp.payment_id} failed`,
      time: relativeTime(opp.detected_at),
      color: "var(--accent)",
    },
  ];

  if (opp.diagnosis_summary) {
    timelineEvents.push({
      icon: <Cpu size={13} color="#7c3aed" />,
      label: "Gemini AI Diagnosis",
      detail: opp.diagnosis_summary,
      color: "#7c3aed",
    });
  }

  if (decision) {
    timelineEvents.push({
      icon: <Zap size={13} color="var(--accent)" />,
      label: `Action Selected: ${actionLabel(decision.selected_action)}`,
      detail: decision.rationale,
      color: "var(--accent)",
    });

    if (decision.requires_approval) {
      timelineEvents.push({
        icon: <Clock size={13} color="#f59e0b" />,
        label: "Awaiting Merchant Approval",
        color: "#f59e0b",
      });
    } else if (decision.execution_status) {
      timelineEvents.push({
        icon: <CheckCircle2 size={13} color="var(--success)" />,
        label: `Executed: ${decision.execution_status}`,
        color: "var(--success)",
      });
    }
  } else if (opp.selected_action) {
    timelineEvents.push({
      icon: <Zap size={13} color="var(--accent)" />,
      label: `Action: ${actionLabel(opp.selected_action)}`,
      color: "var(--accent)",
    });
  }

  return (
    <div>
      {/* Back */}
      <Link
        href="/opportunities"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          fontSize: "0.8125rem",
          color: "var(--text-secondary)",
          textDecoration: "none",
          marginBottom: 20,
        }}
      >
        <ArrowLeft size={13} /> Back to Opportunities
      </Link>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <h1 style={{ marginBottom: 6, fontFamily: "var(--font-serif)" }}>Opportunity Detail</h1>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <Badge variant={statusVariant(opp.status)}>{opp.status}</Badge>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
              {opp.id}
            </span>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          {((opp.requires_approval || decision?.requires_approval) && (opp.action_status === "pending" || decision?.execution_status === "pending")) && (
            <Button
              variant="primary"
              onClick={handleApproveAndExecute}
              loading={deciding}
              style={{
                background: "#f59e0b",
                border: "1px solid #d97706",
                boxShadow: "0 1px 3px rgba(245,158,11,0.28)",
              }}
            >
              <CheckCircle2 size={14} /> Approve &amp; Execute
            </Button>
          )}
          <Button
            variant={opp.selected_action || decision ? "secondary" : "primary"}
            onClick={handleDecide}
            loading={deciding}
            disabled={opp.status === "recovered"}
          >
            <Cpu size={14} /> {opp.selected_action || decision ? "Re-run AI Decision" : "Run AI Decision"}
          </Button>
        </div>
      </div>

      {decideError && (
        <div style={{ marginBottom: 20 }}>
          <ErrorState message={decideError} />
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        {/* Left: Details */}
        <div>
          <Section title="Payment Details">
            <Card>
              <KV label="Payment ID" value={<span style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{opp.payment_id}</span>} />
              <KV label="Merchant ID" value={opp.merchant_id} />
              <KV label="Method" value={opp.payment_method ?? "—"} />
              <KV label="Error Reason" value={opp.error_reason ?? "—"} />
              <KV label="Error Source" value={opp.error_source ?? "—"} />
              <KV label="Attempt #" value={opp.attempt_number} />
              <KV label="Dataset Split" value={<Badge variant={opp.dataset_split === "test" ? "blue" : "gray"}>{opp.dataset_split}</Badge>} />
              <KV label="Detected" value={relativeTime(opp.detected_at)} />
            </Card>
          </Section>

          <Section title="Financial">
            <Card>
              <KV
                label="Amount at Risk"
                value={<strong>₹{(opp.amount_at_risk / 100).toFixed(2)}</strong>}
              />
              <KV
                label="Recovered"
                value={
                  opp.recovered_amount != null
                    ? `₹${(opp.recovered_amount / 100).toFixed(2)}`
                    : "—"
                }
              />
            </Card>
          </Section>

          {decision && (
            <Section title="Decision Output">
              <Card>
                <KV label="Selected Action" value={<Badge variant="blue">{actionLabel(decision.selected_action)}</Badge>} />
                <KV label="Confidence" value={pct(decision.confidence)} />
                <KV label="Expected Recovery Value" value={`₹${decision.expected_recovery_value.toFixed(2)}`} />
                <KV label="Requires Approval" value={decision.requires_approval ? "Yes" : "No"} />
                <KV label="Execution Status" value={decision.execution_status ?? "—"} />
                {(decision.external_reference_url || opp.external_reference_url) && (
                  <KV
                    label="Payment Link"
                    value={
                      <a
                        href={decision.external_reference_url || opp.external_reference_url || "#"}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: "var(--accent)", textDecoration: "underline", fontSize: "0.75rem", wordBreak: "break-all" }}
                      >
                        {decision.external_reference_url || opp.external_reference_url}
                      </a>
                    }
                  />
                )}
                {(decision.external_reference_id || opp.external_reference_id) && (
                  <KV label="Reference ID" value={<span style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{decision.external_reference_id || opp.external_reference_id}</span>} />
                )}
                {decision.diagnosis_category && (
                  <KV label="Failure Category" value={decision.diagnosis_category} />
                )}
                {decision.rationale && (
                  <>
                    <Divider />
                    <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: 1.6 }}>
                      <FileText size={12} style={{ display: "inline", marginRight: 4, verticalAlign: "middle" }} />
                      {decision.rationale}
                    </div>
                  </>
                )}
              </Card>
            </Section>
          )}
        </div>

        {/* Right: Timeline */}
        <Section title="Agent Reasoning Timeline">
          <Card>
            <Timeline events={timelineEvents} />
            {timelineEvents.length === 1 && (
              <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", marginTop: 8 }}>
                Click "Run AI Decision" to trigger the agent pipeline.
              </div>
            )}
          </Card>
        </Section>
      </div>
    </div>
  );
}
