import json

from agentx.layers.ingest.idp_schema import (
    compute_risk_score,
    extract_extraction_result,
    normalize_idp_response,
    normalize_source_label,
    normalize_source_type,
    format_amount_display,
    format_source_label,
    normalize_field_confidences,
    normalize_golden_schema,
    overall_confidence_from_fields,
    round_confidence,
    parse_extraction_fields,
    parse_amount_nominal,
)
from agentx.layers.ingest.parsers.pdf.idp import _map_idp_response


SAMPLE_IDP_RESPONSE = {
    "predictions": {
        "/path/to/file.pdf": {
            "doc_type": "trade",
            "extraction_result": {
                "country": {"value": "United Arab Emirates", "confidence_score": 99},
                "transaction_date": {"value": "25/01/2023", "confidence_score": 97},
                "transaction_type": {"value": "SUBSCRIPTION", "confidence_score": 99},
                "switch_transaction": {"value": "NO", "confidence_score": 95},
                "reference_no": {"value": "IA10953", "confidence_score": 97},
                "sid": {"value": None, "confidence_score": 0},
                "fundcd_type": {"value": "EQUITY FUND", "confidence_score": 99},
                "fund_code": {"value": "AL MAL UAE EQUITY FUND", "confidence_score": 99},
                "fund_currency": {"value": "AED", "confidence_score": 99},
                "amount_nominal": {"value": "AED 5,000,000.00", "confidence_score": 98},
                "amount_unit": {"value": None, "confidence_score": 0},
                "amount_all_units": {"value": "NOT APPLICABLE", "confidence_score": 90},
                "sa_reference_no": {"value": "AE820440000002209913301", "confidence_score": 97},
                "investor_account_name": {
                    "value": "AL MAL CAPITAL (P.S.C) - TREASURY",
                    "confidence_score": 96,
                },
                "document_confidence_score": 85,
            },
        }
    },
    "model": "idp_inference_idp_poc_endpoint_v1",
}


def test_extract_extraction_result_from_predictions():
    extraction = extract_extraction_result(SAMPLE_IDP_RESPONSE)
    assert extraction["country"]["value"] == "United Arab Emirates"
    assert extraction["document_confidence_score"] == 85


def test_extract_extraction_result_from_data_wrapper():
    wrapped = {"data": SAMPLE_IDP_RESPONSE}
    extraction = extract_extraction_result(wrapped)
    assert extraction["investor_account_name"]["value"] == "AL MAL CAPITAL (P.S.C) - TREASURY"
    assert extraction["investor_account_name"]["confidence_score"] == 96


def test_normalize_idp_response_sse_prefix():
    payload = json.dumps(SAMPLE_IDP_RESPONSE)
    normalized = normalize_idp_response(f"data: {payload}")
    assert normalized["predictions"]


def test_map_idp_response_with_data_wrapper():
    intake = _map_idp_response({"data": SAMPLE_IDP_RESPONSE})
    assert intake.party["name"] == "AL MAL CAPITAL (P.S.C) - TREASURY"
    assert intake.field_confidences["investor_account_name"] == 96
    assert intake.field_confidences["country"] == 99


def test_parse_extraction_fields():
    extraction = extract_extraction_result(SAMPLE_IDP_RESPONSE)
    values, confidences = parse_extraction_fields(extraction)
    assert values["transaction_type"] == "SUBSCRIPTION"
    assert confidences["country"] == 99
    assert confidences["sid"] == 0
    assert confidences["document_confidence_score"] == 85


def test_map_idp_response_preserves_raw_output():
    intake = _map_idp_response(SAMPLE_IDP_RESPONSE)
    assert intake.idp_raw == SAMPLE_IDP_RESPONSE
    assert intake.extraction_result["reference_no"]["value"] == "IA10953"
    assert intake.field_confidences["fund_code"] == 99
    assert intake.transaction["amount_nominal"] == "AED 5,000,000.00"
    assert intake.party["name"] == "AL MAL CAPITAL (P.S.C) - TREASURY"


def test_overall_confidence_excludes_document_score():
    extraction = extract_extraction_result(SAMPLE_IDP_RESPONSE)
    _, confidences = parse_extraction_fields(extraction)
    overall = overall_confidence_from_fields(confidences)
    assert 80 < overall < 99
    assert overall == round_confidence(overall)


def test_round_confidence_to_one_decimal():
    assert round_confidence(97.456) == 97.5
    assert round_confidence(98.04) == 98.0


def test_parse_amount_nominal():
    assert parse_amount_nominal("AED 5,000,000.00") == 5000000.0


def test_normalize_golden_schema_from_legacy_keys():
    schema = normalize_golden_schema({
        "intent": "SUBSCRIPTION",
        "party": "Priya Sharma",
        "currency": "INR",
        "amount": 250000,
        "quantity": 100,
        "isin": "INF123",
        "accountId": "INV-1",
        "settlementDate": "2026-07-18",
    })
    assert schema["transaction_type"] == "SUBSCRIPTION"
    assert schema["investor_account_name"] == "Priya Sharma"
    assert schema["fund_currency"] == "INR"
    assert schema["amount_nominal"] == 250000
    assert schema["fund_code"] == "INF123"
    assert set(schema.keys()) == set([
        "country", "transaction_date", "transaction_type", "switch_transaction",
        "reference_no", "sid", "fundcd_type", "fund_code", "fund_currency",
        "amount_nominal", "amount_unit", "amount_all_units", "sa_reference_no",
        "investor_account_name",
    ])


def test_normalize_field_confidences_from_legacy_keys():
    confidences = normalize_field_confidences({
        "ISIN": 99,
        "Investor": 97,
        "Amount": 100,
        "Currency": 99,
    })
    assert confidences["fund_code"] == 99
    assert confidences["investor_account_name"] == 97
    assert confidences["amount_nominal"] == 100
    assert len(confidences) == 14


def test_compute_risk_score_missing_investor_and_amount():
    values = {field: "value" for field in (
        "country", "transaction_date", "transaction_type", "switch_transaction",
        "reference_no", "sid", "fundcd_type", "fund_code", "fund_currency",
        "amount_unit", "amount_all_units", "sa_reference_no",
    )}
    values["investor_account_name"] = None
    values["amount_nominal"] = None
    confidences = {field: 99.0 for field in values}
    score, label = compute_risk_score(values, confidences)
    assert score > 0
    assert label in ("Low", "Medium", "High", "Critical")


def test_compute_risk_score_low_confidence_increases_risk():
    values = {field: "filled" for field in (
        "country", "transaction_date", "transaction_type", "switch_transaction",
        "reference_no", "sid", "fundcd_type", "fund_code", "fund_currency",
        "amount_nominal", "amount_unit", "amount_all_units", "sa_reference_no",
        "investor_account_name",
    )}
    confidences = {field: 99.0 for field in values}
    confidences["investor_account_name"] = 50.0
    score, _ = compute_risk_score(values, confidences)
    assert score >= 5


def test_format_source_label_single_source():
    assert format_source_label("pdf", "PDF") == "PDF"
    assert format_source_label("email", "Email") == "Email"


def test_normalize_source_type():
    assert normalize_source_type("PDF") == "pdf"
    assert normalize_source_type("Email") == "email"
    assert normalize_source_type("Client Template") == "template"
    assert normalize_source_type("SWIFT") == "swift"


def test_normalize_source_label_single_values():
    assert normalize_source_label("Email") == "Email"
    assert normalize_source_label("PDF") == "PDF"
    assert normalize_source_label("Portals & Files") == "Portal"
    assert normalize_source_label("Client Templates") == "Client Template"
    assert normalize_source_label("SWIFT") == "SWIFT"
    assert normalize_source_label("pdf", "anything") == "PDF"


def test_format_amount_display_nominal():
    assert format_amount_display({"amount_nominal": "AED 5,000,000.00"}) == "AED 5,000,000.00"
