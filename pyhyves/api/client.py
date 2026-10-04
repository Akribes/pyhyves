import logging
from collections.abc import AsyncGenerator, Mapping
from typing import Any

from httpx import AsyncClient
from pydantic import BaseModel, ConfigDict, alias_generators

from pyhyves.api.schema import (
    Account,
    ClientAccount,
    ClientAccountPatchParams,
    Comment,
    CommentCreateParams,
    DeleteResponse,
    Friend,
    FriendRequest,
    FriendRequestCreateParams,
    FriendRequestsParams,
    Group,
    GroupCreateParams,
    GroupJoinParams,
    GroupMember,
    GroupPatchParams,
    GroupUserOptions,
    GroupUserOptionsUpdateParams,
    LikeCommentParams,
    LikePostParams,
    Post,
    PostCreateParams,
    PublicUsersCount,
    TimelineEntry,
    UnlikeCommentParams,
    UnlikePostParams,
)
from pyhyves.auth import (
    Auth,
    HyvesAuthException,
)
from pyhyves.config import BATCHED_REQUEST_LIMIT, HYVES_API_URL

logger = logging.getLogger(__name__)

class CamelCaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=alias_generators.to_camel)


class HyvesError(BaseModel):
    code: int
    title: str
    description: str
    type: str

class HyvesResponse(CamelCaseModel):
    has_result: bool
    errors: list[HyvesError]
    result: Any

class BatchedResult(CamelCaseModel):
    items: list[Any]
    cursor: str | None
    has_next: bool
    # limit: int
    # total: int | None

class HyvesAPIException(RuntimeError):
    """Raised when the Hyves API returns errors."""

class HTTPClient:
    """``httpx.AsyncClient`` wrapper with auth and response validation."""

    def __init__(self, *, auth: Auth | None = None, client: AsyncClient | None = None, ) -> None:
        self._client = client or AsyncClient()
        self._auth = auth
        self._token: str | None = None


    async def request[T: BaseModel](
        self,
        endpoint: str,
        *,
        method: str,
        response_type: type[T],
        params: BaseModel | None = None,
        params_override: Mapping[str, str] | None = None,
        data: BaseModel | None = None,
        auth_required: bool = True
    ) -> T:
        """Wrapper around httpx.request with auth.

        If authentication is needed, the token is refreshed if necessary.

        :param params_override:
        :param endpoint: Endpoint
        :param method: HTTP request method
        :param response_type: Pydantic model to validate the response against
        :param params: Request parameters
        :param params_override: Query parameters overwritten in the Pydantic model
        :param data: Request JSON body
        :param auth_required: Whether to include Authorization header
        :return: Validated response
        """

        url = HYVES_API_URL + endpoint
        headers: dict[str, str] = {}

        if auth_required:
            if not self._auth:
                raise HyvesAuthException("No credentials provided but auth_required is True")

            if not self._token:
                self._token = await self._auth.get_new_token()
            headers["Authorization"] = f"Bearer {self._token}"

        data_dump = data.model_dump(exclude_unset=True) if data else None
        params_dump = params.model_dump(exclude_unset=True) if params else None

        if params_override:
            params_dump = params_dump or {}
            params_dump.update(params_override)

        response = await self._client.request(
            method=method,
            url=url,
            headers=headers,
            params=params_dump,
            json=data_dump,
        )

        formatted = HyvesResponse.model_validate(response.json())

        if not formatted.has_result:
            raise HyvesAPIException(f"Hyves API returned {len(formatted.errors)} error(s): {formatted.errors}")

        if formatted.errors:
            logger.warning(f"Got a result, but also received errors: {formatted.errors}")

        result = response_type.model_validate(formatted.result)
        return result

    async def get[T: BaseModel](
        self,
        endpoint: str,
        *,
        response_type: type[T],
        params: BaseModel | None = None,
        auth_required: bool = True
    ) -> T:
        """Do a GET request and validate the response.

        :param endpoint: API endpoint
        :param response_type: Pydantic model to validate the response against
        :param params: Query parameters to send with the request
        :param auth_required: Whether to include the Authorization header
        :return: Validated response
        """
        return await self.request(
            endpoint=endpoint,
            method="GET",
            response_type=response_type,
            params=params,
            auth_required=auth_required,
        )

    async def get_iter[T: BaseModel](
        self,
        endpoint: str,
        *,
        response_type: type[T],
        params: BaseModel | None = None,
        batch_size: int = BATCHED_REQUEST_LIMIT,
        auth_required: bool = True
    ) -> AsyncGenerator[T]:
        """Lazily load items from an endpoint.

        Some endpoints (comments, groups, etc.) return a list of items in pages. This method returns an iterator that
        requests batches of items as needed.

        :param endpoint: The endpoint to load items from
        :param response_type: The type to validate against
        :param params: Query parameters to send with the request. ``limit`` and ``cursor`` are overwritten.
        :param auth_required: Whether to include the Authorization header
        :param batch_size: Number of items to request per batch
        :return: Validated items
        """

        params_override = {"limit": str(batch_size)}
        has_next = True

        while has_next:
            batch = await self.request(
                endpoint=endpoint,
                method="GET",
                response_type=BatchedResult,
                params=params,
                params_override=params_override,
                auth_required=auth_required,
            )

            for x in batch.items:
                yield response_type.model_validate(x)

            has_next = batch.has_next
            if batch.cursor:
                params_override["cursor"] = batch.cursor
            else:
                params_override.pop("cursor", None)

    async def patch[T: BaseModel](
        self,
        endpoint: str,
        *,
        response_type: type[T],
        data: BaseModel | None = None,
        auth_required: bool = True
    ) -> T:
        return await self.request(
            method="PATCH",
            endpoint=endpoint,
            response_type=response_type,
            data=data,
            auth_required=auth_required
        )

    async def put[T: BaseModel](
        self,
        endpoint: str,
        *,
        response_type: type[T],
        data: BaseModel | None = None,
        auth_required: bool = True
    ) -> T:
        return await self.request(
            method="PUT",
            endpoint=endpoint,
            response_type=response_type,
            data=data,
            auth_required=auth_required
        )

    async def post[T: BaseModel](
        self,
        endpoint: str,
        *,
        response_type: type[T],
        data: BaseModel | None = None,
        auth_required: bool = True
    ) -> T:
        return await self.request(
            endpoint=endpoint,
            method="POST",
            response_type=response_type,
            data=data,
            auth_required=auth_required,
        )

    async def delete[T: BaseModel](
        self,
        endpoint: str,
        *,
        params: BaseModel | None = None,
        response_type: type[T],
        auth_required: bool = True
    ) -> T:
        return await self.request(
            endpoint=endpoint,
            method="DELETE",
            params=params,
            response_type=response_type,
            auth_required=auth_required,
        )

class HyvesClient:
    """Methods for accessing API endpoints."""

    def __init__(self, *, auth: Auth | None = None, client: AsyncClient | None = None) -> None:
        self._client = HTTPClient(auth=auth, client=client)

    # region Public endpoints

    async def public_get_user_count(self) -> PublicUsersCount:
        return await self._client.get(
            "/v1/public/users/count",
            response_type=PublicUsersCount,
            auth_required=False
        )

    # endregion

    # region Client account

    async def get_client_account(self) -> ClientAccount:
        return await self._client.get("/v1/account/me", response_type=ClientAccount)

    async def update_client_account(self, params: ClientAccountPatchParams) -> ClientAccount:
        return await self._client.patch(
            "/v1/account/me",
            response_type=ClientAccount,
            data=params,  # TODO check
        )

    def get_client_timeline(self) -> AsyncGenerator[TimelineEntry]:
        return self._client.get_iter("/v1/timeline", response_type=TimelineEntry)

    # endregion

    # region Accounts

    async def get_account(self, account_id: int) -> Account:
        return await self._client.get(f"/v1/account/{account_id}", response_type=Account)

    # endregion

    # region Groups

    def get_sponsored_groups(self) -> AsyncGenerator[Group]:
        return self._client.get_iter("/v1/groups/sponsored", response_type=Group)

    def get_client_groups(self) -> AsyncGenerator[Group]:
        return self._client.get_iter("/v1/groups", response_type=Group)

    async def get_group(self, group_id: int) -> Group:
        return await self._client.get(f"/v1/groups/{group_id}", response_type=Group)

    async def create_group(self, params: GroupCreateParams) -> Group:
        return await self._client.post("/v1/groups", response_type=Group, data=params)

    async def update_group(self, group_id: int, params: GroupPatchParams) -> Group:
        return await self._client.patch(f"/v1/groups/{group_id}", response_type=Group, data=params)

    async def delete_group(self, group_id: int) -> None:
        await self._client.delete(f"/v1/groups/{group_id}", response_type=DeleteResponse)

    def get_group_members(self, group_id: int) -> AsyncGenerator[GroupMember]:
        return self._client.get_iter(f"/v1/groups/{group_id}/members", response_type=GroupMember)

    async def get_group_user_options(self, group_id: int) -> GroupUserOptions:
        return await self._client.get(f"/v1/groups/{group_id}/user-options", response_type=GroupUserOptions)

    async def update_group_user_options(self, group_id: int, params: GroupUserOptionsUpdateParams) -> GroupUserOptions:
        return await self._client.put(f"/v1/groups/{group_id}/user-options", response_type=GroupUserOptions, data=params)

    async def join_group(self, group_id: int, params: GroupJoinParams) -> GroupMember:
        return await self._client.post(f"/v1/groups/{group_id}/join", response_type=GroupMember, data=params)

    async def leave_group(self, group_id: int) -> None:
        await self._client.delete(f"/v1/groups/{group_id}/leave", response_type=DeleteResponse)

    # endregion

    # region Posts

    async def get_post(self, post_id: int) -> Post:
        return await self._client.get(f"/v1/posts/{post_id}", response_type=Post)

    async def create_timeline_post(self, params: PostCreateParams) -> Post:
        return await self._client.post("/v1/posts", response_type=Post, data=params)

    def get_wall_posts(self, account_id: int) -> AsyncGenerator[Post]:
        return self._client.get_iter(f"/v1/wall/{account_id}/posts", response_type=Post)

    async def create_wall_post(self, account_id: int, params: PostCreateParams) -> Post:
        return await self._client.post(f"/v1/wall/{account_id}/posts", response_type=Post, data=params)

    async def approve_wall_post(self, post_id: int, params: PostCreateParams) -> Post:
        return await self._client.post(f"/v1/wall/posts/{post_id}/approve", response_type=Post, data=params)

    async def reject_wall_post(self, post_id: int, params: PostCreateParams) -> Post:
        return await self._client.post(f"/v1/wall/posts/{post_id}/reject", response_type=Post, data=params)

    def get_group_posts(self, group_id: int) -> AsyncGenerator[Post]:
        return self._client.get_iter(f"/v1/groups/{group_id}/posts", response_type=Post)

    async def create_group_post(self, group_id: int, params: PostCreateParams) -> Post:
        return await self._client.post(f"/v1/groups/{group_id}/posts", response_type=Post, data=params)

    async def delete_post(self, post_id: int) -> None:
        await self._client.delete(f"/v1/posts/{post_id}", response_type=DeleteResponse)

    # endregion

    # region Comments

    def get_comments(self, post_id: int) -> AsyncGenerator[Comment]:
        return self._client.get_iter(f"/v1/posts/{post_id}/comments", response_type=Comment)

    async def create_comment(self, post_id: int, params: CommentCreateParams) -> Comment:
        return await self._client.post(f"/v1/posts/{post_id}/comments", response_type=Comment, data=params)

    async def delete_comment(self, post_id: int, comment_id: int) -> None:
        await self._client.delete(f"/v1/posts/{post_id}/comments/{comment_id}", response_type=DeleteResponse)

    # endregion

    # region Likes

    async def like_post(self, post_id: int, params: LikePostParams) -> Post:
        return await self._client.post(f"/v1/posts/{post_id}/like", response_type=Post, data=params)

    async def unlike_post(self, post_id: int, params: UnlikePostParams) -> None:
        # Apparently, unlike the other DELETE endpoints, this endpoint returns the new post
        await self._client.delete(f"/v1/posts/{post_id}/like", params=params, response_type=Post)

    async def like_comment(self, comment_id: int, params: LikeCommentParams) -> Comment:
        # The endpoint is /posts, not /comments for some reason
        return await self._client.post(f"/v1/posts/{comment_id}/like", response_type=Comment, data=params)

    async def unlike_comment(self, comment_id: int, params: UnlikeCommentParams) -> None:
        await self._client.delete(f"/v1/posts/{comment_id}/like", params=params, response_type=Comment)

    # endregion

    # region Friends

    def get_client_friends(self) -> AsyncGenerator[Friend]:
        return self._client.get_iter("/v1/friends", response_type=Friend)

    async def delete_friend(self, account_id: int) -> None:
        await self._client.delete(f"/v1/friends/{account_id}", response_type=DeleteResponse)

    def get_client_friend_requests(self, params: FriendRequestsParams) -> AsyncGenerator[FriendRequest]:
        return self._client.get_iter("/v1/friends/requests", response_type=FriendRequest, params=params, batch_size=4)

    async def create_friend_request(self, params: FriendRequestCreateParams) -> FriendRequest:
        return await self._client.post("/v1/friends/requests", response_type=FriendRequest, data=params)

    async def delete_friend_request(self, request_id: int) -> None:
        await self._client.delete(f"/v1/friends/requests/{request_id}", response_type=DeleteResponse)

    async def accept_friend_request(self, request_id: int) -> FriendRequest:
        return await self._client.post(f"/v1/friends/requests/{request_id}/accept", response_type=FriendRequest)

    async def deny_friend_request(self, request_id: int) -> FriendRequest:
        return await self._client.post(f"/v1/friends/requests/{request_id}/deny", response_type=FriendRequest)

    # endregion
