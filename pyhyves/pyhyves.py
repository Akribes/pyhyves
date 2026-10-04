import logging
from typing import assert_never

import httpx

from pyhyves.auth import (
    Auth,
    Credentials,
    PasswordAuth,
    PasswordCredentials,
    TokenAuth,
    TokenCredentials,
)
from pyhyves.client import HyvesClient

logger = logging.getLogger(__name__)


class Pyhyves:
    """Client for the Hyves API."""

    def __init__(self, credentials: Credentials | None = None) -> None:
        self._client = self._build_client(credentials=credentials)

    @staticmethod
    def _build_client(credentials: Credentials | None) -> HyvesClient:
        http = httpx.AsyncClient()
        auth: Auth | None
        match credentials:
            case None:
                logger.warning("No credentials provided, most endpoints won't work")
                auth = None
            case PasswordCredentials():
                auth = PasswordAuth(http, credentials)
            case TokenCredentials():
                auth = TokenAuth(credentials)
            case _ as unreachable:
                assert_never(unreachable)
        return HyvesClient(auth=auth, client=http)