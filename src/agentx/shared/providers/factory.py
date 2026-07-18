from pydantic import BaseModel


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
    def get_auth(provider_key: str) -> MockAuthProvider:
        return MockAuthProvider()

    @staticmethod
    def get_invoker(provider_key: str) -> MockModelInvoker:
        return MockModelInvoker()
