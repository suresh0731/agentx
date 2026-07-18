import uuid

from agentx.domain.models import InstructionState, JourneyState
from agentx.layers.ingest.parser_loader import ParserLoader
from agentx.layers.ingest.parsers._protocol import ParseContext
from agentx.shared.providers.factory import ProviderFactory


class IngestAgent:
  async def run(self, raw: bytes, source_type: str, filename: str = "") -> InstructionState:
    invoker = ProviderFactory.get_invoker("mock")
    ctx = ParseContext(source_type=source_type, filename=filename)
    intake = await ParserLoader.parse(source_type, raw, ctx, invoker)
    instruction_id = intake.instruction_ref or f"INS-{uuid.uuid4().hex[:7].upper()}"
    return InstructionState(
      instruction_id=instruction_id,
      channel=intake.source_channel,
      source_type=source_type,
      intake_json=intake.model_dump(),
      journey=JourneyState(completed_through=1, active_step=2),
      decisions=["Ingestion complete", f"Parser: {intake.parser_used}"],
    )
