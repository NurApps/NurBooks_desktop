from pydantic import BaseModel
from typing import Optional, List


class BookCreate(BaseModel):
    id: int
    title: str
    author: str
    category: str
    year: Optional[int] = 0
    description: Optional[str] = ""
    cover: Optional[str] = ""
    pdf: str
    fileSize: Optional[str] = None
    pages: Optional[int] = None
    copyrightProtected: Optional[bool] = False
    viewCount: Optional[int] = 0
    downloadCount: Optional[int] = 0


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    category: Optional[str] = None
    year: Optional[int] = None
    description: Optional[str] = None
    cover: Optional[str] = None
    pdf: Optional[str] = None
    fileSize: Optional[str] = None
    pages: Optional[int] = None
    copyrightProtected: Optional[bool] = None
    viewCount: Optional[int] = None
    downloadCount: Optional[int] = None


class AuthorCreate(BaseModel):
    id: int
    name: str
    bio: Optional[str] = ""
    books: Optional[List[int]] = []


class BookmarkCreate(BaseModel):
    bookId: int
    page: int
    timestamp: Optional[str] = None


class ReadingProgressSave(BaseModel):
    bookId: int
    page: int


class AnalyticsEventCreate(BaseModel):
    eventType: str
    bookId: int
    metadata: Optional[dict] = None
