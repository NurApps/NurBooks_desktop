
from pydantic import BaseModel


class BookCreate(BaseModel):
    id: int
    title: str
    author: str
    category: str
    year: int | None = 0
    description: str | None = ""
    cover: str | None = ""
    pdf: str
    fileSize: str | None = None
    pages: int | None = None
    copyrightProtected: bool | None = False
    viewCount: int | None = 0
    downloadCount: int | None = 0


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    category: str | None = None
    year: int | None = None
    description: str | None = None
    cover: str | None = None
    pdf: str | None = None
    fileSize: str | None = None
    pages: int | None = None
    copyrightProtected: bool | None = None
    viewCount: int | None = None
    downloadCount: int | None = None


class AuthorCreate(BaseModel):
    id: int
    name: str
    bio: str | None = ""
    books: list[int] | None = []


class BookmarkCreate(BaseModel):
    bookId: int
    page: int
    timestamp: str | None = None


class ReadingProgressSave(BaseModel):
    bookId: int
    page: int


class FavoriteCreate(BaseModel):
    bookId: int


class WishlistCreate(BaseModel):
    bookId: int


class RatingUpsert(BaseModel):
    bookId: int
    rating: int
    review: str | None = None
    nickname: str | None = None


class LibraryCreate(BaseModel):
    title: str
    description: str = ""
    visibility: str = "public"
    bookIds: list[int] = []


class LibraryUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    visibility: str | None = None
    bookIds: list[int] | None = None


class LibraryJoin(BaseModel):
    inviteCode: str


class LibraryRatingUpsert(BaseModel):
    rating: int


class AnalyticsEventCreate(BaseModel):
    eventType: str
    bookId: int
    metadata: dict | None = None


class UserUpsert(BaseModel):
    nickname: str
