"""Rule-based instruction routing backed by the GoRules zen-engine.

Loads the JSON Decision Model (JDM) graph in `routing_rules.json` and
evaluates it to decide which downstream system (RTAS / ViTAL / RFAS) an
instruction should be dispatched to, based on its transaction `intentHint`
and `country`.

Rule summary:
 - intentHint in (subscription, redemption):
   - country in (HK, Hong Kong) -> RTAS
   - otherwise                 -> ViTAL
 - all other transaction types -> RFAS
"""

import logging
import re
from pathlib import Path
from typing import Any

import zen

logger = logging.getLogger(__name__)

_RULES_PATH = Path(__file__).with_name("routing_rules.json")

VALID_DESTINATIONS = ("RTAS", "ViTAL", "RFAS")
DEFAULT_DESTINATION = "RFAS"

_engine = zen.ZenEngine()
_decision = _engine.create_decision(_RULES_PATH.read_text(encoding="utf-8"))


def normalize_country(country: str | None) -> str:
    """Normalize country values for routing rule evaluation."""
    if not country:
        return ""
    normalized = re.sub(r"\s+", " ", str(country).strip().lower())
    normalized = normalized.replace(".", "")
    if normalized in {"hk", "hongkong"}:
        return "hk"
    if normalized == "hong kong":
        return "hong kong"
    return normalized


def evaluate_destination(intent_hint: str | None, country: str | None) -> str:
    """Evaluate the JDM routing decision table for a transaction's
    `intentHint` and `country`, returning one of RTAS / ViTAL / RFAS.
    """
    context: dict[str, Any] = {
        "intentHint": (intent_hint or "").strip().lower(),
        "country": normalize_country(country),
    }
    response = _decision.evaluate(context)
    destination = (response.get("result") or {}).get("destination", DEFAULT_DESTINATION)
    if destination not in VALID_DESTINATIONS:
        logger.warning(
            "Routing rules engine returned unexpected destination %r for context %s - defaulting to %s",
            destination,
            context,
            DEFAULT_DESTINATION,
        )
        return DEFAULT_DESTINATION
    logger.debug("Routing rules engine: context=%s -> destination=%s", context, destination)
    return destination
