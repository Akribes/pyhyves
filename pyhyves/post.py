from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, NewType, assert_never

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
from pyhyves.api.schema import Post as PostPayload

if TYPE_CHECKING:
    from pyhyves.api.client import HyvesClient

PostId = NewType("PostId", int)
CommentId = NewType("CommentId", int)

class PostRef:
    """A reference to a post. Upgrade to a full ``Post`` with ``fetch``."""

    def __init__(self, client: HyvesClient, post_id: int) -> None:
        self._client = client
        self.id = PostId(post_id)

    async def fetch(self) -> GroupPost | WallPost | TimelinePost:
        payload = await self._client.get_post(self.id)
        return post_from_payload(self._client, payload)

    async def like(self) -> None:
        """Like this post and return it with the updated counters."""
        params = LikePostParams(isComment=False)
        await self._client.like_post(self.id, params)

    async def unlike(self) -> None:
        """Remove this post's like."""
        params = UnlikePostParams(isComment=False)
        await self._client.unlike_post(self.id, params)

    async def get_comments(self) -> AsyncIterator[Comment]:
        """Iterate over this post's comments, fetching pages lazily."""
        async for payload in self._client.get_comments(self.id):
            yield self._client.build_comment(payload)

    async def comment(self, content: str) -> None:
        """Post a comment on this post."""
        params = CommentCreateParams(content=content)
        await self._client.create_comment(self.id, params)

    async def delete(self) -> None:
        """Delete this post."""
        await self._client.delete_post(self.id)

class Post(PostRef):
    """Common fields of all post types (timeline, wall, group)."""

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

class GroupPost(Post):
    def __init__(self, client: HyvesClient, payload: PostPayload) -> None:
        assert payload.postType == PostType.GROUP
        super().__init__(client, payload)
        self.group = client.build_group_ref(payload.groupId)

class WallPost(Post):
    def __init__(self, client: HyvesClient, payload: PostPayload) -> None:
        assert payload.postType == PostType.WALL
        super().__init__(client, payload)
        self.wall_owner = client.build_account_ref(payload.wallOwnerId)

class TimelinePost(Post):
    def __init__(self, client: HyvesClient, payload: PostPayload) -> None:
        assert payload.postType == PostType.TIMELINE
        super().__init__(client, payload)

def post_from_payload(client: HyvesClient, payload: PostPayload) -> GroupPost | WallPost | TimelinePost:
    match payload.postType:
        case PostType.GROUP:
            return GroupPost(client, payload)
        case PostType.WALL:
            return WallPost(client, payload)
        case PostType.TIMELINE:
            return TimelinePost(client, payload)
        case _ as unreachable:
            assert_never(unreachable)

class Comment:
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
        """Like this comment and return it with the updated counters."""
        await self._client.like_comment(self.id, LikeCommentParams(isComment=True))

    async def unlike(self) -> None:
        """Remove this comment's like."""
        await self._client.unlike_comment(self.id, UnlikeCommentParams(isComment=True))

    async def delete(self) -> None:
        """Delete this comment."""
        await self._client.delete_comment(self.post.id, self.id)
