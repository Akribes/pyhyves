"""A Python client for the Hyves API."""

from pyhyves.api.client import HyvesAPIException

from .account import Account, AccountId, AccountPreview, AccountRef
from .api.schema import GroupRole, GroupVisibility
from .auth import (
    Credentials,
    HyvesAuthException,
    PasswordCredentials,
    TokenCredentials,
)
from .group import Group, GroupId, GroupPreview, GroupRef
from .post import (
    BasePost,
    Comment,
    CommentId,
    GroupPost,
    Post,
    PostId,
    PostRef,
    TimelinePost,
    WallPost,
)
from .pyhyves import Pyhyves

__all__ = (
    "Account",
    "AccountId",
    "AccountPreview",
    "AccountRef",
    "BasePost",
    "Comment",
    "CommentId",
    "Credentials",
    "Group",
    "GroupId",
    "GroupPost",
    "GroupPreview",
    "GroupRef",
    "GroupRole",
    "GroupVisibility",
    "HyvesAPIException",
    "HyvesAuthException",
    "PasswordCredentials",
    "Post",
    "PostId",
    "PostRef",
    "Pyhyves",
    "TimelinePost",
    "TokenCredentials",
    "WallPost",
)
