from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, NewType

from pyhyves.api.schema import (
    BasePost as PostPayload,
)
from pyhyves.api.schema import (
    Comment as CommentPayload,
)
from pyhyves.api.schema import (
    CommentCreateParams,
    LikeCommentParams,
    LikePostParams,
    PostType,
    UnlikeCommentParams,
    UnlikePostParams,
)
from pyhyves.api.schema import (
    GroupPost as GroupPostPayload,
)
from pyhyves.api.schema import (
    TimelinePost as TimelinePostPayload,
)
from pyhyves.api.schema import (
    WallPost as WallPostPayload,
)

if TYPE_CHECKING:
    from pyhyves.api.client import HyvesClient

PostId = NewType("PostId", int)
"""Een `NewType` van `int` voor post-ID's."""

CommentId = NewType("CommentId", int)
"""Een `NewType` van `int` voor comment-ID's."""

class PostRef:
    """Een referentie naar een post. Haal de volledige `Post` op met `fetch`."""

    def __init__(self, client: HyvesClient, post_id: int) -> None:
        self._client = client
        self.id = PostId(post_id)

    async def fetch(self) -> GroupPost | WallPost | TimelinePost:
        """Haalt een `Post` op van de Hyves-API."""
        payload = await self._client.get_post(self.id)
        return self._client.build_post(payload)

    async def like(self) -> None:
        """Geeft Respect aan deze post."""
        params = LikePostParams(isComment=False)
        await self._client.like_post(self.id, params)

    async def unlike(self) -> None:
        """Haalt Respect van deze post weg."""
        params = UnlikePostParams(isComment=False)
        await self._client.unlike_post(self.id, params)

    async def get_comments(self) -> AsyncIterator[Comment]:
        """Itereert over de reacties op deze post.

        Yields:
            Reacties op de post
        """
        async for payload in self._client.get_comments(self.id):
            yield self._client.build_comment(payload)

    async def comment(self, content: str) -> Comment:
        """Plaatst een reactie op deze post.

        Returns:
            De nieuwe comment."""
        params = CommentCreateParams(content=content)
        payload = await self._client.create_comment(self.id, params)
        return self._client.build_comment(payload)

    async def delete(self) -> None:
        """Verwijdert deze post."""
        await self._client.delete_post(self.id)

class BasePost(PostRef):
    """Gedeelde attributes van alle soorten posts (tijdlijn, muur, groep)"""

    def __init__(self, client: HyvesClient, payload: PostPayload) -> None:
        self._client = client
        self.id = PostId(payload.id)
        self.author = client.build_account_preview(payload.author)
        self.post_type = payload.postType
        self.content = payload.content
        self.link = payload.link
        self.tags = payload.tags
        self.has_media = payload.hasMedia
        self.has_tags = payload.hasTags
        self.like_count = payload.likeCount
        self.comment_count = payload.commentCount
        self.liked_by_me = payload.likedByMe
        self.likes_enabled = payload.likesEnabled
        self.comments_enabled = payload.commentsEnabled
        self.location_name = payload.locationName
        self.location_coordinate = payload.locationCoordinate
        self.recent_liker_names = payload.recentLikerNames

class GroupPost(BasePost):
    """Een post in een Hyve."""

    def __init__(self, client: HyvesClient, payload: GroupPostPayload) -> None:
        super().__init__(client, payload)
        self.group = client.build_group_ref(payload.groupId)

class WallPost(BasePost):
    """Een Krabbel op iemands profiel."""

    def __init__(self, client: HyvesClient, payload: WallPostPayload) -> None:
        super().__init__(client, payload)
        self.wall_owner = client.build_account_ref(payload.wallOwnerId)

class TimelinePost(BasePost):
    """Een WieWatWaar."""

    def __init__(self, client: HyvesClient, payload: TimelinePostPayload) -> None:
        assert payload.postType == PostType.TIMELINE
        super().__init__(client, payload)

Post = GroupPost | WallPost | TimelinePost
"""Alias voor `GroupPost | WallPost | TimelinePost`."""

class Comment:
    """Een reactie op een post. De Hyves-API stuurt altijd de hele reactie mee, dus er is geen `CommentRef`."""

    def __init__(self, client: HyvesClient, payload: CommentPayload):
        self._client = client
        self.id = CommentId(payload.id)
        self.post = PostRef(client, payload.postId)
        self.author = client.build_account_preview(payload.author)
        self.content = payload.content
        self.tags = payload.tags
        self.liked_by_me = payload.likedByMe
        self.like_count = payload.likeCount
        self.has_replies = payload.hasReplies
        self.recent_liker_names = payload.recentLikerNames

    async def like(self) -> None:
        """Geeft Respect aan deze reactie."""
        await self._client.like_comment(self.id, LikeCommentParams(isComment=True))

    async def unlike(self) -> None:
        """Haalt Respect van deze reactie weg."""
        await self._client.unlike_comment(self.id, UnlikeCommentParams(isComment=True))

    async def delete(self) -> None:
        """Verwijdert deze reactie."""
        await self._client.delete_comment(self.post.id, self.id)
