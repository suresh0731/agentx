import json

from dataclasses import dataclass

from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext
from agentx.layers.ingest.parser_loader import ParserMeta


meta = ParserMeta(parser_id="api_json", version="1.0.0", source_types=["api", "template"], provider="none")


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        data = {}
    channel = "API" if ctx.source_type == "api" else "Client Templates"
    return IntakeJSON(
        source_type=ctx.source_type,
        source_channel=channel,
        party=data.get("party", {}),
        transaction=data.get("transaction", data),
        raw_excerpt=json.dumps(data)[:500],
        parser_used="api_json",
        provider_used="none",
    )
