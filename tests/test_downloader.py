from src.core.downloader import Downloader
from src.core.models import Book


def _book(pdf: str, title: str = "Книга", book_id: int = 5) -> Book:
    return Book(
        id=book_id,
        title=title,
        author="Автор",
        category="Категория",
        year=2024,
        description="",
        cover="",
        pdf=pdf,
    )


def test_convert_raw_url_keeps_raw():
    d = Downloader()
    url = "https://raw.githubusercontent.com/NurApps/repo/main/x.pdf"
    assert d._convert_to_raw_url(url) == url


def test_convert_blob_to_raw():
    d = Downloader()
    url = "https://github.com/NurApps/repo/blob/main/x.pdf"
    assert d._convert_to_raw_url(url) == "https://github.com/NurApps/repo/raw/main/x.pdf"


def test_convert_non_url_passthrough():
    d = Downloader()
    assert d._convert_to_raw_url("pdfs/x.pdf") == "pdfs/x.pdf"


def test_filename_from_original():
    d = Downloader()
    name = d._get_book_filename(_book("https://x/repo/blob/main/Таухид.pdf"), "Таухид.pdf")
    assert name.endswith(".pdf")
    assert name.startswith("5_")


def test_filename_from_title():
    d = Downloader()
    name = d._get_book_filename(_book("https://x/repo/blob/main/x.pdf"))
    assert name == "5_Книга.pdf"


def test_filename_truncated():
    d = Downloader()
    long_title = "Очень длинное название книги которое точно превышает тридцать символов"
    name = d._get_book_filename(_book("https://x/x.pdf", title=long_title))
    assert len(name) < 50


def test_filename_fallback_id():
    d = Downloader()
    book = _book("https://x/x.pdf", title="")
    assert d._get_book_filename(book) == "5.pdf"
