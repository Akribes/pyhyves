
from pydantic import BaseModel

Color = str


class Account(BaseModel):
    id: int
    email: str
    emailVerified: bool
    image: str | None
    banner: str | None
    backgroundHtml: str | None
    # createdAt: str
    # updatedAt: str
    firstName: str | None
    middleName: str | None
    lastName: str | None
    # dateOfBirth: str | None
    banned: bool
    # banReason: Any | None
    # bannedAt: Any | None
    # bannedUntil: Any | None
    name: str
    bio: str | None
    language: str | None
    city: str | None
    country: str | None
    primaryColor: Color | None
    secondaryColor: Color | None
    backgroundColor: Color | None
    # gender: str | None # TODO StrEnum?
    jobTitle: str | None
    interests: list[str]
    slug: str
    unreadNotificationCount: int
