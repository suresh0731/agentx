from fastapi.testclient import TestClient

from recon_service.main import app
from recon_service.models import ReconcileValidateRequest
from recon_service.validator import validate_reconciliation


def test_validate_reconciliation_always_matches_with_agent_output():
    request = ReconcileValidateRequest(
        instruction_id="INS-7844100",
        destination="RTAS",
        route_reference="RTAS-4100",
        ingested_record={
            "transaction_date": "2026-07-18",
            "transaction_type": "SUBSCRIPTION",
            "fund_code": "INF109K01VQ1",
            "amount_nominal": "100000",
            "investor_account_name": "Test Investor",
            "country": "Hong Kong",
        },
    )
    result = validate_reconciliation(request)

    assert result.matched is True
    assert result.status == "matched"
    assert result.counts.mismatched == 0
    assert result.counts.matched == result.counts.total
    assert "Reconciliation Agent Report" in result.agent_output
    assert "Transaction Date" in result.agent_output
    assert "MATCHED" in result.agent_output
    assert result.external_reference == "SET-4100"


def test_reconcile_validate_api_endpoint():
    client = TestClient(app)
    response = client.post(
        "/api/v1/reconcile/validate",
        json={
            "instruction_id": "INS-TEST-001",
            "destination": "ViTAL",
            "ingested_record": {
                "transaction_type": "REDEMPTION",
                "fund_code": "SG9999012345",
            },
            "route_reference": "ViTAL-0001",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["status"] == "matched"
    assert "agent_output" in body
    assert body["destination"] == "ViTAL"
