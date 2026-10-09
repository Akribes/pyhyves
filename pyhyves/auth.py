from __future__ import annotations

import logging
from asyncio import Lock
from typing import Any, assert_never
from urllib.parse import parse_qsl, urlsplit

from authlib.common.errors import AuthlibBaseError
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.httpx_client.oauth2_client import USE_CLIENT_DEFAULT
from pydantic import BaseModel

from pyhyves.config import (
    HYVES_AUTHORIZATION_URL,
    HYVES_CLIENT_ID,
    HYVES_REDIRECT_URL,
    HYVES_SCOPE,
    HYVES_TOKEN_URL,
)

logger = logging.getLogger(__name__)

# Length of the PKCE code verifier. The RFC allows 43 to 128 characters.
CODE_VERIFIER_LENGTH = 96


class TokenCredentials(BaseModel):
    """Credentials from an existing access token, e.g. from DevTools.

    This token is never refreshed, so it expires at the end of its lifetime. Use
    :class:`PasswordCredentials` for a session that keeps itself alive.
    """

    access_token: str


class PasswordCredentials(BaseModel):
    """Credentials for logging in with a username and password."""

    login_id: str
    password: str


Credentials = TokenCredentials | PasswordCredentials


class HyvesAuthException(RuntimeError):
    pass


class HyvesOAuth2Client(AsyncOAuth2Client):  # type: ignore[misc]
    """An OAuth 2.0 client for the Hyves API.

    This is an ``httpx2.AsyncClient`` subclass, so it doubles as the transport for
    :class:`pyhyves.api.client.HTTPClient`. Authlib takes care of attaching the
    ``Authorization`` header and of refreshing the access token before it expires.

    :param credentials: How to authenticate. ``None`` only allows public endpoints.
    :param client_kwargs: Extra keyword arguments for the underlying ``httpx2.AsyncClient``.
    """

    def __init__(self, credentials: Credentials | None = None, **client_kwargs: Any) -> None:
        match credentials:
            case None:
                login_id = password = None
            case PasswordCredentials():
                login_id = credentials.login_id
                password = credentials.password
            case TokenCredentials():
                login_id = password = None
            case _ as unreachable:
                assert_never(unreachable)

        self._login_id = login_id
        self._password = password
        # Serialises logins, so that concurrent requests only trigger a single one
        self._login_lock = Lock()

        super().__init__(
            client_id=HYVES_CLIENT_ID,
            code_challenge_method="S256",
            redirect_uri=HYVES_REDIRECT_URL,
            scope=HYVES_SCOPE,
            authorization_endpoint=HYVES_AUTHORIZATION_URL,
            token_endpoint=HYVES_TOKEN_URL,
            token_endpoint_auth_method="none",
            token=self._initial_token(credentials),
            **self._default_client_kwargs(client_kwargs),
        )

    @staticmethod
    def _default_client_kwargs(client_kwargs: dict[str, Any]) -> dict[str, Any]:
        return {"http2": True} | client_kwargs

    @staticmethod
    def _initial_token(credentials: Credentials | None) -> dict[str, Any] | None:
        """Seed the client with a token that never expires.

        A token without ``expires_at`` is treated as valid forever by authlib, which is
        what we want for a token that cannot be refreshed.
        """
        if isinstance(credentials, TokenCredentials):
            return {"access_token": credentials.access_token, "token_type": "Bearer"}
        return None

    @property
    def can_authenticate(self) -> bool:
        """Whether this client is able to authenticate at all."""
        return self._login_id is not None or self.token is not None

    async def request(
        self,
        method: str,
        url: Any,
        withhold_token: bool = False,
        auth: Any = USE_CLIENT_DEFAULT,
        **kwargs: Any,
    ) -> Any:
        """Send a request, logging in first if that has not happened yet."""
        # Authlib's own token requests pass an explicit auth, so they do not re-enter here
        if not withhold_token and auth is USE_CLIENT_DEFAULT and not self.token:
            if not self.can_authenticate:
                raise HyvesAuthException(
                    "This method requires authentication, but no credentials were provided"
                )
            await self._ensure_logged_in()

        try:
            return await super().request(method, url, withhold_token=withhold_token, auth=auth, **kwargs)
        except AuthlibBaseError as error:
            raise HyvesAuthException(f"Authentication failed: {error}") from error

    async def _ensure_logged_in(self) -> None:
        """Log in, unless another request got there first."""
        async with self._login_lock:
            if self.token:
                return
            await self._login()

    async def _login(self) -> None:
        """Log in with the configured username and password.

        This mimics the login flow from the web app, which uses OAuth 2.0 with PKCE. Normally, a client is sent to
        the authorization endpoint, which runs FusionAuth and returns a login form. Since we cannot receive the
        redirect, we (1) let authlib build the authorization URL with our credentials and code challenge, (2) POST
        it ourselves and follow its redirects, and (3) let authlib exchange the authorization code from the final
        redirect for an access and refresh token.
        """
        logger.debug("Requesting access token with username and password")

        try:
            code_verifier = generate_token(CODE_VERIFIER_LENGTH)
            authorization_url, state = self.create_authorization_url(
                HYVES_AUTHORIZATION_URL,
                code_verifier=code_verifier,
                response_mode="query",
                loginId=self._login_id,
                password=self._password,
            )

            response = await super().request(
                "POST",
                HYVES_AUTHORIZATION_URL,
                data=dict(parse_qsl(urlsplit(authorization_url).query)),
                follow_redirects=True,
                withhold_token=True,
            )

            await self.fetch_token(
                url=HYVES_TOKEN_URL,
                authorization_response=str(response.url),
                state=state,
                code_verifier=code_verifier,
            )
        except AuthlibBaseError as error:
            raise HyvesAuthException(f"Login failed: {error}") from error

        logger.info("Successfully logged in")