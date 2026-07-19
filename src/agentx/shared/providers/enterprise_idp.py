import asyncio
import base64
import json
import logging
import subprocess
import time
import uuid
import warnings
from pathlib import Path
from typing import Any

import httpx

from agentx.config import settings

logger = logging.getLogger(__name__)


def _cert_dir() -> Path:
    if settings.idp_cert_dir:
        return Path(settings.idp_cert_dir)
    return Path(__file__).resolve().parent / "sstm_rt_np"


def _generate_token_sync() -> dict[str, Any]:
    cert_dir = _cert_dir()
    token_jar = cert_dir / "token-tool-candidate_20241105.4.jar"
    keystore = cert_dir / "keystore.jks"
    truststore = cert_dir / "sstm_rt_np.jks"
    password = settings.idp_keystore_password

    cmd = [
        "java",
        "-Djavax.net.ssl.keyStoreType=JKS",
        f"-Djavax.net.ssl.keyStore={keystore}",
        f"-Djavax.net.ssl.keyStorePassword={password}",
        "-Djavax.net.ssl.trustStoreType=JKS",
        f"-Djavax.net.ssl.trustStore={truststore}",
        f"-Djavax.net.ssl.trustStorePassword={password}",
        "-jar",
        str(token_jar),
        settings.idp_token_url,
        settings.idp_token_client_id,
        settings.idp_token_host,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(cert_dir),
        timeout=60,
    )
    if result.returncode != 0:
        logger.error("IDP token tool failed: exit_code=%s stderr=%s", result.returncode, result.stderr.strip())
    output = result.stdout.strip()
    for line in reversed(output.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass

    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Token tool exited {result.returncode}.\n"
            f"STDOUT:\n{output}\nSTDERR:\n{result.stderr}"
        ) from exc


class EnterpriseIdpAuthProvider:
    def __init__(self) -> None:
        self._token_cache: dict[str, Any] | None = None

    def _is_expired(self, token_data: dict[str, Any]) -> bool:
        expires_at = token_data.get("_expires_at")
        if expires_at is None:
            return False
        return time.time() >= expires_at

    async def get_headers(self) -> dict[str, str]:
        token_data = await self._get_token()
        access_token = token_data.get("access_token")
        if not access_token:
            raise RuntimeError("IDP token response missing access_token")
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def refresh(self) -> None:
        self._token_cache = None

    async def _get_token(self) -> dict[str, Any]:
        if self._token_cache and not self._is_expired(self._token_cache):
            logger.debug("Using cached IDP access token")
            return self._token_cache

        logger.info("Fetching new IDP access token from %s", settings.idp_token_url)
        token_data = await asyncio.to_thread(_generate_token_sync)
        expires_in = int(token_data.get("expires_in", 300))
        token_data["_expires_at"] = time.time() + max(expires_in - 30, 0)
        self._token_cache = token_data
        logger.info("IDP access token acquired (expires_in=%ss)", expires_in)
        return token_data


class EnterpriseIdpInvoker:
    def __init__(self) -> None:
        self.auth = EnterpriseIdpAuthProvider()

    async def invoke(self, prompt: str, **kwargs) -> str:
        return json.dumps({"result": "enterprise_idp"})

    async def invoke_structured(self, prompt: str, schema: type) -> Any:
        return schema.model_validate({})

    async def extract_document(self, file_bytes: bytes, file_name: str) -> dict[str, Any]:
        trace_id = str(uuid.uuid4())
        logger.info(
            "IDP extraction request: file_name=%s size=%d trace_id=%s endpoint=%s",
            file_name,
            len(file_bytes),
            trace_id,
            settings.idp_api_url,
        )
        if not settings.idp_verify_ssl:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")

        headers = await self.auth.get_headers()
        payload = {
            "client_id": settings.idp_client_id,
            "doc_type": settings.idp_doc_type,
            "file_content": base64.b64encode(file_bytes).decode("utf-8"),
            "file_name": file_name,
            "file_path": "",
            "ocr_model_name": settings.idp_ocr_model,
            "trace_id": trace_id,
        }
        try:
            async with httpx.AsyncClient(verify=settings.idp_verify_ssl) as client:
                response = await client.post(
                    settings.idp_api_url,
                    headers=headers,
                    json=payload,
                    timeout=settings.idp_request_timeout_seconds,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "IDP extraction HTTP error: file_name=%s trace_id=%s status=%s body=%s",
                file_name,
                trace_id,
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise
        except Exception:
            logger.exception("IDP extraction failed: file_name=%s trace_id=%s", file_name, trace_id)
            raise

        logger.info("IDP extraction succeeded: file_name=%s trace_id=%s", file_name, trace_id)
        return data
