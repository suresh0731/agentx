from dataclasses import dataclass

from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext
from agentx.layers.ingest.parser_loader import ParserMeta


meta = ParserMeta(parser_id="excel_rtas", version="1.0.0", source_types=["excel"], provider="cloud_llm")


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    return IntakeJSON(
        source_type="excel",
        source_channel="Excel",
        transaction={"intentHint": "redemption", "amount": 50000},
        parser_used="excel_rtas",
        provider_used="cloud_llm",
    )
