import re
from datetime import datetime
from typing import Any

IDP_FIELDS = (
    "country",
    "transaction_date",
    "transaction_type",
    "switch_transaction",
    "reference_no",
    "sid",
    "fundcd_type",
    "fund_code",
    "fund_currency",
    "amount_nominal",
    "amount_unit",
    "amount_all_units",
    "sa_reference_no",
    "investor_account_name",
)

INTENT_MAP = {
    "subscription": "Subscription",
    "redemption": "Redemption",
    "switch": "Switch",
    "transfer": "Transfer",
}

DEST_MAP = {
    "Subscription": "TA",
    "Redemption": "FA",
    "Switch": "TA",
    "Transfer": "IS",
}


def extract_extraction_result(response: dict[str, Any]) -> dict[str, Any]:
    predictions = response.get("predictions") or {}
    if predictions:
        first = next(iter(predictions.values()), {})
        if isinstance(first, dict):
            return first.get("extraction_result") or {}

    return response.get("extraction_result") or {}


def parse_extraction_fields(extraction: dict[str, Any]) -> tuple[dict[str, Any], dict[str, float]]:
    values: dict[str, Any] = {}
    confidences: dict[str, float] = {}

    for field in IDP_FIELDS:
        entry = extraction.get(field)
        if not isinstance(entry, dict):
            values[field] = entry
            continue
        values[field] = entry.get("value")
        score = entry.get("confidence_score")
        if score is not None:
            confidences[field] = float(score)

    doc_score = extraction.get("document_confidence_score")
    if doc_score is not None:
        confidences["document_confidence_score"] = float(doc_score)

    return values, confidences


def classify_intent(transaction_type: str | None) -> str:
    hint = (transaction_type or "subscription").lower()
    return INTENT_MAP.get(hint, "Subscription")


def parse_amount_nominal(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
    return float(cleaned) if cleaned else 0.0


def build_golden_schema(
    instruction_id: str,
    values: dict[str, Any],
    destination: str,
) -> dict[str, Any]:
    del instruction_id, destination
    return {field: values.get(field) for field in IDP_FIELDS}


_LEGACY_GOLDEN_KEYS = {
    "party": "investor_account_name",
    "intent": "transaction_type",
    "currency": "fund_currency",
    "amount": "amount_nominal",
    "quantity": "amount_unit",
    "isin": "fund_code",
    "accountId": "sa_reference_no",
    "settlementDate": "transaction_date",
}

_LEGACY_CONFIDENCE_KEYS = {
    "ISIN": "fund_code",
    "Fund": "fund_code",
    "Investor": "investor_account_name",
    "Amount": "amount_nominal",
    "Date": "transaction_date",
    "Account": "sa_reference_no",
    "Currency": "fund_currency",
    "Quantity": "amount_unit",
}


def normalize_golden_schema(schema: dict[str, Any] | None) -> dict[str, Any]:
    source = dict(schema or {})
    for old_key, new_key in _LEGACY_GOLDEN_KEYS.items():
        if old_key in source and source.get(new_key) in (None, ""):
            source[new_key] = source[old_key]

    intake_extraction = source.get("extraction_result")
    if isinstance(intake_extraction, dict):
        values, _ = parse_extraction_fields(intake_extraction)
        source.update(values)

    return {field: source.get(field) for field in IDP_FIELDS}


def normalize_field_confidences(confidences: dict[str, Any] | None) -> dict[str, float]:
    source = dict(confidences or {})
    for old_key, new_key in _LEGACY_CONFIDENCE_KEYS.items():
        if old_key in source and new_key not in source:
            source[new_key] = source[old_key]

    normalized: dict[str, float] = {}
    for field in IDP_FIELDS:
        score = source.get(field)
        normalized[field] = float(score) if score is not None else 0.0
    return normalized


def overall_confidence_from_fields(confidences: dict[str, float]) -> float:
    field_scores = [confidences[field] for field in IDP_FIELDS if field in confidences]
    if not field_scores:
        return 0.0
    return sum(field_scores) / len(field_scores)


# Global nominal fund transaction keyword risk weightage.
# investor_account_name and amount_nominal carry the highest equal weight.
FIELD_RISK_WEIGHTS: dict[str, float] = {
    "investor_account_name": 15.0,
    "amount_nominal": 15.0,
    "fund_code": 10.0,
    "transaction_type": 8.0,
    "transaction_date": 8.0,
    "fund_currency": 6.0,
    "amount_unit": 6.0,
    "reference_no": 5.0,
    "sa_reference_no": 5.0,
    "country": 4.0,
    "switch_transaction": 4.0,
    "fundcd_type": 4.0,
    "amount_all_units": 4.0,
    "sid": 4.0,
}

_MISSING_VALUES = frozenset({"", "—", "NOT APPLICABLE", "N/A", "NA", "NONE"})


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    return str(value).strip().upper() in _MISSING_VALUES


def compute_risk_score(
    values: dict[str, Any],
    confidences: dict[str, float],
) -> tuple[int, str]:
    """Composite risk index from weighted keyword gaps (missing or low-confidence fields)."""
    total_weight = sum(FIELD_RISK_WEIGHTS.values())
    if total_weight <= 0:
        return 0, "Low"

    risk_points = 0.0
    for field, weight in FIELD_RISK_WEIGHTS.items():
        if _is_missing_value(values.get(field)):
            risk_points += weight
            continue
        confidence = confidences.get(field, 0.0)
        if confidence < 98:
            risk_points += weight * (1 - confidence / 100)

    score = min(100, round(risk_points / total_weight * 100))
    if score >= 85:
        label = "Critical"
    elif score >= 70:
        label = "High"
    elif score >= 40:
        label = "Medium"
    else:
        label = "Low"
    return score, label


_SOURCE_TYPE_LABELS: dict[str, str] = {
    "pdf": "PDF",
    "swift": "SWIFT",
    "api": "API",
    "template": "Client Template",
    "excel": "Excel",
    "email": "Email",
    "portal": "Portal",
}

_LEGACY_SOURCE_ALIASES: dict[str, str] = {
    "email + pdf": "PDF",
    "email+pdf": "PDF",
    "portals & files": "Portal",
    "portals and files": "Portal",
    "client templates": "Client Template",
}


def normalize_source_label(value: str | None = None, source_type: str | None = None) -> str:
    """Return a single canonical source label (e.g. PDF, Email, SWIFT)."""
    if source_type:
        mapped = _SOURCE_TYPE_LABELS.get(source_type.strip().lower())
        if mapped:
            return mapped

    if not value:
        return "Unknown"

    key = value.strip().lower()
    if key in _LEGACY_SOURCE_ALIASES:
        return _LEGACY_SOURCE_ALIASES[key]

    for label in _SOURCE_TYPE_LABELS.values():
        if key == label.lower():
            return label

    if key == "swift":
        return "SWIFT"

    return value.strip()


def format_source_label(source_type: str, channel: str = "") -> str:
    return normalize_source_label(channel or None, source_type or None)


def format_amount_display(golden_schema: dict[str, Any] | None) -> str:
    if not golden_schema:
        return "—"
    nominal = golden_schema.get("amount_nominal")
    if nominal not in (None, ""):
        return str(nominal)
    legacy = golden_schema.get("amount")
    return str(legacy) if legacy not in (None, "") else "—"


def append_timeline(timeline: list[str], event: str) -> None:
    ts = datetime.now().strftime("%H:%M")
    timeline.append(f"{ts} — {event}")
