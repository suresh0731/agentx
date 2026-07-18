import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from agentx.layers.ingest.parsers._protocol import IntakeJSON, ParseContext


@dataclass
class ParserMeta:
    parser_id: str
    version: str
    source_types: list[str]
    provider: str


@lru_cache
def _load_registry() -> dict:
    path = Path(__file__).parent / "parser_registry.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class ParserLoader:
    _cache: dict[str, object] = {}

    @classmethod
    def resolve_module_path(cls, source_type: str) -> str:
        reg = _load_registry()
        entry = reg["parsers"].get(source_type, reg["parsers"]["api"])
        active = entry["active"]
        return entry["modules"][active]

    @classmethod
    def load(cls, source_type: str):
        module_path = cls.resolve_module_path(source_type)
        if module_path not in cls._cache:
            cls._cache[module_path] = importlib.import_module(module_path)
        return cls._cache[module_path]

    @classmethod
    async def parse(cls, source_type: str, raw: bytes, ctx: ParseContext, invoker) -> IntakeJSON:
        module = cls.load(source_type)
        return await module.parse(raw, ctx, invoker)
