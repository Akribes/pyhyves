import base64
import hashlib
import logging
import secrets
import urllib.parse
from typing import Literal, Protocol

from httpx import AsyncClient, Response
from pydantic import BaseModel

from pyhyves.config import HYVES_AUTHORIZATION_URL, HYVES_CLIENT_ID, HYVES_TOKEN_URL

logger = logging.getLogger(__name__)

class TokenCredentials(BaseModel):
    """Credentials from an existing access token, e.g. from DevTools."""
    access_token: str


class PasswordCredentials(BaseModel):
    """Credentials for logging in with a username and password."""
    login_id: str
    password: str


Credentials = TokenCredentials | PasswordCredentials


class HyvesAuthException(RuntimeError):
    pass


class Auth(Protocol):
    async def get_new_token(self) -> str:
        """Acquire and return a fresh token."""
        ...


class TokenAuth:
    """Returns a constant token once (for example, intercepted from DevTools)"""

    def __init__(self, credentials: TokenCredentials) -> None:
        self._token = credentials.access_token
        self._expired = False

    async def get_new_token(self) -> str:
        if self._expired:
            raise HyvesAuthException("TokenAuth does not support refreshing tokens")
        self._expired = True

        return self._token


class RequestTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    userId: str
    token_type: Literal["Bearer"]


class PasswordAuth:
    def __init__(self, http: AsyncClient, credentials: PasswordCredentials) -> None:
        self._http = http
        self._login_id = credentials.login_id
        self._password = credentials.password

    async def get_new_token(self) -> str:
        token = await self._do_password_auth()
        logger.info("Successfully logged in")
        return token

    async def _do_password_auth(self) -> str:
        code_verifier, code_challenge = self._generate_code_challenge()

        authorize_response = await self._request_authorization_code(code_challenge)
        query_params = authorize_response.request.url.query.decode()
        parsed_params = urllib.parse.parse_qs(query_params)
        code = parsed_params["code"][0]

        token_response = await self._request_token(code_verifier, code)
        formatted_response = RequestTokenResponse.model_validate(token_response.json())

        return formatted_response.access_token

    async def _request_authorization_code(self, code_challenge: str) -> Response:
        logger.debug("Requesting authorization code with username and password")

        # The commented lines are sent by the Hyves web app, but seemingly not required
        return await self._http.post(
            HYVES_AUTHORIZATION_URL,
            data={
                "client_id": HYVES_CLIENT_ID,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "redirect_uri": "https://hyves.nl/auth",
                "response_mode": "query",
                "response_type": "code",
                "scope": "openid offline_access",
                "loginId": self._login_id,
                "password": self._password,
                # "captcha_token": "",
                # "drop_jkt": "",
                # "metaData.device.name": "",
                # "metaData.device.type": "",
                # "nonce": "",
                # "oauth_context": "",
                # "max_age": "",
                # "pendingIdPLinkId": "",
                # "prompt": "",
                # "state": "",
                # "tenantId": "",
                # "timezone": "",
                # "user_code": "",
                # "showPasswordField": "true",
                # "userVerifyingPlatformAuthenticatorAvailable": "false",
                # "rememberDevice": "true",
            },
            follow_redirects=True,
        )

    async def _request_token(self, code_verifier: str, code: str) -> Response:
        logger.debug("Requesting token from authorization code")
        return await self._http.post(
            HYVES_TOKEN_URL,
            data={
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": "https://hyves.nl/auth",
                "client_id": HYVES_CLIENT_ID,
                "code_verifier": code_verifier,
            },
        )

    @staticmethod
    def _generate_code_challenge() -> tuple[str, str]:
        """Generate a code verifier and code challenge for OAuth 2.0 PKCE."""
        code_verifier = secrets.token_urlsafe(96)[:128]
        hashed_verifier = hashlib.sha256(code_verifier.encode("ascii")).digest()
        encoded_verifier = base64.urlsafe_b64encode(hashed_verifier)
        code_challenge = encoded_verifier.decode("ascii").rstrip("=")
        return code_verifier, code_challenge