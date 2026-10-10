from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, NewType

from pyhyves.api.schema import (
    Account as AccountPayload,
)
from pyhyves.api.schema import (
    ClientAccount as ClientAccountPayload,
)
from pyhyves.api.schema import (
    PartialAccount as PartialAccountPayload,
)
from pyhyves.api.schema import (
    PostCreateParams,
)

if TYPE_CHECKING:
    from pyhyves.api.client import HyvesClient
    from pyhyves.post import WallPost

AccountId = NewType("AccountId", int)
"""Een `NewType` van `int` voor account-ID's."""

class AccountRef:
    """Een referentie naar een profiel. Haal het volledige `Account` op met `fetch`."""

    def __init__(self, client: HyvesClient, account_id: int) -> None:
        self._client = client
        self.id = AccountId(account_id)

    async def fetch(self) -> Account:
        """Haalt het volledige profiel op."""
        payload = await self._client.get_account(self.id)
        return self._client.build_account(payload)

    async def get_wall_posts(self) -> AsyncIterator[WallPost]:
        """Itereert over de Krabbels op dit profiel.

        Yields:
            Krabbels, geladen in batches zodra ze nodig zijn.
        """

        async for payload in self._client.get_wall_posts(self.id):
            yield self._client.build_post(payload)

    async def create_wall_post(self, content: str, link: str | None = None) -> WallPost:
        """Plaatst een Krabbel op dit profiel.

        Returns:
            De nieuwe post.
        """
        params = PostCreateParams(content=content, link=link)
        payload = await self._client.create_wall_post(self.id, params)
        return self._client.build_post(payload)

class AccountPreview(AccountRef):
    """Een gedeeltelijk profiel. Haal het volledige `Account` op met `fetch`."""

    def __init__(self, client: HyvesClient, payload: PartialAccountPayload):
        self._client = client
        self.id = AccountId(payload.profileId)
        self.name = payload.name
        self.first_name = payload.firstName
        self.middle_name = payload.middleName
        self.last_name = payload.lastName
        self.image_url = payload.imageUrl
        self.banner_url = payload.bannerUrl

class Account(AccountPreview):
    """Het profiel van een gebruiker.

    Te verkrijgen met [pyhyves.Pyhyves.get_account][]."""

    def __init__(self, client: HyvesClient, payload: AccountPayload):
        self._client = client
        self.id = AccountId(payload.id)
        self.name = payload.name
        self.first_name = payload.firstName
        self.middle_name = payload.middleName
        self.last_name = payload.lastName
        self.image_url = payload.image
        self.banner_url = payload.banner
        self.slug = payload.slug
        self.background_html = payload.backgroundHtml
        self.bio = payload.bio
        self.city = payload.city
        self.primary_color = payload.primaryColor
        self.secondary_color = payload.secondaryColor
        self.background_color = payload.backgroundColor
        self.job_title = payload.jobTitle
        self.is_blocked = payload.isBlocked


class ClientAccount(Account):
    """Het profiel van de ingelogde gebruiker.

    Te verkrijgen met [pyhyves.Pyhyves.get_client_account][]."""

    def __init__(self, client: HyvesClient, payload: ClientAccountPayload) -> None:
        self._client = client
        self.id = AccountId(payload.id)
        self.name = payload.name
        self.first_name = payload.firstName
        self.middle_name = payload.middleName
        self.last_name = payload.lastName
        self.image_url = payload.image
        self.banner_url = payload.banner
        self.background_html = payload.backgroundHtml
        self.bio = payload.bio
        self.city = payload.city
        self.country = payload.country
        self.primary_color = payload.primaryColor
        self.secondary_color = payload.secondaryColor
        self.background_color = payload.backgroundColor
        self.job_title = payload.jobTitle
        self.gender = payload.gender
        self.slug = payload.slug
        self.email = payload.email
        self.email_verified = payload.emailVerified
        self.language = payload.language
        self.date_of_birth = payload.dateOfBirth
        self.interests = payload.interests
        self.banned = payload.banned
        self.ban_reason = payload.banReason
        self.banned_at = payload.bannedAt
        self.banned_until = payload.bannedUntil
        self.unread_notification_count = payload.unreadNotificationCount
