from dataclasses import dataclass

from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext
from agentx.layers.ingest.parser_loader import ParserMeta


meta = ParserMeta(parser_id="swift_sstm", version="1.0.0", source_types=["swift"], provider="cloud_llm")


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    return IntakeJSON(source_type="swift", source_channel="SWIFT", parser_used="swift_sstm", provider_used="cloud_llm")
