from dataclasses import dataclass

from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext
from agentx.layers.ingest.parser_loader import ParserMeta


meta = ParserMeta(parser_id="swift_rfas", version="1.0.0", source_types=["swift"], provider="cloud_llm")


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    text = raw.decode("utf-8", errors="ignore")
    return IntakeJSON(
        source_type="swift",
        source_channel="SWIFT",
        party={"name": "SWIFT Client"},
        transaction={"intentHint": "subscription", "amount": 250000, "currency": "INR", "isin": "INF109K01VQ1"},
        raw_excerpt=text[:500],
        parser_used="swift_rfas",
        provider_used="cloud_llm",
    )
