"""Write routed instruction rows to destination-specific Excel output folders."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from openpyxl import Workbook

from agentx.config import settings
from agentx.domain.models import InstructionState
from agentx.layers.ingest.idp_schema import IDP_FIELDS, parse_extraction_fields

logger = logging.getLogger(__name__)

DESTINATION_FOLDERS = ("RTAS", "ViTAL", "RFAS")

ROUTING_OUTPUT_HEADERS: tuple[str, ...] = (
    "No.",
    "Transaction Date",
    "Transaction Type",
    "Switch Transaction",
    "Reference No.",
    "Status",
    "IM Fee Amendment",
    "IM Payment Date Amendment",
    "SA Code",
    "SA Name",
    "Investor Fund Unit A/C No.",
    "Investor Fund Unit A/C Name",
    "SID",
    "FundCd Type",
    "Fund Code",
    "Fund Name",
    "IM Code",
    "IM Name",
    "CB Code",
    "CB Name",
    "Fund CCY",
    "Amount (Nominal)",
    "Amount (Unit)",
    "Amount (All Units)",
    "Fee (Nominal)",
    "Fee (Unit)",
    "Fee (%)",
    "Transfer Path",
    "REDM Payment A/C Sequential Code",
    "REDM Payment Bank BIC Code",
    "REDM Payment Bank BI Member Code",
    "REDM Payment Bank Name",
    "REDM Payment A/C No.",
    "REDM Payment A/C Name",
    "Payment Date",
    "Transfer Type",
    "Input Date",
    "Upload Reference No.",
    "SA Reference No.",
    "IM Status",
    "CB Status",
    "CB Completion Status",
    "Trade Date",
    "Nav Date",
    "Settlement Date",
)

# Maps routing spreadsheet headers to golden-schema / IDP field keys.
HEADER_TO_IDP_FIELD: dict[str, str] = {
    "Transaction Date": "transaction_date",
    "Transaction Type": "transaction_type",
    "Switch Transaction": "switch_transaction",
    "Reference No.": "reference_no",
    "Investor Fund Unit A/C No.": "sa_reference_no",
    "Investor Fund Unit A/C Name": "investor_account_name",
    "SID": "sid",
    "FundCd Type": "fundcd_type",
    "Fund Code": "fund_code",
    "Fund CCY": "fund_currency",
    "Amount (Nominal)": "amount_nominal",
    "Amount (Unit)": "amount_unit",
    "Amount (All Units)": "amount_all_units",
    "SA Reference No.": "sa_reference_no",
}


def _schema_value(raw: Any) -> Any:
    if isinstance(raw, dict) and "value" in raw:
        return raw.get("value")
    return raw


def _format_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def collect_idp_values(state: InstructionState) -> dict[str, Any]:
    """Merge golden-schema and intake extraction values for routing output."""
    values: dict[str, Any] = {}
    extraction = state.intake_json.get("extraction_result") or {}
    parsed_extraction, _ = parse_extraction_fields(extraction) if extraction else ({}, {})

    for field in IDP_FIELDS:
        value = _schema_value(state.golden_schema.get(field))
        if value in (None, ""):
            value = parsed_extraction.get(field)
        values[field] = value
    return values


def build_routing_row(state: InstructionState, row_number: int = 1) -> list[str]:
    """Build a single routing output row from extracted IDP values."""
    idp_values = collect_idp_values(state)
    today = datetime.now().strftime("%Y-%m-%d")
    row: list[str] = []

    for header in ROUTING_OUTPUT_HEADERS:
        if header == "No.":
            row.append(str(row_number))
        elif header == "Status":
            row.append(state.status or "Routed")
        elif header == "Input Date":
            row.append(today)
        elif header == "Upload Reference No.":
            row.append(state.instruction_id)
        elif header in HEADER_TO_IDP_FIELD:
            row.append(_format_cell(idp_values.get(HEADER_TO_IDP_FIELD[header])))
        else:
            row.append("")

    return row


def destination_output_dir(destination: str, base_dir: Path | None = None) -> Path:
    folder = destination if destination in DESTINATION_FOLDERS else "RFAS"
    root = base_dir or (settings.project_root / settings.route_output_folder)
    return root / folder


def ensure_destination_folders(base_dir: Path | None = None) -> None:
    root = base_dir or (settings.project_root / settings.route_output_folder)
    for folder in DESTINATION_FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)


def write_routing_output(
    state: InstructionState,
    destination: str,
    base_dir: Path | None = None,
) -> Path:
    """Create an Excel file for the routed instruction in the destination folder."""
    output_dir = destination_output_dir(destination, base_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{state.instruction_id}_{timestamp}.xlsx"
    output_path = output_dir / filename

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Routing Output"
    sheet.append(list(ROUTING_OUTPUT_HEADERS))
    sheet.append(build_routing_row(state))

    workbook.save(output_path)
    logger.info(
        "Routing output saved: instruction_id=%s destination=%s path=%s",
        state.instruction_id,
        destination,
        output_path,
    )
    return output_path
