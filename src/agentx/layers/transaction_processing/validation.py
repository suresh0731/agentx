"""FDLT fund-transaction field validation rules."""

import re
from dataclasses import dataclass, field

from agentx.layers.ingest.idp_schema import _is_missing_value

TRANSACTION_TYPE_MAP = {
    "SUBSCRIPTION": "P",
    "PURCHASE": "P",
    "REDEMPTION": "S",
    "SALE": "S",
    "P": "P",
    "S": "S",
}

SWITCH_MAP = {
    "YES": "Y",
    "NO": "N",
    "Y": "Y",
    "N": "N",
}

FUNDCD_TYPE_VALUES = frozenset({"I", "V", "C", "Z"})

MANDATORY_FIELDS = (
    "transaction_date",
    "transaction_type",
    "switch_transaction",
    "reference_no",
    "sid",
    "fundcd_type",
    "fund_code",
    "fund_currency",
)


@dataclass
class FieldValidationResult:
    field: str
    passed: bool
    message: str
    needs_human_review: bool = False


@dataclass
class ValidationReport:
    passed: bool
    field_results: list[FieldValidationResult] = field(default_factory=list)
    human_review_fields: list[str] = field(default_factory=list)
    failed_fields: list[str] = field(default_factory=list)


def _field_needs_human_review(value: object, confidence: float) -> bool:
    if _is_missing_value(value):
        return True
    return confidence == 0


def _normalize_transaction_type(value: object) -> str | None:
    if _is_missing_value(value):
        return None
    return TRANSACTION_TYPE_MAP.get(str(value).strip().upper())


def _normalize_switch(value: object) -> str | None:
    if _is_missing_value(value):
        return None
    return SWITCH_MAP.get(str(value).strip().upper())


def _is_valid_date(value: object) -> bool:
    text = str(value).strip()
    if re.fullmatch(r"\d{8}", text):
        return True
    return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", text))


def _is_amount_blank(value: object) -> bool:
    return _is_missing_value(value)


def validate_fund_transaction(
    values: dict[str, object],
    confidences: dict[str, float],
) -> ValidationReport:
    """Validate extracted IDP fields against FDLT fund-transaction rules."""
    results: list[FieldValidationResult] = []
    failed_fields: list[str] = []

    def _record(fld: str, passed: bool, message: str) -> None:
        results.append(FieldValidationResult(fld, passed, message))
        if not passed:
            failed_fields.append(fld)

    # --- Mandatory fields ---
    tx_date = values.get("transaction_date")
    if _is_missing_value(tx_date):
        _record("transaction_date", False, "Transaction date is mandatory")
    elif not _is_valid_date(tx_date):
        _record("transaction_date", False, "Transaction date must be YYYYMMDD or DD/MM/YYYY")
    else:
        _record("transaction_date", True, "Transaction date format valid")

    tx_type = _normalize_transaction_type(values.get("transaction_type"))
    if tx_type is None:
        _record("transaction_type", False, "Transaction type is mandatory (P/S)")
    elif tx_type not in {"P", "S"}:
        _record("transaction_type", False, "Transaction type must be P (purchase) or S (sale)")
    else:
        _record("transaction_type", True, f"Transaction type mapped to {tx_type}")

    switch = _normalize_switch(values.get("switch_transaction"))
    if switch is None:
        _record("switch_transaction", False, "Switch transaction flag is mandatory (Y/N)")
    elif switch not in {"Y", "N"}:
        _record("switch_transaction", False, "Switch transaction must be Y or N")
    else:
        _record("switch_transaction", True, f"Switch transaction mapped to {switch}")

    ref_no = values.get("reference_no")
    if _is_missing_value(ref_no):
        _record("reference_no", False, "Reference number is mandatory")
    elif not re.fullmatch(r"[A-Za-z0-9]{1,12}", str(ref_no).strip()):
        _record("reference_no", False, "Reference number must be alphanumeric, max 12 characters")
    else:
        _record("reference_no", True, "Reference number valid")

    sid = values.get("sid")
    if _is_missing_value(sid):
        _record("sid", False, "SID (AccountId) is mandatory")
    elif not re.fullmatch(r"\d{6}", str(sid).strip()):
        _record("sid", False, "SID must be numeric, 6 digits")
    else:
        _record("sid", True, "SID valid")

    fundcd = values.get("fundcd_type")
    if _is_missing_value(fundcd):
        _record("fundcd_type", False, "Fund type code is mandatory")
    elif str(fundcd).strip().upper() not in FUNDCD_TYPE_VALUES:
        _record("fundcd_type", False, "Fund type code must be I, V, C, or Z")
    else:
        _record("fundcd_type", True, "Fund type code valid")

    fund_code = values.get("fund_code")
    fundcd_upper = str(fundcd).strip().upper() if not _is_missing_value(fundcd) else ""
    if _is_missing_value(fund_code):
        _record("fund_code", False, "Fund code (ISIN) is mandatory")
    elif fundcd_upper == "I" and not re.fullmatch(r"[A-Za-z0-9]{12}", str(fund_code).strip()):
        _record("fund_code", False, "ISIN fund code must be 12 alphanumeric characters")
    else:
        _record("fund_code", True, "Fund code present")

    fund_ccy = values.get("fund_currency")
    if _is_missing_value(fund_ccy):
        _record("fund_currency", False, "Fund currency is mandatory")
    elif not re.fullmatch(r"[A-Z]{3}", str(fund_ccy).strip().upper()):
        _record("fund_currency", False, "Fund currency must be a 3-letter ISO 4217 code")
    else:
        _record("fund_currency", True, "Fund currency valid")

    # --- Conditional mandatory fields ---
    amount_nominal = values.get("amount_nominal")
    amount_unit = values.get("amount_unit")
    amount_all_units = values.get("amount_all_units")

    nominal_blank = _is_amount_blank(amount_nominal)
    unit_blank = _is_amount_blank(amount_unit)
    all_units_blank = _is_amount_blank(amount_all_units)

    if nominal_blank and unit_blank and all_units_blank:
        _record("amount_nominal", False, "At least one amount field (nominal, unit, or all units) is required")
    else:
        _record("amount_nominal", True, "Amount (nominal) satisfied")

    if unit_blank and nominal_blank and all_units_blank:
        _record("amount_unit", False, "Amount (unit) required when nominal and all-units are blank")
    else:
        _record("amount_unit", True, "Amount (unit) satisfied")

    if all_units_blank and nominal_blank and unit_blank:
        _record("amount_all_units", False, "Amount (all units) required when nominal and units are blank")
    elif not all_units_blank and str(amount_all_units).strip().upper() not in {"Y", "N", "NOT APPLICABLE"}:
        _record("amount_all_units", False, "Amount (all units) must be Y for full redemption")
    else:
        _record("amount_all_units", True, "Amount (all units) satisfied")

    sa_ref = values.get("sa_reference_no")
    if switch == "Y" and _is_missing_value(sa_ref):
        _record("sa_reference_no", False, "SA reference number is mandatory for switch transactions")
    elif switch == "Y" and not re.fullmatch(r"[A-Za-z0-9]{1,12}", str(sa_ref).strip()):
        _record("sa_reference_no", False, "SA reference number must be alphanumeric, max 12 characters")
    else:
        _record("sa_reference_no", True, "SA reference number satisfied")

    review_scope = set(MANDATORY_FIELDS)
    if nominal_blank and unit_blank and all_units_blank:
        review_scope.update(["amount_nominal", "amount_unit", "amount_all_units"])
    if switch == "Y":
        review_scope.add("sa_reference_no")

    human_review_fields = [
        fld for fld in review_scope
        if _field_needs_human_review(values.get(fld), confidences.get(fld, 0.0))
    ]

    for result in results:
        result.needs_human_review = result.field in human_review_fields

    passed = not failed_fields and not human_review_fields
    return ValidationReport(
        passed=passed,
        field_results=results,
        human_review_fields=human_review_fields,
        failed_fields=failed_fields,
    )
