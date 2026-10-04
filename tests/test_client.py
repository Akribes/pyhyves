from unittest.mock import AsyncMock

import httpx
import pytest
from pydantic import BaseModel

from pyhyves.api.client import HTTPClient


class Dummy(BaseModel):
    id: int

class NestedDummy(BaseModel):
    id: int
    things: dict[str, str]

TEST_OBJECT = NestedDummy(id=1, things={"a": "b"})
TEST_DATA = TEST_OBJECT.model_dump(mode="json")
TEST_RESPONSE = {
    "hasResult": True,
    "result": TEST_DATA,
    "errors": [],
}


class TestHTTPClient:
    @pytest.mark.asyncio
    async def test_get_unauthenticated_request(self, respx_mock):
        respx_mock.get(
            "https://api.hyves.nl/v1/fake-endpoint",
            params={
                "id": 1,
            },
        ).respond(
            status_code=200,
            json=TEST_RESPONSE,
        )

        async with httpx.AsyncClient() as http:
            client = HTTPClient(client=http)
            result = await client.get(
                "/v1/fake-endpoint",
                response_type=NestedDummy,
                params=Dummy(id=1),
                auth_required=False
            )

        assert result == TEST_OBJECT

    @pytest.mark.asyncio
    async def test_get_includes_authentication_header(self, respx_mock):
        respx_mock.get(
            "https://api.hyves.nl/v1/fake-endpoint",
            headers={
                "Authorization": "Bearer 123456",
            }
        ).respond(
            status_code=200,
            json=TEST_RESPONSE,
        )

        auth = AsyncMock()
        auth.get_new_token.return_value = "123456"

        async with httpx.AsyncClient() as http:
            client = HTTPClient(
                auth=auth,
                client=http
            )
            result = await client.get("/v1/fake-endpoint", response_type=NestedDummy)

        assert result == TEST_OBJECT

    @pytest.mark.asyncio
    async def test_get_iter_returns_all_items(self, respx_mock):
        respx_mock.get(
            "https://api.hyves.nl/v1/fake-endpoint",
            params__eq={
                "limit": "20",
                "id": 1,
            }
        ).respond(
            status_code=200,
            json={
                "hasResult": True,
                "result": {
                    "items": [
                        {"id": i} for i in range(20)
                    ],
                    "cursor": "a",
                    "hasNext": True,
                    "total": None,
                    "limit": 20,
                },
                "errors": [],
            }
        )
        respx_mock.get(
            "https://api.hyves.nl/v1/fake-endpoint",
            params__eq={
                "cursor": "a",
                "limit": "20",
                "id": 1,
            }
        ).respond(
            status_code=200,
            json={
                "hasResult": True,
                "result": {
                    "items": [
                        {"id": 20}
                    ],
                    "cursor": None,
                    "hasNext": False,
                    "total": None,
                    "limit": 20,
                },
                "errors": [],
            }
        )

        async with httpx.AsyncClient() as http:
            client = HTTPClient(client=http)

            results = []
            async for x in client.get_iter(
                "/v1/fake-endpoint",
                response_type=Dummy,
                params=Dummy(id=1),
                auth_required=False
            ):
                results.append(x.id)

        assert results == list(range(21))