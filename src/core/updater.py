"""
Проверка и загрузка обновлений через GitHub Releases.
"""
import json
import os
import ssl
import subprocess
import sys
import threading
import urllib.request
from dataclasses import dataclass

from src.config import APP_VERSION
from src.core.logger import get_logger
from src.core.utils import download_to_file

logger = get_logger(__name__)

REPO = "NurApps/NurBooks_desktop"
API_URL = f"https://api.github.com/repos/{REPO}/releases"


MAX_UPDATE_BYTES = 300 * 1024 * 1024


@dataclass
class ReleaseInfo:
    tag: str
    version: str
    is_beta: bool
    download_url: str
    body: str
    sha256: str = ""


def _parse_version(tag: str) -> tuple:
    """v1.3.5 → (1, 3, 5)"""
    v = tag.lstrip("vV")
    parts = []
    for p in v.split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def _get_json(url: str, timeout: int = 10) -> dict | None:
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={"User-Agent": "NurBooks/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        logger.error(f"GitHub API error: {e}")
        return None


def check_latest(beta: bool = False) -> ReleaseInfo | None:
    """Проверяет последний релиз на GitHub."""
    url = API_URL if beta else f"{API_URL}/latest"
    data = _get_json(url)
    if not data:
        return None

    releases = data if isinstance(data, list) else [data]
    for rel in releases:
        tag = rel.get("tag_name", "")
        is_prerelease = rel.get("prerelease", False)
        if not beta and is_prerelease:
            continue

        assets = rel.get("assets", [])
        exe_asset = None
        for a in assets:
            name = a.get("name", "").lower()
            if name.endswith(".exe"):
                exe_asset = a
                break
        if not exe_asset:
            continue

        digest = str(exe_asset.get("digest") or "")
        sha256 = digest.split(":", 1)[1].lower() if digest.startswith("sha256:") else ""

        return ReleaseInfo(
            tag=tag,
            version=tag.lstrip("vV"),
            is_beta=is_prerelease,
            download_url=exe_asset["browser_download_url"],
            body=rel.get("body", ""),
            sha256=sha256,
        )
    return None


def is_newer(installed: str, latest: str) -> bool:
    """True если latest новее installed."""
    return _parse_version(latest) > _parse_version(installed)


def download_update(url: str, dest: str, progress_callback=None, expected_sha256: str = ""):
    """Скачивает EXE в dest и проверяет SHA-256 из GitHub Releases."""
    if not expected_sha256:
        raise ValueError("SHA-256 обновления не указан — загрузка отклонена")
    download_to_file(
        url,
        dest,
        timeout=60,
        max_bytes=MAX_UPDATE_BYTES,
        progress_callback=progress_callback,
        expected_sha256=expected_sha256,
    )
    with open(dest, "rb") as f:
        if f.read(2) != b"MZ":
            os.remove(dest)
            raise ValueError("скачанный файл не является EXE")


def apply_update(new_exe: str):
    """Запускает новый EXE, завершает текущий процесс."""
    if getattr(sys, "frozen", False):
        path = os.path.realpath(new_exe)
        if not os.path.isfile(path) or os.path.getsize(path) > MAX_UPDATE_BYTES:
            raise ValueError("некорректный файл обновления")
        with open(path, "rb") as f:
            if f.read(2) != b"MZ":
                raise ValueError("файл обновления повреждён")
        subprocess.Popen([path], shell=False)
        os._exit(0)
    else:
        logger.info("Update skipped (not frozen)")


def check_in_background(beta: bool, callback):
    """Проверяет обновление в фоновом потоке. callback(release_info or None)."""
    def _run():
        try:
            info = check_latest(beta=beta)
            if info and is_newer(APP_VERSION, info.version):
                callback(info)
            else:
                callback(None)
        except Exception as e:
            logger.error(f"Background update check failed: {e}")
            callback(None)
    threading.Thread(target=_run, daemon=True).start()
