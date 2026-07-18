from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, Field


class IntakeJSON(BaseModel):
    instruction_ref: str | None = None
    source_type: str
    source_channel: str
    detected_language: str = "en"
    normalized_language: str = "en"
    party: dict[str, Any] = Field(default_factory=dict)
    transaction: dict[str, Any] = Field(default_factory=dict)
    extracted_fields: list[dict[str, Any]] = Field(default_factory=list)
    raw_excerpt: str = ""
    parser_used: str = ""
    parser_version: str = "1.0.0"
    provider_used: str = "mock"


@dataclass
class ParseContext:
    source_type: str
    filename: str = ""
    metadata: dict[str, Any] | None = None


class ParserPlugin(Protocol):
    meta: Any
    async def parse(self, raw: bytes, ctx: ParseContext, invoker: Any) -> IntakeJSON: ...
