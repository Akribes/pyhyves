from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, NewType

from pyhyves.api.schema import (
    Group as GroupPayload,
)
from pyhyves.api.schema import (
    GroupJoinParams,
    GroupUserOptionsUpdateParams,
    PostCreateParams,
)
from pyhyves.api.schema import (
    GroupMember as GroupMemberPayload,
)
from pyhyves.api.schema import (
    PartialGroup as PartialGroupPayload,
)

if TYPE_CHECKING:
    from pyhyves.api.client import HyvesClient
    from pyhyves.post import GroupPost

@dataclass(frozen=True, slots=True)
class GroupUserOptions:
    timeline: bool
    friends_activity: bool
    notifications: bool

class GroupMember:
    def __init__(self, client: HyvesClient, payload: GroupMemberPayload):
        self._client = client
        self.group = client.build_group_ref(payload.groupId)
        self.account = client.build_account_preview(payload)
        self.role = payload.role
        self.is_blocked_from_group = payload.isBlockedFromGroup


GroupId = NewType("GroupId", int)

class GroupRef:
    """A reference to a group. Upgrade to a full ``Group`` with ``fetch``."""

    def __init__(self, client: HyvesClient, group_id: int) -> None:
        self._client = client
        self.id = GroupId(group_id)

    async def fetch(self) -> Group:
        payload = await self._client.get_group(self.id)
        return self._client.build_group(payload)

    async def join(self) -> None:
        await self._client.join_group(self.id, params=GroupJoinParams())

    async def leave(self) -> None:
        await self._client.leave_group(self.id)

    async def get_members(self) -> AsyncIterator[GroupMember]:
        async for payload in self._client.get_group_members(self.id):
            yield self._client.build_group_member(payload)

    async def get_posts(self) -> AsyncIterator[GroupPost]:
        async for payload in self._client.get_group_posts(self.id):
            yield self._client.build_post(payload)

    async def create_post(self, content: str, link: str | None = None) -> None:
        params = PostCreateParams(content=content, link=link)
        await self._client.create_group_post(self.id, params=params)

    async def get_user_options(self) -> GroupUserOptions:
        payload = await self._client.get_group_user_options(self.id)
        return GroupUserOptions(
            payload.timeline,
            payload.friendsActivity,
            payload.notifications,
        )

    async def update_user_options(self, options: GroupUserOptions) -> None:
        params = GroupUserOptionsUpdateParams(
            timeline=options.timeline,
            friendsActivity=options.friends_activity,
            notifications=options.notifications,
        )
        await self._client.update_group_user_options(self.id, params=params)

    # async def update(self, ...): ...

    async def delete(self) -> None:
        await self._client.delete_group(self.id)


class GroupPreview(GroupRef):
    """A preview of a group. Upgrade to a full ``Group`` with ``fetch``."""

    def __init__(self, client: HyvesClient, payload: PartialGroupPayload) -> None:
        self._client = client
        self.id = GroupId(payload.id)
        self.name = payload.name
        self.image_url = payload.imageUrl
        self.banner_url = payload.bannerUrl


class Group(GroupPreview):
    """A group's public profile."""

    def __init__(self, client: HyvesClient, payload: GroupPayload) -> None:
        self._client = client
        self.id = GroupId(payload.id)
        self.name = payload.name
        self.image_url = payload.image
        self.banner_url = payload.banner
        self.description = payload.description
        self.owner = client.build_account_ref(payload.ownerUserId)
        self.role_to_post = payload.roleToPost
        self.likes_on_post_enabled = payload.likesOnPostEnabled
        self.comments_on_post_enabled = payload.commentsOnPostEnabled
        self.member_count = payload.memberCount
        self.is_owner = payload.isOwner
        self.background_html = payload.backgroundHtml
        self.member_role = payload.memberRole
        self.can_post = payload.canPost
