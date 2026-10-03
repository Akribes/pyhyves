import logging
from collections.abc import AsyncGenerator, Mapping
from typing import Any

from httpx import AsyncClient, Response
from pydantic import BaseModel, ConfigDict, alias_generators

from pyhyves import HyvesAuthException
from pyhyves.auth import (
    Auth,
)
from pyhyves.config import BATCHED_REQUEST_LIMIT, HYVES_API_URL

logger = logging.getLogger(__name__)

class CamelCaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=alias_generators.to_camel)


class _HyvesResponse(CamelCaseModel):
    has_result: bool
    errors: list[Any]
    result: Any


class _BatchedResult(CamelCaseModel):
    items: list[Any]
    cursor: str | None
    has_next: bool
    # limit: int
    # total: int | None


class HyvesAPIException(RuntimeError):
    """Raised when the Hyves API returns errors."""


class HyvesClient:
    def __init__(self, *, auth: Auth | None = None, client: AsyncClient | None = None, ) -> None:
        self._client = client or AsyncClient()
        self._auth = auth
        self._token: str | None = None

    async def get[T: BaseModel](
        self,
        endpoint: str,
        *,
        response_type: type[T],
        params: Mapping[str, str] | None = None,
        auth_required: bool = True
    ) -> T:
        """Do a GET request and validate the response.

        :param endpoint: API endpoint
        :param response_type: Pydantic model to validate the response against
        :param params: Query parameters to send with the request
        :param auth_required: Whether to include the Authorization header
        :return: Validated response
        """
        response = await self.request(
            method="GET",
            endpoint=endpoint,
            params=params,
            auth_required=auth_required
        )
        formatted = _HyvesResponse.model_validate(response.json())

        if not formatted.has_result:
            raise HyvesAPIException(f"Hyves API returned {len(formatted.errors)} error(s): {formatted.errors}")

        if formatted.errors:
            logger.warning(f"Got a result, but also received errors: {formatted.errors}")

        result = response_type.model_validate(formatted.result)
        return result

    async def get_iter[T: BaseModel](
        self,
        endpoint: str,
        *,
        response_type: type[T],
        params: Mapping[str, str] | None = None,
        auth_required: bool = True
    ) -> AsyncGenerator[T]:
        """Lazily load items from an endpoint.

        Some endpoints (comments, groups, etc.) return a list of items in pages. This method returns an iterator that
        requests batches of items as needed.

        :param endpoint: The endpoint to load items from
        :param response_type: The type to validate against
        :param params: Query parameters to send with the request. ``limit`` and ``cursor`` are overwritten.
        :param auth_required: Whether to include the Authorization header
        :return: Validated items
        """

        params = {**params} if params else {}
        params["limit"] = str(BATCHED_REQUEST_LIMIT)
        params.pop("cursor", None)
        has_next = True

        while has_next:
            batch = await self.get(
                endpoint=endpoint,
                response_type=_BatchedResult,
                params=params,
                auth_required=auth_required,
            )

            for x in batch.items:
                yield response_type.model_validate(x)

            has_next = batch.has_next
            params["cursor"] = batch.cursor

    async def request(
        self,
        endpoint: str,
        *,
        method: str,
        params: Mapping[str, str] | None,
        auth_required: bool = True
    ) -> Response:
        """Wrapper around httpx.request with auth.

        If authentication is needed, the token is refreshed if necessary.

        :param method: HTTP request method
        :param endpoint: Endpoint
        :param params: Request parameters
        :param auth_required: Whether to include Authorization header
        :return: An httpx Response object
        """

        url = HYVES_API_URL + endpoint
        headers: dict[str, str] = {}

        if auth_required:
            if not self._auth:
                raise HyvesAuthException("No credentials provided but auth_required is True")

            if not self._token:
                self._token = await self._auth.get_new_token()
            headers["Authorization"] = f"Bearer {self._token}"

        return await self._client.request(
            method=method,
            url=url,
            headers=headers,
            params=params
        )
