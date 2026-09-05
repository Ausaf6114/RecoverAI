/**
 * API client — all requests go to the FastAPI backend.
 * Base URL defaults to http://localhost:8000 in development.
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ─── Types ────────────────────────────────────────────────────────────────────

export interface AnalyticsResponse {
  total_opportunities: number;
  open_opportunities: number;
  recovered_opportunities: number;
  recovery_rate: number;
  total_at_risk_gmv_inr: number;
  total_recovered_gmv_inr: number;
  total_action_cost_inr: number;
  net_revenue_inr: number;
  action_breakdown: Record<string, number>;
  pending_approvals_count: number;
  baseline_benchmark: {
    baseline_recovery_rate: number;
    baseline_recovered_gmv_inr: number;
    incremental_recovered_gmv_inr: number;
    uplift_percentage: number;
  };
}

export interface OpportunitySummary {
  id: string;
  payment_id: string;
  merchant_id: string;
  status: string;
  amount_at_risk: number;
  recovered_amount: number | null;
  detected_at: string | null;
  dataset_split: string;
  action_id?: string | null;
  action_status?: string | null;
  selected_action?: string | null;
  requires_approval?: boolean;
}

export interface OpportunityDetail extends OpportunitySummary {
  payment_method: string | null;
  error_reason: string | null;
  error_source: string | null;
  attempt_number: number;
  selected_action: string | null;
  requires_approval: boolean;
  diagnosis_summary: string | null;
  external_reference_id?: string | null;
  external_reference_url?: string | null;
}

export interface DecideResponse {
  opportunity_id: string;
  payment_id: string;
  selected_action: string;
  confidence: number;
  expected_recovery_value: number;
  requires_approval: boolean;
  execution_status: string | null;
  action_id?: string | null;
  external_reference_id?: string | null;
  external_reference_url?: string | null;
  diagnosis_category: string | null;
  diagnosis_hypothesis: string | null;
  rationale: string;
}

export interface ActionResponse {
  id: string;
  opportunity_id: string;
  strategy: string;
  status: string;
  external_reference_id: string | null;
  external_reference_url: string | null;
  created_at: string;
  executed_at: string | null;
}

// ─── API Functions ────────────────────────────────────────────────────────────

export const api = {
  getAnalytics: () =>
    apiFetch<AnalyticsResponse>("/analytics/recovery"),

  listOpportunities: (params?: { status?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString() ? `?${qs}` : "";
    return apiFetch<OpportunitySummary[]>(`/recovery/opportunities${query}`);
  },

  getOpportunity: (id: string) =>
    apiFetch<OpportunityDetail>(`/recovery/opportunities/${id}`),

  decideOpportunity: (id: string) =>
    apiFetch<DecideResponse>(`/recovery/opportunities/${id}/decide`, { method: "POST" }),

  listActions: (params?: { status?: string; opportunity_id?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.opportunity_id) qs.set("opportunity_id", params.opportunity_id);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString() ? `?${qs}` : "";
    return apiFetch<ActionResponse[]>(`/recovery/actions${query}`);
  },

  getAction: (id: string) =>
    apiFetch<ActionResponse>(`/recovery/actions/${id}`),

  approveAction: (id: string, approvedBy = "merchant_admin") =>
    apiFetch<ActionResponse>(`/recovery/actions/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }),

  executeAction: (id: string) =>
    apiFetch<ActionResponse>(`/recovery/actions/${id}/execute`, { method: "POST" }),
};
