"""
Integration tests for RecoverAI Analytics API endpoint.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAnalyticsAPI:
    def test_get_recovery_analytics(self):
        response = client.get("/analytics/recovery")
        assert response.status_code == 200
        data = response.json()

        assert "total_opportunities" in data
        assert "open_opportunities" in data
        assert "recovered_opportunities" in data
        assert "recovery_rate" in data
        assert "total_at_risk_gmv_inr" in data
        assert "total_recovered_gmv_inr" in data
        assert "total_action_cost_inr" in data
        assert "net_revenue_inr" in data
        assert "action_breakdown" in data
        assert "pending_approvals_count" in data
        assert "baseline_benchmark" in data

        benchmark = data["baseline_benchmark"]
        assert "baseline_recovery_rate" in benchmark
        assert "baseline_recovered_gmv_inr" in benchmark
        assert "incremental_recovered_gmv_inr" in benchmark
        assert "uplift_percentage" in benchmark
