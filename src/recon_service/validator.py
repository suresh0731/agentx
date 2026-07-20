"""Mock reconciliation validator — compares ingested vs external system records."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from recon_service.models import (
    FieldValidation,
    ReconcileValidateRequest,
    ReconcileValidateResponse,
    ValidationCounts,
)

# Fields compared between ingested (IDP) record and external system load.
VALIDATION_FIELDS: tuple[tuple[str, str], ...] = (
    ("Transaction Date", "transaction_date"),
    ("Transaction Type", "transaction_type"),
    ("Switch Transaction", "switch_transaction"),
    ("Reference No.", "reference_no"),
    ("Investor Fund Unit A/C No.", "sa_reference_no"),
    ("Investor Fund Unit A/C Name", "investor_account_name"),
    ("SID", "sid"),
    ("FundCd Type", "fundcd_type"),
    ("Fund Code", "fund_code"),
    ("Fund CCY", "fund_currency"),
    ("Amount (Nominal)", "amount_nominal"),
    ("Amount (Unit)", "amount_unit"),
    ("Amount (All Units)", "amount_all_units"),
    ("Country", "country"),
)


def _field_value(record: dict[str, Any], key: str) -> str:
    raw = record.get(key)
    if isinstance(raw, dict) and "value" in raw:
        raw = raw.get("value")
    if raw is None:
        return ""
    return str(raw).strip()


def _mock_external_record(ingested: dict[str, Any]) -> dict[str, str]:
    """Enterprise stand-in: external system returns the same loaded values."""
    return {schema_key: _field_value(ingested, schema_key) for _, schema_key in VALIDATION_FIELDS}


def _format_agent_output(
    request: ReconcileValidateRequest,
    validations: list[FieldValidation],
    external_reference: str,
    validated_at: str,
) -> str:
    lines = [
        "Reconciliation Agent Report",
        "===========================",
        f"Instruction ID : {request.instruction_id}",
        f"Destination    : {request.destination}",
        f"Route Ref      : {request.route_reference or '—'}",
        f"External Ref   : {external_reference}",
        f"Validated At   : {validated_at}",
        f"Result         : MATCHED",
        "",
        "Field Validation",
        "----------------",
    ]

    for item in validations:
        marker = "✓" if item.status == "matched" else "✗"
        lines.append(
            f"{marker} {item.field:<28} "
            f"ingested={item.ingested_value or '—':<18} | external={item.external_value or '—'}"
        )

    matched = sum(1 for item in validations if item.status == "matched")
    lines.extend(
        [
            "",
            "Summary",
            "-------",
            (
                f"All {matched}/{len(validations)} compared fields match between the ingested "
                f"record and the {request.destination} load. Reconciliation complete."
            ),
        ]
    )
    return "\n".join(lines)


def validate_reconciliation(request: ReconcileValidateRequest) -> ReconcileValidateResponse:
    """Validate ingested data against the mock external system record (always matched)."""
    ingested = request.ingested_record or {}
    external = _mock_external_record(ingested)
    validations: list[FieldValidation] = []

    for label, schema_key in VALIDATION_FIELDS:
        ingested_value = _field_value(ingested, schema_key)
        external_value = external.get(schema_key, "")
        if not ingested_value and not external_value:
            continue
        validations.append(
            FieldValidation(
                field=label,
                ingested_value=ingested_value,
                external_value=external_value or ingested_value,
                status="matched",
            )
        )

    if not validations:
        validations.append(
            FieldValidation(
                field="Instruction ID",
                ingested_value=request.instruction_id,
                external_value=request.instruction_id,
                status="matched",
            )
        )

    validated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    external_reference = f"SET-{request.instruction_id[-4:]}"
    counts = ValidationCounts(
        total=len(validations),
        matched=len(validations),
        mismatched=0,
    )
    summary = (
        f"Reconciliation matched for {request.instruction_id} in {request.destination}. "
        f"{counts.matched}/{counts.total} fields validated."
    )
    agent_output = _format_agent_output(request, validations, external_reference, validated_at)

    return ReconcileValidateResponse(
        status="matched",
        matched=True,
        summary=summary,
        agent_output=agent_output,
        external_reference=external_reference,
        validated_at=validated_at,
        destination=request.destination,
        field_validations=validations,
        counts=counts,
    )
