import logging

from pydantic import BaseModel

from agentx.shared.providers.enterprise_idp import EnterpriseIdpAuthProvider, EnterpriseIdpInvoker

logger = logging.getLogger(__name__)


class MockAuthProvider:
    async def get_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer mock-token"}

    async def refresh(self) -> None:
        return None


class MockModelInvoker:
    async def invoke(self, prompt: str, **kwargs) -> str:
        return '{"result": "mock"}'

    async def invoke_structured(self, prompt: str, schema: type[BaseModel]) -> BaseModel:
        return schema.model_validate({})


class ProviderFactory:
    @staticmethod
    def get_auth(provider_key: str):
        if provider_key == "enterprise_idp":
            return EnterpriseIdpAuthProvider()
        return MockAuthProvider()

    @staticmethod
    def get_invoker(provider_key: str):
        logger.debug("Resolving provider invoker: provider_key=%s", provider_key)
        if provider_key == "enterprise_idp":
            return EnterpriseIdpInvoker()
        return MockModelInvoker()
