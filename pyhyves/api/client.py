import logging
from collections.abc import AsyncIterator, Mapping
from typing import Any, assert_never, overload

from pydantic import BaseModel, RootModel

from pyhyves.account import (
    Account,
    AccountPreview,
    AccountRef,
)
from pyhyves.api.schema import (
    Account as AccountPayload,
)
from pyhyves.api.schema import (
    ClientAccount as ClientAccountPayload,
)
from pyhyves.api.schema import (
    ClientAccountPatchParams,
    CommentCreateParams,
    DeleteResponse,
    FriendRequestCreateParams,
    FriendRequestsParams,
    GroupCreateParams,
    GroupJoinParams,
    GroupPatchParams,
    GroupUserOptionsUpdateParams,
    LikeCommentParams,
    LikePostParams,
    PostCreateParams,
    PublicUsersCount,
    UnlikeCommentParams,
    UnlikePostParams,
    WallPostApproveParams,
    WallPostRejectParams,
)
from pyhyves.api.schema import (
    Comment as CommentPayload,
)
from pyhyves.api.schema import (
    Friend as FriendPayload,
)
from pyhyves.api.schema import (
    FriendRequest as FriendRequestPayload,
)
from pyhyves.api.schema import (
    Group as GroupPayload,
)
from pyhyves.api.schema import (
    GroupMember as GroupMemberPayload,
)
from pyhyves.api.schema import (
    GroupPost as GroupPostPayload,
)
from pyhyves.api.schema import (
    GroupUserOptions as GroupUserOptionsPayload,
)
from pyhyves.api.schema import (
    PartialAccount as PartialAccountPayload,
)
from pyhyves.api.schema import (
    PartialGroup as PartialGroupPayload,
)
from pyhyves.api.schema import (
    Post as PostPayload,
)
from pyhyves.api.schema import (
    TimelineEntry as TimelineEntryPayload,
)
from pyhyves.api.schema import (
    TimelinePost as TimelinePostPayload,
)
from pyhyves.api.schema import (
    WallPost as WallPostPayload,
)
from pyhyves.auth import HyvesOAuth2Client
from pyhyves.config import BATCHED_REQUEST_LIMIT, HYVES_API_URL
from pyhyves.group import Group, GroupMember, GroupPreview, GroupRef
from pyhyves.post import (
    Comment,
    GroupPost,
    Post,
    PostRef,
    TimelinePost,
    WallPost,
)

logger = logging.getLogger(__name__)


class HyvesError(BaseModel):
    code: int
    title: str
    description: str
    type: str

class HyvesResponse(BaseModel):
    hasResult: bool
    errors: list[HyvesError]
    result: Any

class BatchedResult(BaseModel):
    items: list[Any]
    cursor: str | None
    hasNext: bool
    # limit: int
    # total: int | None

class HyvesAPIException(RuntimeError):
    """Een fout vanuit de Hyves-API."""

class HTTPClient:
    """Wrapper om `httpx2.AsyncClient` met authenticatie en validatie."""

    def __init__(self, client: HyvesOAuth2Client) -> None:
        self._client = client

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
        """Stuurt een request en valideert de respons.

        Args:
            endpoint: Het endpoint om aan te roepen.
            method: De HTTP-requestmethode.
            response_type: Het Pydantic-model om de respons mee te valideren.
            params: Query-parameters van de request.
            params_override: Query-parameters die de waarden uit `params`
                overschrijven.
            data: De body van de request als Pydantic-model.
            auth_required: Of de `Authorization`-header nodig is.

        Returns:
            De gevalideerde respons.

        Raises:
            HyvesAPIException: Als de Hyves-API een fout teruggeeft.
        """

        url = HYVES_API_URL + endpoint

        data_dump = data.model_dump(exclude_unset=True) if data else None
        params_dump = params.model_dump(exclude_unset=True) if params else None

        if params_override:
            params_dump = params_dump or {}
            params_dump.update(params_override)

        response = await self._client.request(
            method=method,
            url=url,
            withhold_token=not auth_required,
            params=params_dump,
            json=data_dump,
        )

        formatted = HyvesResponse.model_validate(response.json())

        if not formatted.hasResult:
            raise HyvesAPIException(f"Hyves API returned {len(formatted.errors)} error(s): {formatted.errors}")

        if formatted.errors:
            logger.warning(f"Got a result from the Hyves API, but also received errors: {formatted.errors}")

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
    ) -> AsyncIterator[T]:
        """Laadt items van een endpoint zodra ze nodig zijn, in batches.

        Sommige endpoints (reacties, groepen, etc.) geven hun items terug
        in pagina's. Deze methode geeft een iterator terug die steeds een nieuwe
        batch aanvraagt op het moment dat die nodig is.

        Args:
            endpoint: Het endpoint om de items van op te halen.
            response_type: Het type om de items mee te valideren.
            params: Query-parameters om mee te sturen. `limit` en `cursor` worden
                overschreven.
            batch_size: Het aantal items per batch.
            auth_required: Of de `Authorization`-header nodig is.

        Yields:
            De gevalideerde items.

        Raises:
            HyvesAPIException: Als de Hyves-API een fout teruggeeft.
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

            has_next = batch.hasNext
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
    """Definities van de API-endpoints en builders voor de Pyhyves-types."""

    def __init__(self, client: HyvesOAuth2Client) -> None:
        self._client = HTTPClient(client)

    # region Public endpoints

    async def public_get_user_count(self) -> PublicUsersCount:
        return await self._client.get(
            "/v1/public/users/count",
            response_type=PublicUsersCount,
            auth_required=False
        )

    # endregion

    # region Client account

    async def get_client_account(self) -> ClientAccountPayload:
        return await self._client.get("/v1/account/me", response_type=ClientAccountPayload)

    async def update_client_account(self, params: ClientAccountPatchParams) -> ClientAccountPayload:
        return await self._client.patch(
            "/v1/account/me",
            response_type=ClientAccountPayload,
            data=params,
        )

    def get_client_timeline(self, *, batch_size: int = BATCHED_REQUEST_LIMIT) -> AsyncIterator[TimelineEntryPayload]:
        return self._client.get_iter(
            "/v1/timeline", response_type=TimelineEntryPayload, batch_size=batch_size
        )

    # endregion

    # region Accounts

    async def get_account(self, account_id: int) -> AccountPayload:
        return await self._client.get(f"/v1/account/{account_id}", response_type=AccountPayload)

    # endregion

    # region Groups

    def get_sponsored_groups(
        self, *, batch_size: int = BATCHED_REQUEST_LIMIT
    ) -> AsyncIterator[GroupPayload]:
        return self._client.get_iter(
            "/v1/groups/sponsored", response_type=GroupPayload, batch_size=batch_size
        )

    def get_client_groups(
        self, *, batch_size: int = BATCHED_REQUEST_LIMIT
    ) -> AsyncIterator[GroupPayload]:
        return self._client.get_iter("/v1/groups", response_type=GroupPayload, batch_size=batch_size)

    async def get_group(self, group_id: int) -> GroupPayload:
        return await self._client.get(f"/v1/groups/{group_id}", response_type=GroupPayload)

    async def create_group(self, params: GroupCreateParams) -> GroupPayload:
        return await self._client.post("/v1/groups", response_type=GroupPayload, data=params)

    async def update_group(self, group_id: int, params: GroupPatchParams) -> GroupPayload:
        return await self._client.patch(f"/v1/groups/{group_id}", response_type=GroupPayload, data=params)

    async def delete_group(self, group_id: int) -> None:
        await self._client.delete(f"/v1/groups/{group_id}", response_type=DeleteResponse)

    def get_group_members(
        self, group_id: int, *, batch_size: int = BATCHED_REQUEST_LIMIT
    ) -> AsyncIterator[GroupMemberPayload]:
        return self._client.get_iter(
            f"/v1/groups/{group_id}/members", response_type=GroupMemberPayload, batch_size=batch_size
        )

    async def get_group_user_options(self, group_id: int) -> GroupUserOptionsPayload:
        return await self._client.get(f"/v1/groups/{group_id}/user-options", response_type=GroupUserOptionsPayload)

    async def update_group_user_options(self, group_id: int, params: GroupUserOptionsUpdateParams) -> GroupUserOptionsPayload:
        return await self._client.put(f"/v1/groups/{group_id}/user-options", response_type=GroupUserOptionsPayload, data=params)

    async def join_group(self, group_id: int, params: GroupJoinParams) -> GroupMemberPayload:
        return await self._client.post(f"/v1/groups/{group_id}/join", response_type=GroupMemberPayload, data=params)

    async def leave_group(self, group_id: int) -> None:
        await self._client.delete(f"/v1/groups/{group_id}/leave", response_type=DeleteResponse)

    # endregion

    # region Posts

    async def get_post(self, post_id: int) -> PostPayload:
        response_type = RootModel[PostPayload]
        payload = await self._client.get(f"/v1/posts/{post_id}", response_type=response_type)
        return payload.root

    async def create_timeline_post(self, params: PostCreateParams) -> TimelinePostPayload:
        return await self._client.post("/v1/posts", response_type=TimelinePostPayload, data=params)

    def get_wall_posts(
        self, account_id: int, *, batch_size: int = BATCHED_REQUEST_LIMIT
    ) -> AsyncIterator[WallPostPayload]:
        return self._client.get_iter(
            f"/v1/wall/{account_id}/posts", response_type=WallPostPayload, batch_size=batch_size
        )

    async def create_wall_post(self, account_id: int, params: PostCreateParams) -> WallPostPayload:
        return await self._client.post(f"/v1/wall/{account_id}/posts", response_type=WallPostPayload, data=params)

    async def approve_wall_post(self, post_id: int, params: WallPostApproveParams) -> WallPostPayload:
        return await self._client.post(f"/v1/wall/posts/{post_id}/approve", response_type=WallPostPayload, data=params)

    async def reject_wall_post(self, post_id: int, params: WallPostRejectParams) -> WallPostPayload:
        return await self._client.post(f"/v1/wall/posts/{post_id}/reject", response_type=WallPostPayload, data=params)

    def get_group_posts(
        self, group_id: int, *, batch_size: int = BATCHED_REQUEST_LIMIT
    ) -> AsyncIterator[GroupPostPayload]:
        return self._client.get_iter(
            f"/v1/groups/{group_id}/posts", response_type=GroupPostPayload, batch_size=batch_size
        )

    async def create_group_post(self, group_id: int, params: PostCreateParams) -> GroupPostPayload:
        return await self._client.post(f"/v1/groups/{group_id}/posts", response_type=GroupPostPayload, data=params)

    async def delete_post(self, post_id: int) -> None:
        await self._client.delete(f"/v1/posts/{post_id}", response_type=DeleteResponse)

    # endregion

    # region Comments

    def get_comments(
        self, post_id: int, *, batch_size: int = BATCHED_REQUEST_LIMIT
    ) -> AsyncIterator[CommentPayload]:
        return self._client.get_iter(
            f"/v1/posts/{post_id}/comments", response_type=CommentPayload, batch_size=batch_size
        )

    async def create_comment(self, post_id: int, params: CommentCreateParams) -> CommentPayload:
        return await self._client.post(f"/v1/posts/{post_id}/comments", response_type=CommentPayload, data=params)

    async def delete_comment(self, post_id: int, comment_id: int) -> None:
        await self._client.delete(f"/v1/posts/{post_id}/comments/{comment_id}", response_type=DeleteResponse)

    # endregion

    # region Likes

    async def like_post(self, post_id: int, params: LikePostParams) -> PostPayload:
        response_type = RootModel[PostPayload]
        payload = await self._client.post(f"/v1/posts/{post_id}/like", response_type=response_type, data=params)
        return payload.root

    async def unlike_post(self, post_id: int, params: UnlikePostParams) -> PostPayload:
        # Apparently, unlike the other DELETE endpoints, this endpoint returns the new post
        response_type = RootModel[PostPayload]
        payload = await self._client.delete(f"/v1/posts/{post_id}/like", params=params, response_type=response_type)
        return payload.root

    async def like_comment(self, comment_id: int, params: LikeCommentParams) -> CommentPayload:
        # The endpoint is /posts, not /comments for some reason
        return await self._client.post(f"/v1/posts/{comment_id}/like", response_type=CommentPayload, data=params)

    async def unlike_comment(self, comment_id: int, params: UnlikeCommentParams) -> CommentPayload:
        return await self._client.delete(f"/v1/posts/{comment_id}/like", params=params, response_type=CommentPayload)

    # endregion

    # region Friends

    def get_client_friends(
        self, *, batch_size: int = BATCHED_REQUEST_LIMIT
    ) -> AsyncIterator[FriendPayload]:
        return self._client.get_iter("/v1/friends", response_type=FriendPayload, batch_size=batch_size)

    async def delete_friend(self, account_id: int) -> None:
        await self._client.delete(f"/v1/friends/{account_id}", response_type=DeleteResponse)

    def get_client_friend_requests(
        self,
        params: FriendRequestsParams,
        *,
        batch_size: int = 4,
    ) -> AsyncIterator[FriendRequestPayload]:
        return self._client.get_iter(
            "/v1/friends/requests", response_type=FriendRequestPayload, params=params, batch_size=batch_size
        )

    async def create_friend_request(self, params: FriendRequestCreateParams) -> FriendRequestPayload:
        return await self._client.post("/v1/friends/requests", response_type=FriendRequestPayload, data=params)

    async def delete_friend_request(self, request_id: int) -> None:
        await self._client.delete(f"/v1/friends/requests/{request_id}", response_type=DeleteResponse)

    async def accept_friend_request(self, request_id: int) -> FriendRequestPayload:
        return await self._client.post(f"/v1/friends/requests/{request_id}/accept", response_type=FriendRequestPayload)

    async def deny_friend_request(self, request_id: int) -> FriendRequestPayload:
        return await self._client.post(f"/v1/friends/requests/{request_id}/deny", response_type=FriendRequestPayload)

    # endregion

    # region Builders

    def build_account_ref(self, account_id: int) -> AccountRef:
        return AccountRef(self, account_id)

    def build_account_preview(self, payload: PartialAccountPayload | GroupMemberPayload) -> AccountPreview:
        match payload:
            case PartialAccountPayload():
                return AccountPreview(self, payload)
            case GroupMemberPayload():
                return AccountPreview(
                    self, PartialAccountPayload(
                        profileId=payload.userId,
                        name=payload.name,
                        firstName=payload.firstName,
                        middleName=payload.middleName,
                        lastName=payload.lastName,
                        imageUrl=payload.image,
                        bannerUrl=payload.banner,
                    )
                )
            case _ as unreachable:
                assert_never(unreachable)

    def build_account(self, payload: AccountPayload) -> Account:
        return Account(self, payload)

    def build_group_ref(self, group_id: int) -> GroupRef:
        return GroupRef(self, group_id)

    def build_group_preview(self, payload: PartialGroupPayload) -> GroupPreview:
        return GroupPreview(self, payload)

    def build_group(self, payload: GroupPayload) -> Group:
        return Group(self, payload)

    def build_group_member(self, payload: GroupMemberPayload) -> GroupMember:
        return GroupMember(self, payload)

    def build_post_ref(self, post_id: int) -> PostRef:
        return PostRef(self, post_id)

    @overload
    def build_post(self, payload: GroupPostPayload) -> GroupPost: ...

    @overload
    def build_post(self, payload: TimelinePostPayload) -> TimelinePost: ...

    @overload
    def build_post(self, payload: WallPostPayload) -> WallPost: ...

    @overload
    def build_post(self, payload: PostPayload) -> Post: ...

    def build_post(self, payload: PostPayload) -> Post:
        match payload:
            case GroupPostPayload():
                return GroupPost(self, payload)
            case TimelinePostPayload():
                return TimelinePost(self, payload)
            case WallPostPayload():
                return WallPost(self, payload)
            case _ as unreachable:
                assert_never(unreachable)

    def build_comment(self, payload: CommentPayload) -> Comment:
        return Comment(self, payload)

    # endregion
