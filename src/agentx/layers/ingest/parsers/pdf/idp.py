from dataclasses import dataclass

from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext
from agentx.layers.ingest.parser_loader import ParserMeta


meta = ParserMeta(parser_id="pdf_idp", version="1.0.0", source_types=["pdf"], provider="enterprise_idp")


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    text = raw.decode("utf-8", errors="ignore")[:2000]
    return IntakeJSON(
        source_type="pdf",
        source_channel="Email + PDF",
        party={"name": "Demo Investor"},
        transaction={"intentHint": "subscription", "amount": 100000, "currency": "INR"},
        raw_excerpt=text,
        parser_used="pdf_idp",
        provider_used="enterprise_idp",
    )
