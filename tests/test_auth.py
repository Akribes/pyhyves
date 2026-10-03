import base64
import hashlib
from urllib.parse import parse_qs

import httpx
import pytest

from pyhyves.auth import PasswordAuth, PasswordCredentials, TokenAuth, TokenCredentials


class TestTokenAuth:
    @pytest.mark.asyncio
    async def test_returns_token(self):
        token = "some token"
        auth = TokenAuth(TokenCredentials(access_token=token))

        assert await auth.get_new_token() == token

    @pytest.mark.asyncio
    async def test_raises_on_refresh(self):
        token = "some token"
        auth = TokenAuth(TokenCredentials(access_token=token))

        await auth.get_new_token()
        with pytest.raises(
            Exception, match="TokenAuth does not support refreshing tokens"
        ):
            await auth.get_new_token()


class TestPasswordAuth:
    @pytest.mark.asyncio
    async def test_password_auth(self, respx_mock):
        login_id = "some login id"
        password = "some password"

        authorize_route = respx_mock.post(
            "https://auth.hyves.nl/oauth2/authorize",
            data__contains={
                "loginId": login_id,
                "password": password,
                "code_challenge_method": "S256",
                "redirect_uri": "https://hyves.nl/auth",
                "response_mode": "query",
                "response_type": "code",
                "scope": "openid offline_access",
                "client_id": "38e5b2e0-67de-4150-b71c-0e744b0ac489",
            },
        ).respond(
            status_code=302,
            headers={
                "Location": "https://hyves.nl/auth?code=somecode",
            },
        )

        respx_mock.get(
            "https://hyves.nl/auth",
            params__contains={
                "code": "somecode",
            },
        ).respond(
            status_code=200,
        )

        token_route = respx_mock.post(
            "https://auth.hyves.nl/oauth2/token",
            data__contains={
                "code": "somecode",
                "grant_type": "authorization_code",
                "redirect_uri": "https://hyves.nl/auth",
                "client_id": "38e5b2e0-67de-4150-b71c-0e744b0ac489",
            },
        ).respond(
            status_code=200,
            json={
                "access_token": "some token",
                "refresh_token": "some refresh token",
                "expires_in": 3600,
                "token_type": "Bearer",
                "userId": "some user id",
            },
        )

        async with httpx.AsyncClient() as client:
            auth = PasswordAuth(client, PasswordCredentials(login_id=login_id, password=password))
            token = await auth._do_password_auth()

        authorize_request = authorize_route.calls[0].request
        authorize_data = parse_qs(authorize_request.content.decode())
        code_challenge = authorize_data["code_challenge"][0]

        token_request = token_route.calls[0].request
        token_data = parse_qs(token_request.content.decode())
        code_verifier = token_data["code_verifier"][0]

        hashed_verifier = hashlib.sha256(code_verifier.encode("ascii")).digest()
        encoded_verifier = base64.urlsafe_b64encode(hashed_verifier)
        assert code_challenge == encoded_verifier.decode("ascii").replace("=", "")

        assert token == "some token"
