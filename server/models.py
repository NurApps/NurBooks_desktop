from pydantic import BaseModel, Field

# Разумные верхние границы: защищают Firestore от раздувания документов
# и ответы API от гигантских payload'ов.
MAX_TITLE = 300
MAX_AUTHOR = 200
MAX_CATEGORY = 100
MAX_DESCRIPTION = 5000
MAX_URL = 2000
MAX_REVIEW = 2000
MAX_NICKNAME = 64
MAX_BOOKS_IN_LIBRARY = 1000


class BookCreate(BaseModel):
    id: int = Field(ge=0)
    title: str = Field(min_length=1, max_length=MAX_TITLE)
    author: str = Field(default="", max_length=MAX_AUTHOR)
    category: str = Field(default="", max_length=MAX_CATEGORY)
    year: int | None = Field(default=0, ge=0, le=3000)
    description: str | None = Field(default="", max_length=MAX_DESCRIPTION)
    cover: str | None = Field(default="", max_length=MAX_URL)
    pdf: str = Field(min_length=1, max_length=MAX_URL)
    fileSize: str | None = Field(default=None, max_length=64)
    pages: int | None = Field(default=None, ge=0, le=1_000_000)
    copyrightProtected: bool | None = False
    viewCount: int | None = Field(default=0, ge=0)
    downloadCount: int | None = Field(default=0, ge=0)


class BookUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=MAX_TITLE)
    author: str | None = Field(default=None, max_length=MAX_AUTHOR)
    category: str | None = Field(default=None, max_length=MAX_CATEGORY)
    year: int | None = Field(default=None, ge=0, le=3000)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION)
    cover: str | None = Field(default=None, max_length=MAX_URL)
    pdf: str | None = Field(default=None, min_length=1, max_length=MAX_URL)
    fileSize: str | None = Field(default=None, max_length=64)
    pages: int | None = Field(default=None, ge=0, le=1_000_000)
    copyrightProtected: bool | None = None
    viewCount: int | None = Field(default=None, ge=0)
    downloadCount: int | None = Field(default=None, ge=0)


class AuthorCreate(BaseModel):
    id: int = Field(ge=0)
    name: str = Field(min_length=1, max_length=MAX_AUTHOR)
    bio: str | None = Field(default="", max_length=MAX_DESCRIPTION)
    books: list[int] | None = Field(default_factory=list, max_length=MAX_BOOKS_IN_LIBRARY)


class BookmarkCreate(BaseModel):
    bookId: int = Field(ge=0)
    page: int = Field(ge=0, le=1_000_000)
    timestamp: str | None = Field(default=None, max_length=64)


class ReadingProgressSave(BaseModel):
    bookId: int = Field(ge=0)
    page: int = Field(ge=0, le=1_000_000)


class FavoriteCreate(BaseModel):
    bookId: int = Field(ge=0)


class WishlistCreate(BaseModel):
    bookId: int = Field(ge=0)


class RatingUpsert(BaseModel):
    bookId: int = Field(ge=0)
    rating: int = Field(ge=1, le=5)
    review: str | None = Field(default=None, max_length=MAX_REVIEW)
    nickname: str | None = Field(default=None, max_length=MAX_NICKNAME)


class LibraryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    visibility: str = Field(default="public", pattern="^(public|private)$")
    bookIds: list[int] = Field(default_factory=list, max_length=MAX_BOOKS_IN_LIBRARY)


class LibraryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    visibility: str | None = Field(default=None, pattern="^(public|private)$")
    bookIds: list[int] | None = Field(default=None, max_length=MAX_BOOKS_IN_LIBRARY)


class LibraryJoin(BaseModel):
    inviteCode: str = Field(min_length=1, max_length=32)


class LibraryRatingUpsert(BaseModel):
    rating: int = Field(ge=1, le=5)


class AnalyticsEventCreate(BaseModel):
    eventType: str = Field(min_length=1, max_length=32)
    bookId: int = Field(ge=0)
    metadata: dict | None = None


class UserUpsert(BaseModel):
    nickname: str = Field(min_length=1, max_length=MAX_NICKNAME)
