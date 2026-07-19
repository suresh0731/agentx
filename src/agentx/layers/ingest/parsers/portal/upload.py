from agentx.layers.ingest.parser_loader import ParserMeta
from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext

meta = ParserMeta(parser_id="portal_upload", version="1.0.0", source_types=["portal"], provider="none")


async def parse(raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
    return IntakeJSON(
        source_type="portal",
        source_channel="Portal",
        parser_used="portal_upload",
        provider_used="none",
    )
