import os

import pytest

from src.core.utils import (
    assert_safe_remote_url,
    download_to_file,
    safe_filename,
    safe_path_within,
)


def test_safe_filename_strips_traversal_and_keeps_cyrillic():
    assert safe_filename("../../Книга.pdf") == "Книга.pdf"
    assert safe_filename("..\\..\\secret.txt") == "secret.txt"
    assert safe_filename("") == ""
    assert safe_filename("...") == ""


def test_safe_filename_windows_reserved():
    assert safe_filename("CON.txt") == "_CON.txt"


def test_safe_filename_limits_length():
    name = safe_filename("a" * 500 + ".pdf", max_length=40)
    assert len(name) <= 40


def test_safe_path_within_blocks_escape(tmp_path):
    with pytest.raises(ValueError):
        safe_path_within(str(tmp_path), "../outside.pdf")
    assert safe_path_within(str(tmp_path), "book.pdf") == os.path.realpath(
        os.path.join(tmp_path, "book.pdf")
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com/x.pdf",
        "https://127.0.0.1/x.pdf",
        "https://localhost/x.pdf",
        "https://user:pass@example.com/x.pdf",
    ],
)
def test_assert_safe_remote_url_rejects_dangerous(url):
    with pytest.raises(ValueError):
        assert_safe_remote_url(url)


def test_download_to_file_requires_https(tmp_path):
    with pytest.raises(ValueError):
        download_to_file("http://example.com/x.pdf", str(tmp_path / "x.pdf"))
    assert not (tmp_path / "x.pdf").exists()
