"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, OpportunitySummary } from "@/lib/api";
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

const STATUS_FILTERS = ["all", "open", "pending", "completed", "recovered"];

function OpportunitiesContent() {
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get("status") ?? "all";

  const [opps, setOpps] = useState<OpportunitySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState(initialStatus);
  const [offset, setOffset] = useState(0);
  const PAGE_SIZE = 50;

  const load = (s: string, off: number) => {
    setLoading(true);
    api
      .listOpportunities({ status: s === "all" ? undefined : s, limit: PAGE_SIZE, offset: off })
      .then((r) => { setOpps(r); setError(null); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(status, offset); }, [status, offset]);

  const handleStatus = (s: string) => {
    setStatus(s);
    setOffset(0);
  };

  return (
    <div>
      <PageHeader
        title="Recovery Opportunities"
        subtitle="Failed payments detected and queued for recovery"
      />

      {/* Status filter tabs */}
      <div
        style={{
          display: "flex",
          gap: 4,
          marginBottom: 20,
          background: "var(--border-subtle)",
          borderRadius: 8,
          padding: 4,
          width: "fit-content",
        }}
      >
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            onClick={() => handleStatus(s)}
            style={{
              padding: "5px 16px",
              borderRadius: 6,
              fontSize: "0.8125rem",
              fontWeight: status === s ? 600 : 400,
              border: "none",
              background: status === s ? "#fff" : "transparent",
              color: status === s ? "var(--accent)" : "var(--text-muted)",
              cursor: "pointer",
              boxShadow: status === s ? "0 1px 3px rgba(25,40,57,0.08)" : "none",
              transition: "all 0.15s ease",
              letterSpacing: status === s ? "-0.01em" : "normal",
            }}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      <Section>
        <Card padding={0}>
          {loading ? (
            <Loading />
          ) : error ? (
            <ErrorState message={error} />
          ) : opps.length === 0 ? (
            <EmptyState message={`No ${status === "all" ? "" : status} opportunities found.`} />
          ) : (
            <>
              <Table>
                <thead>
                  <tr>
                    <Th>Payment ID</Th>
                    <Th>Merchant</Th>
                    <Th>Status</Th>
                    <Th>Split</Th>
                    <Th right>At Risk (INR)</Th>
                    <Th right>Recovered (INR)</Th>
                    <Th>Detected</Th>
                    <Th></Th>
                  </tr>
                </thead>
                <tbody>
                  {opps.map((o) => (
                    <tr key={o.id}>
                      <Td mono>
                        <Link
                          href={`/opportunities/${o.id}`}
                          style={{ color: "var(--accent)", textDecoration: "none" }}
                        >
                          {o.payment_id.slice(0, 20)}
                        </Link>
                      </Td>
                      <Td>{o.merchant_id.slice(0, 18)}</Td>
                      <Td>
                        <Badge variant={statusVariant(o.status)}>{o.status}</Badge>
                      </Td>
                      <Td>
                        <Badge variant={o.dataset_split === "test" ? "blue" : "gray"}>
                          {o.dataset_split}
                        </Badge>
                      </Td>
                      <Td right>₹{(o.amount_at_risk / 100).toFixed(2)}</Td>
                      <Td right>
                        {o.recovered_amount != null
                          ? `₹${(o.recovered_amount / 100).toFixed(2)}`
                          : "—"}
                      </Td>
                      <Td>{relativeTime(o.detected_at)}</Td>
                      <Td>
                        <Link href={`/opportunities/${o.id}`}>
                          <Button variant="ghost" size="sm">Detail →</Button>
                        </Link>
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
              {/* Pagination */}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, padding: "12px 16px", borderTop: "1px solid var(--border-subtle)" }}>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                >
                  ← Prev
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={opps.length < PAGE_SIZE}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Next →
                </Button>
              </div>
            </>
          )}
        </Card>
      </Section>
    </div>
  );
}

export default function OpportunitiesPage() {
  return (
    <Suspense fallback={<Loading />}>
      <OpportunitiesContent />
    </Suspense>
  );
}
