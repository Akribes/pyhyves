from __future__ import annotations

import logging
from asyncio import Lock
from dataclasses import dataclass
from typing import Any, assert_never
from urllib.parse import parse_qsl, urlsplit

from authlib.common.errors import AuthlibBaseError
from authlib.common.security import generate_token
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.integrations.httpx_client.oauth2_client import USE_CLIENT_DEFAULT

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


@dataclass(frozen=True)
class TokenCredentials:
    """Inloggegevens op basis van een bestaand access token, bijvoorbeeld uit DevTools.

    Het token wordt niet ververst en vervalt na een uur.
    """

    access_token: str

@dataclass(frozen=True)
class PasswordCredentials:
    """Een gebruikersnaam en wachtwoord."""

    login_id: str
    password: str


class HyvesAuthException(RuntimeError):
    pass


class HyvesOAuth2Client(AsyncOAuth2Client):  # type: ignore[misc]
    """Een OAuth 2.0-client voor de Hyves API.

    Dit is een subclass van `httpx2.AsyncClient` en wordt door `pyhyves.api.client.HTTPClient` gebruikt. Authlib voegt
    de `Authorization`-header toe aan requests en ververst automatisch tokens.

    Args:
        credentials: Inloggegevens
        client_kwargs: Extra kwargs voor de onderliggende `httpx2.AsyncClient`
    """

    def __init__(self, credentials: PasswordCredentials | TokenCredentials | None = None, **client_kwargs: Any) -> None:
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
    def _initial_token(credentials: PasswordCredentials | TokenCredentials | None) -> dict[str, Any] | None:
        """Voorziet de client van een token dat nooit verloopt.

        Authlib behandelt een token zonder `expires_at` als altijd geldig, en als we een `TokenCredentials` hebben
        wilen we dat.
        """
        if isinstance(credentials, TokenCredentials):
            return {"access_token": credentials.access_token, "token_type": "Bearer"}
        return None

    @property
    def can_authenticate(self) -> bool:
        """Of deze client op enige manier kan authenticeren."""
        return self._login_id is not None or self.token is not None

    async def request(
        self,
        method: str,
        url: Any,
        withhold_token: bool = False,
        auth: Any = USE_CLIENT_DEFAULT,
        **kwargs: Any,
    ) -> Any:
        """Stuurt een request, logt eerst in als dat nog niet is gebeurd.

        Raises:
            HyvesAuthException: Als er geen inloggegevens zijn meegegeven, of als het inloggen mislukt.
        """
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
        """Logt in, tenzij een andere request daar eerder was."""
        async with self._login_lock:
            if self.token:
                return
            await self._login()

    async def _login(self) -> None:
        """Logt in met een gebruikersnaam en wachtwoord.

        Doet zich voor als de webapp. Werkt met OAuth 2.0 met PKCE. Normaal gesproken logt de gebruiker in door naar de
        URL gegenereerd door Authlib te gaan, maar omdat we de redirect_uri niet kunnen veranderen maken we hier gewoon
        zelf de request die de browser normaal zou maken. Vervolgens vraagt authlib weer een access token aan.
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