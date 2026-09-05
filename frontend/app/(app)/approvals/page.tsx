"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, OpportunitySummary, ActionResponse } from "@/lib/api";
import { relativeTime, actionLabel } from "@/lib/utils";
import {
  PageHeader,
  Section,
  Card,
  Badge,
  statusVariant,
  Button,
  Table,
  Th,
  Td,
  Loading,
  ErrorState,
  EmptyState,
} from "@/components/ui";

interface PendingItem {
  opp: OpportunitySummary;
  actionId?: string;
}

export default function ApprovalsPage() {
  const [items, setItems] = useState<PendingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actioning, setActioning] = useState<string | null>(null);

  const loadPending = () => {
    setLoading(true);
    api
      .listOpportunities({ status: "pending", limit: 100 })
      .then((opps) => setItems(opps.map((o) => ({ opp: o }))))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadPending(); }, []);

  const handleApprove = async (opp: OpportunitySummary) => {
    setActioning(opp.id);
    try {
      let actionId = opp.action_id;
      if (!actionId) {
        const detail = await api.getOpportunity(opp.id);
        actionId = detail.action_id;
      }
      if (!actionId) {
        const decide = await api.decideOpportunity(opp.id);
        actionId = decide.action_id;
      }
      if (actionId) {
        await api.approveAction(actionId);
        await api.executeAction(actionId);
      }
      setItems((prev) => prev.filter((i) => i.opp.id !== opp.id));
    } catch (e: unknown) {
      alert(`Error: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setActioning(null);
    }
  };

  return (
    <div>
      <PageHeader
        title="Action Approval Queue"
        subtitle="Recovery actions requiring merchant approval before execution"
        action={
          <Button variant="secondary" size="sm" onClick={loadPending}>
            Refresh
          </Button>
        }
      />

      <Section>
        <Card padding={0}>
          {loading ? (
            <Loading />
          ) : error ? (
            <ErrorState message={error} />
          ) : items.length === 0 ? (
            <EmptyState message="No actions pending approval. All decisions are auto-approved or executed." />
          ) : (
            <Table>
              <thead>
                <tr>
                  <Th>Opportunity ID</Th>
                  <Th>Payment ID</Th>
                  <Th>Merchant</Th>
                  <Th>Status</Th>
                  <Th right>At Risk (INR)</Th>
                  <Th>Detected</Th>
                  <Th></Th>
                </tr>
              </thead>
              <tbody>
                {items.map(({ opp }) => (
                  <tr key={opp.id}>
                    <Td mono>
                      <Link
                        href={`/opportunities/${opp.id}`}
                        style={{ color: "var(--accent)", textDecoration: "none" }}
                      >
                        {opp.id.slice(0, 14)}…
                      </Link>
                    </Td>
                    <Td mono>{opp.payment_id.slice(0, 18)}</Td>
                    <Td>{opp.merchant_id.slice(0, 18)}</Td>
                    <Td>
                      <Badge variant={statusVariant(opp.status)}>{opp.status}</Badge>
                    </Td>
                    <Td right>₹{(opp.amount_at_risk / 100).toFixed(2)}</Td>
                    <Td>{relativeTime(opp.detected_at)}</Td>
                    <Td>
                      <div style={{ display: "flex", gap: 6 }}>
                        <Link href={`/opportunities/${opp.id}`}>
                          <Button variant="ghost" size="sm">View</Button>
                        </Link>
                        <Button
                          variant="primary"
                          size="sm"
                          loading={actioning === opp.id}
                          onClick={() => handleApprove(opp)}
                        >
                          Approve &amp; Run
                        </Button>
                      </div>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
        </Card>
      </Section>

      {/* Info card */}
      <Card
        style={{
          marginTop: 20,
          borderLeft: "3px solid var(--accent)",
          background: "var(--accent-light)",
          border: "1px solid var(--accent-border)",
          borderLeftWidth: 3,
        }}
        padding="14px 18px"
      >
        <div style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.65 }}>
          <strong style={{ color: "var(--accent)" }}>ⓘ  About approvals: </strong>
          RecoverAI gates high-value actions (payment links &gt; ₹1,000) for merchant review.
          Clicking <strong>"Approve &amp; Run"</strong> triggers the agent pipeline and executes
          the action in <strong>Razorpay Test Mode</strong>.
        </div>
      </Card>
    </div>
  );
}
