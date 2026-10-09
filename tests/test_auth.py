import asyncio
import base64
import hashlib
from typing import Any
from urllib.parse import parse_qs

# respx validates side effects against the httpx (v1) classes, even though it mocks httpx2,
# so the login redirect below has to be an httpx.Response
import httpx
import httpx2
import pytest

from pyhyves.auth import (
    HyvesAuthException,
    HyvesOAuth2Client,
    PasswordCredentials,
    TokenCredentials,
)

AUTHORIZE_URL = "https://auth.hyves.nl/oauth2/authorize"
TOKEN_URL = "https://auth.hyves.nl/oauth2/token"
REDIRECT_URL = "https://hyves.nl/auth"
API_URL = "https://api.hyves.nl"

CLIENT_ID = "38e5b2e0-67de-4150-b71c-0e744b0ac489"


def form(request: httpx2.Request) -> dict[str, str]:
    """The request body as a flat dict of form fields"""
    return {key: values[0] for key, values in parse_qs(request.content.decode()).items()}


def uses_http2(client: httpx2.AsyncClient) -> bool:
    """Whether the client's transport can negotiate HTTP/2."""
    pool = getattr(getattr(client, "_transport", None), "_pool", None)
    return bool(getattr(pool, "_http2", False))


def echo_state(state: str | None = None):
    """A handler for the authorization endpoint that redirects with an authorization code.

    The state is echoed back from the request, as the real server does, unless it is forced
    to a fixed value.
    """

    def handler(request: httpx2.Request) -> httpx.Response:
        echoed = state if state is not None else form(request)["state"]
        return httpx.Response(
            302, headers={"Location": f"{REDIRECT_URL}?code=somecode&state={echoed}"}
        )

    return handler


def mock_login(
    httpx2_mock,
    *,
    state: str | None = None,
    token: dict[str, Any] | None = None,
    delay: float = 0.0,
) -> tuple[Any, Any]:
    """Mock a successful login. Returns the (authorize, token) routes.

    ``delay`` makes the token endpoint slow, so that concurrent requests overlap.
    """
    authorize = httpx2_mock.post(AUTHORIZE_URL)
    authorize.mock(side_effect=echo_state(state))
    httpx2_mock.get(REDIRECT_URL).respond(200)

    async def token_endpoint(request: httpx2.Request) -> httpx.Response:
        if delay:
            await asyncio.sleep(delay)
        return httpx.Response(
            200,
            json=token
            or {
                "access_token": "some token",
                "refresh_token": "some refresh token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "userId": "some user id",
            },
        )

    token_route = httpx2_mock.post(TOKEN_URL, data__contains={"grant_type": "authorization_code"})
    token_route.mock(side_effect=token_endpoint)
    return authorize, token_route


class TestPasswordCredentials:
    @pytest.mark.asyncio
    async def test_logs_in_and_authenticates(self, httpx2_mock):
        authorize, token = mock_login(httpx2_mock)
        api = httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="some login id", password="some password")) as client:
            response = await client.request("GET", f"{API_URL}/v1/me")

        assert response.status_code == 200
        assert api.calls[0].request.headers["authorization"] == "Bearer some token"

        # The authorization request carries the credentials and our code challenge
        sent = form(authorize.calls[0].request)
        assert sent["loginId"] == "some login id"
        assert sent["password"] == "some password"
        assert sent["client_id"] == CLIENT_ID
        assert sent["redirect_uri"] == REDIRECT_URL
        assert sent["response_mode"] == "query"
        assert sent["response_type"] == "code"
        assert sent["scope"] == "openid offline_access"
        assert sent["code_challenge_method"] == "S256"

        # The code verifier sent to the token endpoint matches the challenge
        token_body = form(token.calls[0].request)
        assert token_body["grant_type"] == "authorization_code"
        assert token_body["code"] == "somecode"
        verifier = token_body["code_verifier"]
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        assert base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=") == sent["code_challenge"]

    @pytest.mark.asyncio
    async def test_only_logs_in_once(self, httpx2_mock):
        _, token = mock_login(httpx2_mock)
        api = httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="password")) as client:
            for _ in range(3):
                await client.request("GET", f"{API_URL}/v1/me")

        assert len(token.calls) == 1
        assert len(api.calls) == 3

    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_validates_state(self, httpx2_mock):
        mock_login(httpx2_mock, state="a different state")
        httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="password")) as client:
            with pytest.raises(HyvesAuthException, match="Login failed"):
                await client.request("GET", f"{API_URL}/v1/me")

    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_reports_invalid_credentials(self, httpx2_mock):
        mock_login(
            httpx2_mock,
            token={"error": "invalid_grant", "error_description": "Invalid username or password"},
        )
        httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="wrong")) as client:
            with pytest.raises(HyvesAuthException, match="invalid_grant"):
                await client.request("GET", f"{API_URL}/v1/me")

    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_withholds_token_for_public_endpoints(self, httpx2_mock):
        _, token = mock_login(httpx2_mock)
        public = httpx2_mock.get(f"{API_URL}/v1/public").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="password")) as client:
            await client.request("GET", f"{API_URL}/v1/public", withhold_token=True)

        assert "authorization" not in public.calls[0].request.headers
        assert not token.calls


class TestRefresh:
    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self, httpx2_mock):
        mock_login(httpx2_mock)
        refresh = httpx2_mock.post(TOKEN_URL, data__contains={"grant_type": "refresh_token"}).respond(
            200, json={"access_token": "a new token", "expires_in": 3600, "token_type": "Bearer"}
        )
        api = httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="password")) as client:
            await client.request("GET", f"{API_URL}/v1/me")

            # Expire the access token, but keep the refresh token
            client.token["expires_at"] = 0
            response = await client.request("GET", f"{API_URL}/v1/me")

        assert response.request.headers["authorization"] == "Bearer a new token"
        assert len(api.calls) == 2

        sent = form(refresh.calls[0].request)
        assert sent["grant_type"] == "refresh_token"
        assert sent["refresh_token"] == "some refresh token"
        assert sent["client_id"] == CLIENT_ID

    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_does_not_refresh_valid_token(self, httpx2_mock):
        _, token = mock_login(httpx2_mock)
        httpx2_mock.post(TOKEN_URL, data__contains={"grant_type": "refresh_token"}).respond(
            200, json={"access_token": "a new token", "expires_in": 3600, "token_type": "Bearer"}
        )
        httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="password")) as client:
            for _ in range(3):
                await client.request("GET", f"{API_URL}/v1/me")

        assert len(token.calls) == 1
        assert client.token["access_token"] == "some token"


class TestConcurrentLogin:
    @pytest.mark.asyncio
    async def test_logs_in_once_for_concurrent_requests(self, httpx2_mock):
        # A slow token endpoint makes the requests overlap, so that they really race
        _, token = mock_login(httpx2_mock, delay=0.05)
        httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="password")) as client:
            responses = await asyncio.gather(
                *(client.request("GET", f"{API_URL}/v1/me") for _ in range(10))
            )

        assert all(r.status_code == 200 for r in responses)
        assert len(token.calls) == 1

    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_fails_concurrent_requests_when_login_fails(self, httpx2_mock):
        """A failed login should be reported, not swallowed into a missing-token error."""
        mock_login(
            httpx2_mock,
            delay=0.05,
            token={"error": "invalid_grant", "error_description": "nope"},
        )
        httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(PasswordCredentials(login_id="user", password="wrong")) as client:
            responses = await asyncio.gather(
                *(client.request("GET", f"{API_URL}/v1/me") for _ in range(5)),
                return_exceptions=True,
            )

        assert all(isinstance(r, HyvesAuthException) for r in responses)
        assert all("invalid_grant" in str(r) for r in responses)


class TestTokenCredentials:
    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_sends_token_without_logging_in(self, httpx2_mock):
        authorize = httpx2_mock.post(AUTHORIZE_URL).respond(200)
        token = httpx2_mock.post(TOKEN_URL).respond(200)
        api = httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(TokenCredentials(access_token="some token")) as client:
            response = await client.request("GET", f"{API_URL}/v1/me")

        assert response.request.headers["authorization"] == "Bearer some token"
        assert not authorize.calls
        assert not token.calls
        assert len(api.calls) == 1

    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_token_is_never_refreshed(self, httpx2_mock):
        """A token from DevTools cannot be refreshed, so it is reused as-is."""
        httpx2_mock.post(TOKEN_URL).respond(
            200, json={"access_token": "a new token", "token_type": "Bearer"}
        )
        api = httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client(TokenCredentials(access_token="some token")) as client:
            for _ in range(3):
                await client.request("GET", f"{API_URL}/v1/me")

        assert len(api.calls) == 3
        assert all(call.request.headers["authorization"] == "Bearer some token" for call in api.calls)

        # No expiry information means authlib treats the token as valid forever
        assert client.token.is_expired() is None


class TestWithoutCredentials:
    @pytest.mark.httpx2(assert_all_called=False)
    @pytest.mark.asyncio
    async def test_raises_for_authenticated_endpoints(self, httpx2_mock):
        api = httpx2_mock.get(f"{API_URL}/v1/me").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client() as client:
            with pytest.raises(HyvesAuthException, match="no credentials were provided"):
                await client.request("GET", f"{API_URL}/v1/me")

        assert not api.calls

    @pytest.mark.asyncio
    async def test_allows_public_endpoints(self, httpx2_mock):
        public = httpx2_mock.get(f"{API_URL}/v1/public").respond(
            200, json={"hasResult": True, "result": {}, "errors": []}
        )

        async with HyvesOAuth2Client() as client:
            response = await client.request("GET", f"{API_URL}/v1/public", withhold_token=True)

        assert response.status_code == 200
        assert "authorization" not in public.calls[0].request.headers


class TestClientConfiguration:
    @pytest.mark.asyncio
    async def test_enables_http2_by_default(self):
        async with HyvesOAuth2Client(TokenCredentials(access_token="t")) as client:
            assert uses_http2(client)

    @pytest.mark.asyncio
    async def test_allows_overriding_http2(self):
        async with HyvesOAuth2Client(TokenCredentials(access_token="t"), http2=False) as client:
            assert not uses_http2(client)

    @pytest.mark.asyncio
    async def test_forwards_client_kwargs(self):
        timeout = httpx2.Timeout(5.0)
        async with HyvesOAuth2Client(TokenCredentials(access_token="t"), timeout=timeout) as client:
            assert client.timeout == timeout