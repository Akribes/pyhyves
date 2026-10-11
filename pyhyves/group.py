from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, NewType

from pyhyves.api.schema import (
    Group as GroupPayload,
)
from pyhyves.api.schema import (
    GroupJoinParams,
    GroupPatchParams,
    GroupRole,
    GroupUserOptionsUpdateParams,
    PostCreateParams,
)
from pyhyves.api.schema import (
    GroupMember as GroupMemberPayload,
)
from pyhyves.api.schema import (
    PartialGroup as PartialGroupPayload,
)
from pyhyves.util import KEEP_CURRENT

if TYPE_CHECKING:
    from pyhyves.account import AccountPreview, AccountRef
    from pyhyves.api.client import HyvesClient
    from pyhyves.post import GroupPost

@dataclass(frozen=True, slots=True)
class GroupUserOptions:
    """Gebruikersvoorkeuren voor een Hyve, uit het menu "Voorkeuren" van een Hyve."""

    timeline: bool
    """Toon activiteiten in activiteitentijdlijn"""

    friends_activity: bool
    """Toon activiteiten van vrienden"""

    notifications: bool
    """Notificaties"""

class GroupMember:
    """Een lidmaatschap van een Hyve."""

    group: GroupRef
    """De Hyve waarin deze lid is."""

    account: AccountPreview
    """Het lid zelf."""

    role: GroupRole
    """De rol van het lid."""

    is_blocked_from_group: bool

    def __init__(self, client: HyvesClient, payload: GroupMemberPayload):
        self._client = client
        self.group = client.build_group_ref(payload.groupId)
        self.account = client.build_account_preview(payload)
        self.role = payload.role
        self.is_blocked_from_group = payload.isBlockedFromGroup


GroupId = NewType("GroupId", int)
"""Een `NewType` van `int` voor Hyve-ID's."""

class GroupRef:
    """Een referentie naar een Hyve. Haal de volledige `Group` op met `fetch`."""

    id: GroupId

    def __init__(self, client: HyvesClient, group_id: int) -> None:
        self._client = client
        self.id = GroupId(group_id)

    async def fetch(self) -> Group:
        """Haalt een `Group` op van de Hyves-API."""
        payload = await self._client.get_group(self.id)
        return self._client.build_group(payload)

    async def join(self) -> None:
        """Word lid van deze Hyve."""
        await self._client.join_group(self.id, params=GroupJoinParams())

    async def leave(self) -> None:
        """Verlaat deze Hyve."""
        await self._client.leave_group(self.id)

    async def get_members(self) -> AsyncIterator[GroupMember]:
        """Itereert over de leden van deze Hyve.

        Yields:
            Hyve-leden.
        """
        async for payload in self._client.get_group_members(self.id):
            yield self._client.build_group_member(payload)

    async def get_posts(self) -> AsyncIterator[GroupPost]:
        """Itereert over de posts in deze Hyve.

        Yields:
            Posts, van nieuw naar oud.
        """
        async for payload in self._client.get_group_posts(self.id):
            yield self._client.build_post(payload)

    async def create_post(self, content: str, link: str | None = None) -> None:
        """Plaatst een post in deze Hyve.

        Args:
            content: Inhoud van de post
            link: Optionele link
        """
        params = PostCreateParams(content=content, link=link)
        await self._client.create_group_post(self.id, params=params)

    async def get_user_options(self) -> GroupUserOptions:
        """Gebruikersvoorkeuren voor deze Hyve"""
        payload = await self._client.get_group_user_options(self.id)
        return GroupUserOptions(
            payload.timeline,
            payload.friendsActivity,
            payload.notifications,
        )

    async def update_user_options(self, options: GroupUserOptions) -> None:
        """Wijzigt de gebruikersvoorkeuren voor deze Hyve.

        Args:
            options: Voorkeuren"""
        params = GroupUserOptionsUpdateParams(
            timeline=options.timeline,
            friendsActivity=options.friends_activity,
            notifications=options.notifications,
        )
        await self._client.update_group_user_options(self.id, params=params)

    async def edit(
        self,
        *,
        name: str = KEEP_CURRENT,
        description: str = KEEP_CURRENT,
        role_to_post: GroupRole = KEEP_CURRENT,
        likes_on_post_enabled: bool = KEEP_CURRENT,
        comments_on_post_enabled: bool = KEEP_CURRENT,
    ) -> Group:
        """Wijzigt de naam en/of groepsomschrijving van deze Hyve.

        Alleen de parameters die je meegeeft worden naar de Hyves-API gestuurd.
        Geef je `None` mee, dan wordt dat veld geleegd.

        Args:
            name: Een nieuwe naam.
            description: Een nieuwe groepsomschrijving.
            role_to_post: Minimale rol om in deze groep te posten.
            likes_on_post_enabled: Respect toestaan.
            comments_on_post_enabled: Reacties toestaan. Hyves geeft een error als je dit gebruikt in combinatie met
                `role_to_post` op [pyhyves.GroupRole.MEMBER][MEMBER].

        Returns:
            De gewijzigde Hyve.
        """
        given = {
            "id": self.id,
            "name": name,
            "description": description,
            "roleToPost": role_to_post,
            "likesOnPostEnabled": likes_on_post_enabled,
            "commentsOnPostEnabled": comments_on_post_enabled,
        }
        data: dict[str, Any] = {key: value for key, value in given.items() if value is not KEEP_CURRENT}
        params = GroupPatchParams(**data)
        payload = await self._client.update_group(self.id, params)
        return self._client.build_group(payload)

    async def delete(self) -> None:
        """Verwijdert deze Hyve."""
        await self._client.delete_group(self.id)


class GroupPreview(GroupRef):
    """Een verkorte weergave van een Hyve. Haal de volledige `Group` op met `fetch`."""

    id: GroupId
    name: str
    image_url: str | None
    banner_url: str | None

    def __init__(self, client: HyvesClient, payload: PartialGroupPayload) -> None:
        self._client = client
        self.id = GroupId(payload.id)
        self.name = payload.name
        self.image_url = payload.imageUrl
        self.banner_url = payload.bannerUrl


class Group(GroupPreview):
    """Gegevens over een Hyve."""

    id: GroupId
    name: str
    image_url: str | None
    banner_url: str | None
    description: str
    owner: AccountRef
    role_to_post: GroupRole
    likes_on_post_enabled: bool
    comments_on_post_enabled: bool
    member_count: int
    is_owner: bool
    background_html: str | None
    member_role: GroupRole | None
    can_post: bool | None

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
