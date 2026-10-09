import pytest
from pydantic import BaseModel

from pyhyves.api.client import HTTPClient
from pyhyves.auth import HyvesAuthException, HyvesOAuth2Client, TokenCredentials

API_URL = "https://api.hyves.nl"


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
    async def test_get_unauthenticated_request(self, httpx2_mock):
        httpx2_mock.get(f"{API_URL}/v1/fake-endpoint").respond(200, json=TEST_RESPONSE)

        async with HyvesOAuth2Client() as oauth:
            client = HTTPClient(oauth)
            result = await client.get(
                "/v1/fake-endpoint",
                response_type=NestedDummy,
                params=Dummy(id=1),
                auth_required=False,
            )

        assert result == TEST_OBJECT

    @pytest.mark.asyncio
    async def test_get_includes_authentication_header(self, httpx2_mock):
        api = httpx2_mock.get(f"{API_URL}/v1/fake-endpoint").respond(200, json=TEST_RESPONSE)

        async with HyvesOAuth2Client(TokenCredentials(access_token="123456")) as oauth:
            client = HTTPClient(oauth)
            result = await client.get("/v1/fake-endpoint", response_type=NestedDummy)

        assert result == TEST_OBJECT
        assert api.calls[0].request.headers["authorization"] == "Bearer 123456"

    @pytest.mark.asyncio
    async def test_get_iter_returns_all_items(self, httpx2_mock):
        # The first page, then the page identified by its cursor
        httpx2_mock.get(
            f"{API_URL}/v1/fake-endpoint", params__eq={"limit": "20", "id": "1"}
        ).respond(
            200,
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
            },
        )
        httpx2_mock.get(
            f"{API_URL}/v1/fake-endpoint", params__eq={"limit": "20", "id": "1", "cursor": "a"}
        ).respond(
            200,
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
            },
        )

        async with HyvesOAuth2Client() as oauth:
            client = HTTPClient(oauth)
            results = []
            async for x in client.get_iter(
                "/v1/fake-endpoint",
                response_type=Dummy,
                params=Dummy(id=1),
                auth_required=False,
            ):
                results.append(x.id)

        assert results == list(range(21))

    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_raises_without_credentials(self, httpx2_mock):
        api = httpx2_mock.get(f"{API_URL}/v1/fake-endpoint").respond(200, json=TEST_RESPONSE)

        async with HyvesOAuth2Client() as oauth:
            client = HTTPClient(oauth)
            with pytest.raises(HyvesAuthException, match="no credentials were provided"):
                await client.get("/v1/fake-endpoint", response_type=NestedDummy)

        assert not api.calls
