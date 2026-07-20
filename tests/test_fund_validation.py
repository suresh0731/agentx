import pytest

from agentx.layers.ingest.idp_schema import extract_doc_type, parse_extraction_fields
from agentx.layers.transaction_processing.agent import TransactionProcessingAgent
from agentx.layers.transaction_processing.validation import validate_fund_transaction
from tests.test_idp_schema import SAMPLE_IDP_RESPONSE


def _sample_values_and_confidences():
    extraction = SAMPLE_IDP_RESPONSE["predictions"][
        "/path/to/file.pdf"
    ]["extraction_result"]
    return parse_extraction_fields(extraction)


def test_extract_doc_type_trade():
    assert extract_doc_type(SAMPLE_IDP_RESPONSE) == "trade"


def test_validation_flags_null_and_zero_confidence_fields():
    values, confidences = _sample_values_and_confidences()
    report = validate_fund_transaction(values, confidences)

    assert "sid" in report.human_review_fields
    assert "amount_unit" not in report.human_review_fields
    assert "sid" in report.failed_fields
    assert not report.passed


def test_validation_fundcd_type_invalid():
    values, confidences = _sample_values_and_confidences()
    report = validate_fund_transaction(values, confidences)
    assert "fundcd_type" in report.failed_fields


@pytest.mark.asyncio
async def test_idp_stages_as_separate_steps():
    extraction = SAMPLE_IDP_RESPONSE["predictions"]["/path/to/file.pdf"]["extraction_result"]
    values, confidences = parse_extraction_fields(extraction)

    InstructionState = __import__(
        "agentx.domain.models", fromlist=["InstructionState"]
    ).InstructionState

    state = InstructionState(
        instruction_id="INS-TEST001",
        intake_json={
            "extraction_result": extraction,
            "field_confidences": confidences,
            "idp_raw": SAMPLE_IDP_RESPONSE,
            "transaction": {"doc_type": "trade"},
        },
    )

    agent = TransactionProcessingAgent()
    after_detect = await agent.detect(state)
    assert after_detect.journey.completed_through == 2
    assert after_detect.journey.active_step == 3

    after_validate = await agent.validate(after_detect)
    assert after_validate.journey.completed_through == 3
    assert after_validate.journey.active_step == 4

    result = await agent.repair(after_validate)
    assert any("bypass" in n.lower() for n in result.repair_notes)
    assert result.needs_human_review is True
    assert result.journey.held_step == 4


@pytest.mark.asyncio
async def test_idp_path_segregates_detect_validate_repair():
    extraction = SAMPLE_IDP_RESPONSE["predictions"]["/path/to/file.pdf"]["extraction_result"]
    values, confidences = parse_extraction_fields(extraction)

    state = __import__("agentx.domain.models", fromlist=["InstructionState"]).InstructionState(
        instruction_id="INS-TEST001",
        intake_json={
            "extraction_result": extraction,
            "field_confidences": confidences,
            "idp_raw": SAMPLE_IDP_RESPONSE,
            "transaction": {"doc_type": "trade"},
        },
    )

    agent = TransactionProcessingAgent()
    result = await agent.run(state)

    assert result.intent == "Subscription"
    assert any("Trade Fund" in d for d in result.decisions)
    assert any("Validate" in d for d in result.decisions)
    assert any("bypass" in n.lower() for n in result.repair_notes)
    assert result.needs_human_review is True
    assert result.journey.held_step == 4
    assert result.journey.completed_through == 3


@pytest.mark.asyncio
async def test_idp_path_passes_when_all_fields_valid():
    extraction = {
        "country": {"value": "UAE", "confidence_score": 99},
        "transaction_date": {"value": "20230125", "confidence_score": 99},
        "transaction_type": {"value": "SUBSCRIPTION", "confidence_score": 99},
        "switch_transaction": {"value": "NO", "confidence_score": 99},
        "reference_no": {"value": "IA10953", "confidence_score": 99},
        "sid": {"value": "102602", "confidence_score": 99},
        "fundcd_type": {"value": "I", "confidence_score": 99},
        "fund_code": {"value": "FD1111111118", "confidence_score": 99},
        "fund_currency": {"value": "AED", "confidence_score": 99},
        "amount_nominal": {"value": "5000000", "confidence_score": 99},
        "amount_unit": {"value": None, "confidence_score": 0},
        "amount_all_units": {"value": "NOT APPLICABLE", "confidence_score": 90},
        "sa_reference_no": {"value": "AE820440000002209913301", "confidence_score": 99},
        "investor_account_name": {"value": "TEST INVESTOR", "confidence_score": 99},
    }
    values, confidences = parse_extraction_fields(extraction)
    report = validate_fund_transaction(values, confidences)
    assert report.passed

    state = __import__("agentx.domain.models", fromlist=["InstructionState"]).InstructionState(
        instruction_id="INS-TEST002",
        intake_json={
            "extraction_result": extraction,
            "field_confidences": confidences,
            "idp_raw": {"predictions": {"/f.pdf": {"doc_type": "trade", "extraction_result": extraction}}},
            "transaction": {"doc_type": "trade"},
        },
    )
    result = await TransactionProcessingAgent().run(state)
    assert result.needs_human_review is False
    assert result.journey.completed_through == 4
    assert result.journey.active_step == 5
