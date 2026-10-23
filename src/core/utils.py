import hashlib
import ipaddress
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_DOWNLOAD_BYTES = 200 * 1024 * 1024

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def convert_github_url(url: str) -> str:
    """Конвертирует GitHub blob URL в raw URL для прямого доступа к файлу.

    Поддерживает:
    - https://github.com/owner/repo/blob/branch/path/file -> raw
    - https://github.com/owner/repo/releases/download/... -> без изменений
    - Уже raw-ссылки -> без изменений
    """
    if not url or not url.startswith(("http://", "https://")):
        return url

    if "raw.githubusercontent.com" in url:
        return url

    if "releases/download" in url:
        return url

    match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/blob/(.+)/(.+)",
        url,
    )
    if match:
        owner, repo, branch, filepath = match.groups()
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"

    return url


def format_file_size(size_bytes: int) -> str:
    """Форматирует размер файла в читаемый вид"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def safe_filename(filename: str, max_length: int = 120) -> str:
    """Безопасное имя файла: без пути, ``..``, управляющих и опасных символов.

    Сохраняет Unicode-буквы (кириллицу), чтобы названия книг оставались
    читаемыми, но убирает всё, чем можно выйти за пределы каталога.
    """
    name = os.path.basename(str(filename or "").replace("\\", "/"))
    name = "".join(c for c in name if c.isalnum() or c in " ._-()[]")
    name = name.strip(" .")
    if not name:
        return ""
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    ext = ext[:16]
    if stem.upper() in _WINDOWS_RESERVED:
        stem = f"_{stem}"
    stem = stem[: max(1, max_length - len(ext) - 1)].rstrip(" .")
    return f"{stem}.{ext}" if ext else stem


def safe_path_within(base_dir: str, filename: str) -> str:
    """Возвращает путь внутри base_dir или ValueError при попытке выхода наружу."""
    base = os.path.realpath(base_dir)
    candidate = os.path.realpath(os.path.join(base, filename))
    try:
        if os.path.commonpath([base, candidate]) != base:
            raise ValueError("path escapes base directory")
    except ValueError as exc:
        raise ValueError("path escapes base directory") from exc
    return candidate


def _is_public_ip(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Не даём urllib самому ходить по редиректам — проверяем каждый хост."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def assert_safe_remote_url(url: str, allow_private: bool = False) -> str:
    """Разрешает только https-URL без credentials и (по умолчанию) без приватных IP."""
    parsed = urllib.parse.urlparse(str(url or ""))
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("only https URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("credentials in URL are not allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("invalid URL host")
    if not allow_private:
        if host.lower() in {"localhost", "localhost.localdomain"}:
            raise ValueError("local hosts are not allowed")
        try:
            infos = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise ValueError(f"cannot resolve host: {host}") from exc
        for info in infos:
            if not _is_public_ip(info[4][0]):
                raise ValueError("private/reserved addresses are not allowed")
    return url


def download_to_file(
    url: str,
    dest_path: str,
    timeout: int = 60,
    max_bytes: int = MAX_DOWNLOAD_BYTES,
    progress_callback=None,
    expected_sha256: str | None = None,
) -> str:
    """Скачивает https-файл с проверкой размера/хэша и атомарной записью.

    Возвращает путь к файлу. Бросает ValueError при любой проверке.
    """
    assert_safe_remote_url(url)
    os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
    tmp_path = f"{dest_path}.part"
    hasher = hashlib.sha256()
    total = 0
    downloaded = 0
    opener = urllib.request.build_opener(_NoRedirectHandler())
    current_url = url
    req = urllib.request.Request(current_url, headers={"User-Agent": "NurBooks/1.0"})
    try:
        for _ in range(5):
            try:
                resp = opener.open(req, timeout=timeout)
                break
            except urllib.error.HTTPError as exc:
                if exc.code not in (301, 302, 303, 307, 308):
                    raise
                location = exc.headers.get("Location")
                if not location:
                    raise ValueError("redirect without Location") from exc
                current_url = urllib.parse.urljoin(current_url, location)
                assert_safe_remote_url(current_url)
                req = urllib.request.Request(current_url, headers={"User-Agent": "NurBooks/1.0"})
        else:
            raise ValueError("too many redirects")

        with resp:
            final = urllib.parse.urlparse(resp.geturl())
            if final.scheme != "https":
                raise ValueError("redirect to non-https URL is not allowed")
            length = resp.headers.get("Content-Length")
            if length and length.isdigit() and int(length) > max_bytes:
                raise ValueError("file is too large")
            with open(tmp_path, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        raise ValueError("file is too large")
                    hasher.update(chunk)
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and length and length.isdigit() and int(length):
                        progress_callback(downloaded / int(length))
        if expected_sha256 and hasher.hexdigest().lower() != expected_sha256.lower():
            raise ValueError("sha256 mismatch")
        os.replace(tmp_path, dest_path)
        return dest_path
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def open_in_system(path: str):
    """Открывает файл/папку без shell-инъекций."""
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def get_file_hash(filepath: str) -> str:
    """Вычисляет хеш файла для проверки целостности"""
    try:
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return ""


def validate_pdf(filepath: str) -> bool:
    """Проверяет, является ли файл валидным PDF"""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            return header == b'%PDF'
    except OSError:
        return False
