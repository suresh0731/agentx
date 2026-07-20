from pathlib import Path

import pytest
from openpyxl import load_workbook

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.route.output_writer import (
    ROUTING_OUTPUT_HEADERS,
    build_routing_row,
    destination_output_dir,
    write_routing_output,
)
from agentx.layers.route.rules_engine import evaluate_destination, normalize_country


@pytest.mark.parametrize(
    ("intent_hint", "country", "expected"),
    [
        ("subscription", "HK", "RTAS"),
        ("subscription", "hk", "RTAS"),
        ("subscription", "Hong Kong", "RTAS"),
        ("subscription", "HONG KONG", "RTAS"),
        ("redemption", "Hong Kong", "RTAS"),
        ("redemption", "hk", "RTAS"),
        ("subscription", "India", "ViTAL"),
        ("subscription", "Singapore", "ViTAL"),
        ("redemption", "Malaysia", "ViTAL"),
        ("switch", "Hong Kong", "RFAS"),
        ("transfer", "HK", "RFAS"),
        ("switch", "India", "RFAS"),
    ],
)
def test_evaluate_destination_hk_rules(intent_hint, country, expected):
    assert evaluate_destination(intent_hint, country) == expected


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("HK", "hk"),
        ("Hong Kong", "hong kong"),
        ("hongkong", "hk"),
        ("H.K.", "hk"),
        ("  India  ", "india"),
        (None, ""),
    ],
)
def test_normalize_country(raw, normalized):
    assert normalize_country(raw) == normalized


def test_write_routing_output_creates_destination_folder_and_maps_idp_fields(tmp_path):
    state = InstructionState(
        instruction_id="INS-TEST-001",
        status="Routed",
        golden_schema={
            "transaction_date": "2026-07-18",
            "transaction_type": "SUBSCRIPTION",
            "switch_transaction": "NO",
            "reference_no": "REF-001",
            "sid": "SID-99",
            "fundcd_type": "EQUITY",
            "fund_code": "INF109K01VQ1",
            "fund_currency": "HKD",
            "amount_nominal": "100000",
            "amount_unit": "1200",
            "amount_all_units": "NO",
            "sa_reference_no": "INV-001",
            "investor_account_name": "Test Investor",
            "country": "Hong Kong",
        },
        journey=JourneyState(completed_through=5, active_step=6),
    )

    output_path = write_routing_output(state, "RTAS", base_dir=tmp_path)
    assert output_path.exists()
    assert output_path.parent == destination_output_dir("RTAS", tmp_path)

    workbook = load_workbook(output_path)
    sheet = workbook.active
    headers = [cell.value for cell in sheet[1]]
    values = [cell.value for cell in sheet[2]]

    assert headers == list(ROUTING_OUTPUT_HEADERS)
    assert values[headers.index("Transaction Date")] == "2026-07-18"
    assert values[headers.index("Transaction Type")] == "SUBSCRIPTION"
    assert values[headers.index("Fund Code")] == "INF109K01VQ1"
    assert values[headers.index("Investor Fund Unit A/C Name")] == "Test Investor"
    assert values[headers.index("Upload Reference No.")] == "INS-TEST-001"
    assert values[headers.index("Status")] == "Routed"


def test_build_routing_row_uses_extraction_result_when_golden_schema_empty():
    state = InstructionState(
        instruction_id="INS-TEST-002",
        intake_json={
            "extraction_result": {
                "transaction_type": {"value": "REDEMPTION", "confidence_score": 98},
                "fund_code": {"value": "SG9999012345", "confidence_score": 97},
            }
        },
    )
    row = build_routing_row(state)
    header_index = {header: idx for idx, header in enumerate(ROUTING_OUTPUT_HEADERS)}
    assert row[header_index["Transaction Type"]] == "REDEMPTION"
    assert row[header_index["Fund Code"]] == "SG9999012345"
