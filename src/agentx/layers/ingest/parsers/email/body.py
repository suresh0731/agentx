from agentx.layers.ingest.parser_loader import ParserMeta
from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext

meta = ParserMeta(parser_id="email_body", version="1.0.0", source_types=["email"], provider="cloud_llm")


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    return IntakeJSON(
        source_type="email",
        source_channel="Email",
        parser_used="email_body",
        provider_used="cloud_llm",
    )
