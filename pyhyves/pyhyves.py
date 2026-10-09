from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Self, assert_never

import httpx

from pyhyves.api.client import HyvesClient
from pyhyves.api.schema import (
    GroupCreateParams,
    GroupRole,
    GroupVisibility,
    PostCreateParams,
    WallPostApproveParams,
    WallPostRejectParams,
)
from pyhyves.auth import (
    Auth,
    Credentials,
    PasswordAuth,
    PasswordCredentials,
    TokenAuth,
    TokenCredentials,
)

if TYPE_CHECKING:
    from pyhyves.account import Account, AccountId, AccountRef
    from pyhyves.group import Group, GroupId, GroupRef
    from pyhyves.post import Post, PostId, PostRef

logger = logging.getLogger(__name__)


class Pyhyves:
    """An authenticated session against the Hyves API.

    :param credentials: How to authenticate. ``None`` only works for the public endpoints.
    :param http: An existing HTTP client to use instead of creating one. When passed, the caller stays responsible
        for closing it.
    """

    def __init__(
        self,
        credentials: Credentials | None = None,
        *,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_http = http is None
        self._http = httpx.AsyncClient() if http is None else http
        self._client = self._build_client(credentials=credentials, http=self._http)

    @staticmethod
    def _build_client(credentials: Credentials | None, http: httpx.AsyncClient) -> HyvesClient:
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

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying HTTP client, unless it was injected."""
        if self._owns_http:
            await self._http.aclose()

    # region Public

    async def public_get_user_count(self) -> int:
        """Get the total number of registered users. Does not need auth."""
        return (await self._client.public_get_user_count()).count

    # endregion

    # region Account

    def get_account_ref(self, account_id: AccountId) -> AccountRef:
        return self._client.build_account_ref(account_id)

    async def get_account(self, account_id: AccountId) -> Account:
        """Get a user's public profile."""
        return await self.get_account_ref(account_id).fetch()

    # endregion

    # region Groups

    def get_group_ref(self, group_id: GroupId) -> GroupRef:
        """Return a reference to a group, without fetching it."""
        return self._client.build_group_ref(group_id)

    async def get_group(self, group_id: GroupId) -> Group:
        """Get a group by id."""
        return await self.get_group_ref(group_id).fetch()

    async def create_group(
        self,
        name: str,
        description: str,
        *,
        role_to_post: GroupRole = GroupRole.MEMBER,
        likes_on_post_enabled: bool = True,
    ) -> Group:
        """Create a public group owned by you."""
        params = GroupCreateParams(
            id=0,
            name=name,
            description=description,
            visibility=GroupVisibility.PUBLIC,
            roleToPost=role_to_post,
            likesOnPostEnabled=likes_on_post_enabled,
            deleteImage=False,
            deleteBanner=False,
        )
        payload = await self._client.create_group(params)
        return self._client.build_group(payload)

    async def get_client_groups(self) -> AsyncIterator[Group]:
        """Iterate over the groups you are a member of."""
        async for payload in self._client.get_client_groups():
            yield self._client.build_group(payload)

    async def get_sponsored_groups(self) -> AsyncIterator[Group]:
        """Iterate over the sponsored groups."""
        async for payload in self._client.get_sponsored_groups():
            yield self._client.build_group(payload)

    # endregion

    # region Posts

    def get_post_ref(self, post_id: PostId) -> PostRef:
        """Return a reference to a post, without fetching it."""
        return self._client.build_post_ref(post_id)

    async def get_post(self, post_id: PostId) -> Post:
        """Get a post by id."""
        return await self.get_post_ref(post_id).fetch()

    async def create_timeline_post(self, content: str, *, link: str | None = None) -> None:
        """Post to your own timeline."""
        await self._client.create_timeline_post(
            PostCreateParams(content=content, link=link)
        )

    async def approve_wall_post(self, post_id: PostId) -> None:
        """Approve a pending post on your wall."""
        await self._client.approve_wall_post(post_id, WallPostApproveParams())

    async def reject_wall_post(self, post_id: PostId) -> None:
        """Reject a pending post on your wall."""
        await self._client.reject_wall_post(post_id, WallPostRejectParams())

    # endregion
