import json
import logging
from typing import Any

from agentx.layers.ingest.idp_schema import (
    IDP_FIELDS,
    extract_extraction_result,
    parse_extraction_fields,
)
from agentx.layers.ingest.parser_loader import ParserMeta
from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext

logger = logging.getLogger(__name__)

meta = ParserMeta(parser_id="pdf_idp", version="1.0.0", source_types=["pdf"], provider="enterprise_idp")


def _map_idp_response(response: dict[str, Any]) -> IntakeJSON:
    extraction = extract_extraction_result(response)
    values, field_confidences = parse_extraction_fields(extraction)

    extracted_fields = [
        {
            "name": field,
            "value": values.get(field),
            "confidence_score": field_confidences.get(field),
        }
        for field in IDP_FIELDS
    ]

    transaction_type = values.get("transaction_type")
    intent_hint = (transaction_type or "subscription").lower()

    return IntakeJSON(
        source_type="pdf",
        source_channel="PDF",
        party={
            "name": values.get("investor_account_name"),
            "accountId": values.get("sa_reference_no"),
        },
        transaction={
            "intentHint": intent_hint,
            **values,
        },
        extraction_result=extraction,
        field_confidences=field_confidences,
        idp_raw=response,
        document_confidence_score=field_confidences.get("document_confidence_score"),
        extracted_fields=extracted_fields,
        raw_excerpt=json.dumps(extraction, indent=2)[:4000],
        parser_used="pdf_idp",
        provider_used="enterprise_idp",
    )


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    if not hasattr(invoker, "extract_document"):
        raise RuntimeError("PDF parser requires enterprise IDP invoker")

    filename = ctx.filename or "document.pdf"
    logger.info("PDF parse started: filename=%s size=%d", filename, len(raw))
    response = await invoker.extract_document(raw, filename)
    intake = _map_idp_response(response)
    investor = (intake.party or {}).get("name") if isinstance(intake.party, dict) else None
    logger.info(
        "PDF parse complete: filename=%s investor=%s intent_hint=%s fields_extracted=%d",
        filename,
        investor or "(unknown)",
        intake.transaction.get("intentHint") if intake.transaction else "(unknown)",
        len(intake.extracted_fields or []),
    )
    return intake
