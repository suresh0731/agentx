import logging
import uuid

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.idp_schema import append_timeline, format_source_label, normalize_source_label
from agentx.layers.ingest.parser_loader import ParserLoader
from agentx.layers.ingest.parsers._protocol import ParseContext
from agentx.shared.providers.factory import ProviderFactory

logger = logging.getLogger(__name__)


class IngestAgent:
    async def run(self, raw: bytes, source_type: str, filename: str = "") -> InstructionState:
        logger.info(
            "Ingest started: filename=%s source_type=%s payload_size=%d",
            filename or "(unnamed)",
            source_type,
            len(raw),
        )
        module = ParserLoader.load(source_type)
        provider_key = getattr(module, "meta").provider
        logger.debug("Parser loaded: parser_id=%s provider=%s", getattr(module, "meta").parser_id, provider_key)
        invoker = ProviderFactory.get_invoker(provider_key)
        ctx = ParseContext(source_type=source_type, filename=filename)
        intake = await ParserLoader.parse(source_type, raw, ctx, invoker)
        instruction_id = intake.instruction_ref or f"INS-{uuid.uuid4().hex[:7].upper()}"
        source_label = format_source_label(source_type, intake.source_channel)
        timeline: list[str] = []
        append_timeline(timeline, f"Ingestion ({source_label})")
        investor = (intake.party or {}).get("name") if isinstance(intake.party, dict) else None
        logger.info(
            "Ingest complete: instruction_id=%s parser=%s channel=%s investor=%s",
            instruction_id,
            intake.parser_used,
            normalize_source_label(intake.source_channel, source_type),
            investor or "(unknown)",
        )
        return InstructionState(
            instruction_id=instruction_id,
            channel=normalize_source_label(intake.source_channel, source_type),
            source_type=source_type,
            intake_json=intake.model_dump(),
            journey=JourneyState(completed_through=1, active_step=2),
            decisions=["Ingestion complete", f"Parser: {intake.parser_used}"],
            timeline=timeline,
        )
