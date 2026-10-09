"""
Pydantic models representing API inputs and responses
"""

from enum import StrEnum, auto
from typing import Any, Literal

from pydantic import BaseModel, Field

Color = str


class PublicUsersCount(BaseModel):
    count: int

class ClientAccount(BaseModel):
    id: int
    email: str
    emailVerified: bool
    image: str | None = None
    banner: str | None = None
    backgroundHtml: str | None = None
    createdAt: Any
    updatedAt: Any
    firstName: str | None = None
    middleName: str | None = None
    lastName: str | None = None
    dateOfBirth: str
    banned: bool
    banReason: Any | None = None
    bannedAt: Any | None = None
    bannedUntil: Any | None = None
    name: str
    bio: str | None = None
    language: str | None = None
    city: str | None = None
    country: str | None = None
    primaryColor: Color | None = None
    secondaryColor: Color | None = None
    backgroundColor: Color | None = None
    gender: str | None  # TODO enum
    jobTitle: str | None = None
    interests: list[str] = Field(default_factory=list)
    slug: str
    unreadNotificationCount: int

class ClientAccountPatchParams(BaseModel):
    bio: str | None = None
    city: str | None = None
    primaryColor: Color | None = None
    secondaryColor: Color | None = None
    backgroundColor: Color | None = None

class FriendshipStatus(StrEnum):
    PENDING = "pending"
    FRIENDS = "friends"
    NONE = "none"

class FriendRequestDirection(StrEnum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"

class PartialFriendRequest(BaseModel):
    id: int
    direction: FriendRequestDirection

class Account(BaseModel):
    id: int
    image: str | None = None
    banner: str | None = None
    backgroundHtml: str | None = None
    firstName: str | None = None
    middleName: str | None = None
    lastName: str | None = None
    name: str
    bio: str | None = None
    city: str | None = None
    primaryColor: Color | None = None
    secondaryColor: Color | None = None
    backgroundColor: Color | None = None
    jobTitle: str | None = None
    slug: str
    isBlocked: bool | None = None
    friendshipStatus: FriendshipStatus | None = None
    friendRequest: PartialFriendRequest | None = None
    friendPreview: Any | None = None

class PartialAccount(BaseModel):
    profileId: int
    name: str
    firstName: str | None = None
    middleName: str | None = None
    lastName: str | None = None
    imageUrl: str | None = None
    bannerUrl: str | None = None

class PartialGroup(BaseModel):
    id: int
    name: str
    imageUrl: str | None = None
    bannerUrl: str | None = None

class TimelineEntryMetadata(BaseModel):
    actor: PartialAccount
    postAuthor: PartialAccount | None = None
    group: PartialGroup | None = None

class TimelineVisibilitySelf(BaseModel):
    reason: Literal["self"]

class TimelineVisibilityFriend(BaseModel):
    reason: Literal["friend"]
    viaProfileId: int

class TimelineVisibilityWallOwner(BaseModel):
    reason: Literal["wall_owner"]

TimelineVisibility = TimelineVisibilitySelf | TimelineVisibilityFriend | TimelineVisibilityWallOwner

class TimelineEntryKind(StrEnum):
    POST = auto()
    ACTIVITY = auto()

class TimelineEntryType(StrEnum):
    PROFILE_PICTURE = auto()
    TIMELINE_POST = auto()
    GROUP_POST = auto()
    GROUP_JOIN = auto()

class TimelineEntry(BaseModel):
    id: int
    profileId: int
    entryKey: str
    entryKind: TimelineEntryKind | str
    entryType: TimelineEntryType | str
    postId: int | None = None
    groupId: int | None = None
    actorProfileId: int
    sourceId: int | None = None
    content: Any
    metadata: TimelineEntryMetadata
    visibility: TimelineVisibility | Any | None = None
    feedAt: Any
    createdAt: Any
    updatedAt: Any

class PostType(StrEnum):
    GROUP = auto()
    WALL = auto()
    TIMELINE = auto()

class WallVisibility(StrEnum):
    APPROVED = auto()
    PENDING = auto()

class Post(BaseModel):
    id: int
    authorUserId: int
    postType: PostType
    content: str
    link: str | None = None
    linkPreview: Any | None = None
    wallOwnerId: int | None = None
    groupId: int | None = None
    groupName: str | None = None
    groupImageUrl: str | None = None
    wallVisibility: WallVisibility | str | None = None
    likesEnabled: bool
    commentsEnabled: bool
    locationName: str | None = None
    locationCoordinate: Any | None = None
    images: list[Any]
    tags: list[str]
    hasMedia: bool
    hasTags: bool
    likeCount: int
    commentCount: int
    recentLikerNames: list[str] = Field(default_factory=list)
    createdAt: Any
    updatedAt: Any
    lastComment: Any | None = None
    moderationHiddenAt: Any | None = None
    authorModerationHiddenAt: Any | None = None
    groupModerationHiddenAt: Any | None = None
    likedByMe: bool
    author: PartialAccount

class Comment(BaseModel):
    id: int
    postId: int
    parentCommentId: int | None = None
    authorUserId: int
    content: str
    images: list[Any]
    tags: list[str]
    createdAt: Any
    updatedAt: Any
    likedByMe: bool
    likeCount: int
    recentLikerNames: list[str] = Field(default_factory=list)
    author: PartialAccount
    hasReplies: bool

class GroupVisibility(StrEnum):
    PUBLIC = auto()

class GroupRole(StrEnum):
    OWNER = auto()
    MEMBER = auto()

class Location(BaseModel):
    id: int
    label: str | None = None
    city: str | None = None
    stateCode: str | None = None
    stateName: str | None = None
    countryCode: str | None = None
    country: str | None = None
    latitude: float| None = None
    longitude: float| None = None

class Group(BaseModel):
    id: int
    name: str
    description: str
    ownerUserId: int
    image: str | None = None
    banner: str | None = None
    backgroundHtml: str | None = None
    visibility: GroupVisibility | str
    roleToPost: GroupRole
    joinInfo: Any | None = None
    location: Location | None = None
    createdAt: Any
    updatedAt: Any
    likesOnPostEnabled: bool
    commentsOnPostEnabled: bool
    memberCount: int
    isOwner: bool
    # joinedAt
    memberRole: GroupRole | None = None  # Only present if client is a member
    canPost: bool | None = None  # Only present if client is a member
    verified: bool | None = None  # Omitted when updating a group

class GroupCreateParams(BaseModel):
    id: Literal[0]
    name: str
    description: str
    # location: Location | None = None
    visibility: Literal[GroupVisibility.PUBLIC]
    roleToPost: GroupRole
    likesOnPostEnabled: bool
    commentsOnPostEnabled: bool | None = None # Must be unset if roleToPost is member
    deleteImage: Literal[False]
    deleteBanner: Literal[False]

class GroupPatchParams(BaseModel):
    id: int | None = None  # No idea what this is for, it works without, but the web app includes it
    # image: Image | None = None
    # banner: Image | None = None
    deleteImage: bool = False
    deleteBanner: bool = False
    name: str | None = None
    description: str | None = None

class GroupMember(BaseModel):
    id: int
    groupId: int
    userId: int
    role: GroupRole
    joinedAt: Any
    updatedAt: Any
    image: str | None = None
    banner: str | None = None
    name: str
    firstName: str | None = None
    middleName: str | None = None
    lastName: str | None = None
    isBlockedFromGroup: bool

class GroupUserOptions(BaseModel):
    timeline: bool
    friendsActivity: bool
    notifications: bool

class GroupUserOptionsUpdateParams(BaseModel):
    timeline: bool
    friendsActivity: bool
    notifications: bool

class GroupJoinParams(BaseModel):
    pass

class PostCreateParams(BaseModel):
    content: str
    link: str | None = None

class WallPostApproveParams(BaseModel):
    pass

class WallPostRejectParams(BaseModel):
    pass

class CommentCreateParams(BaseModel):
    content: str

class LikePostParams(BaseModel):
    isComment: Literal[False]

class UnlikePostParams(BaseModel):
    isComment: Literal[False]

class LikeCommentParams(BaseModel):
    isComment: Literal[True]

class UnlikeCommentParams(BaseModel):
    isComment: Literal[True]

class Friend(BaseModel):
    id: int
    userId: int
    friendUserId: int
    firstName: str | None = None
    middleName: str | None = None
    lastName: str | None = None
    username: str
    image: str | None = None
    mutualFriendsCount: int
    createdAt: Any

class FriendRequestStatus(StrEnum):
    PENDING = auto()
    ACCEPTED = auto()
    DENIED = auto()

class FriendRequest(BaseModel):
    id: int
    fromUserId: int
    toUserId: int
    status: FriendRequestStatus
    createdAt: Any
    updatedAt: Any
    firstName: str | None = None
    middleName: str | None = None
    lastName: str | None = None
    username: str
    image: str | None = None
    mutualFriendsCount: int | None = None # Only present for pending friend requests

class FriendRequestsParams(BaseModel):
    direction: FriendRequestDirection

class FriendRequestCreateParams(BaseModel):
    userId: int

class DeleteResponse(BaseModel):
    success: bool