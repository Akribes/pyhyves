from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, NewType

from pyhyves.api.schema import (
    Account as AccountPayload,
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

class AccountRef:
    """A reference to a profile. Upgrade to a full ``Account`` with ``fetch``."""

    def __init__(self, client: HyvesClient, account_id: int) -> None:
        self._client = client
        self.id = AccountId(account_id)

    async def fetch(self) -> Account:
        payload = await self._client.get_account(self.id)
        return self._client.build_account(payload)

    async def get_wall_posts(self) -> AsyncIterator[WallPost]:
        async for payload in self._client.get_wall_posts(self.id):
            yield self._client.build_post(payload)

    async def create_wall_post(self, content: str, link: str | None = None) -> None:
        params = PostCreateParams(content=content, link=link)
        await self._client.create_wall_post(self.id, params)

class AccountPreview(AccountRef):
    """A partial account. Upgrade to a full ``Account`` with ``fetch``."""

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
    """Another user's public profile."""

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
