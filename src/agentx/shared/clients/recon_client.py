"""HTTP client for the external reconciliation validation service."""

from __future__ import annotations

import logging

import httpx

from agentx.config import settings

logger = logging.getLogger(__name__)


class ReconServiceClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float | None = None):
        self.base_url = (base_url or settings.recon_service_url).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.recon_service_timeout_seconds

    async def validate(
        self,
        instruction_id: str,
        destination: str,
        ingested_record: dict,
        route_reference: str | None = None,
    ) -> dict:
        payload = {
            "instruction_id": instruction_id,
            "destination": destination or "RFAS",
            "ingested_record": ingested_record,
            "route_reference": route_reference,
        }
        url = f"{self.base_url}/api/v1/reconcile/validate"
        logger.info("Calling recon service: instruction_id=%s url=%s", instruction_id, url)
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
