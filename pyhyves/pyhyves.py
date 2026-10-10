from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Self

from pyhyves.api.client import HyvesClient
from pyhyves.api.schema import (
    GroupCreateParams,
    GroupRole,
    GroupVisibility,
    PostCreateParams,
)
from pyhyves.auth import HyvesOAuth2Client, PasswordCredentials, TokenCredentials

if TYPE_CHECKING:
    from pyhyves.account import Account, AccountId, AccountRef
    from pyhyves.group import Group, GroupId, GroupRef
    from pyhyves.post import BasePost, PostId, PostRef


class Pyhyves:
    """Een geauthenticeerde sessie met de Hyves API.

    Args:
        credentials: Optionele inloggegevens. Zonder inloggegevens werken alleen openbare endpoints.
    """

    def __init__(
        self,
        credentials: PasswordCredentials | TokenCredentials | None = None,
    ) -> None:
        self._http = HyvesOAuth2Client(credentials)
        self._client = HyvesClient(self._http)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Sluit de onderliggende HTTP-client af.

        Je kunt deze class ook als async context manager gebruiken (`async with Pyhyves() as hyves: ...`).
        """
        await self._http.aclose()

    # region Public

    async def public_get_user_count(self) -> int:
        """Haalt het totale aantal geregistreerde gebruikers op. Geen authenticatie nodig.

        Returns:
            Het totale aantal geregistreerde gebruikers.
        """
        return (await self._client.public_get_user_count()).count

    # endregion

    # region Account

    def get_account_ref(self, account_id: AccountId) -> AccountRef:
        """Maakt een referentie naar een account zonder een request te maken."""
        return self._client.build_account_ref(account_id)

    async def get_account(self, account_id: AccountId) -> Account:
        """Haalt het profiel van een gebruiker op."""
        return await self.get_account_ref(account_id).fetch()

    # endregion

    # region Groups

    def get_group_ref(self, group_id: GroupId) -> GroupRef:
        """Geeft een referentie naar een Hyve, zonder een request te maken."""
        return self._client.build_group_ref(group_id)

    async def get_group(self, group_id: GroupId) -> Group:
        """Haalt een Hyve op."""
        return await self.get_group_ref(group_id).fetch()

    async def create_group(
        self,
        name: str,
        description: str,
        *,
        role_to_post: GroupRole = GroupRole.MEMBER,
        likes_on_post_enabled: bool = True,
    ) -> Group:
        """Maakt een openbare groep aan die van jou is.

        Args:
            name: De naam van de groep.
            description: Groepsbeschrijving.
            role_to_post: De rol die nodig is om in de groep te posten.
            likes_on_post_enabled: Of likes op posts in de groep toegestaan zijn.

        Returns:
            De aangemaakte groep.
        """
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
        """Itereert over de Hyves waarvan je lid bent.

        Yields:
            De Hyves, in batches geladen zodra ze nodig zijn.
        """
        async for payload in self._client.get_client_groups():
            yield self._client.build_group(payload)

    async def get_sponsored_groups(self) -> AsyncIterator[Group]:
        """Itereert over de uitgelichte Hyves.

        Yields:
            Uitgelichte Hyves, in batches geladen zodra ze nodig zijn.
        """
        async for payload in self._client.get_sponsored_groups():
            yield self._client.build_group(payload)

    # endregion

    # region Posts

    def get_post_ref(self, post_id: PostId) -> PostRef:
        """Geeft een referentie naar een post, zonder een request te maken."""
        return self._client.build_post_ref(post_id)

    async def get_post(self, post_id: PostId) -> BasePost:
        """Haalt een post op."""
        return await self.get_post_ref(post_id).fetch()

    async def create_timeline_post(self, content: str, *, link: str | None = None) -> None:
        """Plaatst een WieWatWaar.

        Args:
            content: De inhoud van de post.
            link: Optionele link.
        """
        await self._client.create_timeline_post(
            PostCreateParams(content=content, link=link)
        )

    # endregion
