import tempfile
from pathlib import Path

from src.core.models import UserSettings
from src.core.storage import Storage


def _storage_with_data_path() -> tuple[Storage, str]:
    data_path = tempfile.mkdtemp()
    s = Storage()
    s.data_path = data_path
    return s, data_path


def test_load_settings_default_when_missing():
    s, data_path = _storage_with_data_path()
    settings = s.load_settings()
    assert settings.theme == "light"
    assert settings.default_path == "downloads" or settings.default_path


def test_load_settings_migrates_broken_cloudflare_key():
    """Битый ключ enable云flare_storage не должен ронять загрузку настроек."""
    s, data_path = _storage_with_data_path()
    Path(data_path, "settings.json").write_text(
        '{"default_path": "downloads", "theme": "dark", "enable\u4e91flare_storage": true}',
        encoding="utf-8",
    )
    settings = s.load_settings()
    assert settings.theme == "dark"
    assert settings.enable_cloudflare_storage is True


def test_load_settings_ignores_unknown_keys():
    s, data_path = _storage_with_data_path()
    Path(data_path, "settings.json").write_text(
        '{"default_path": "downloads", "theme": "dark", "unknown_future_setting": 123}',
        encoding="utf-8",
    )
    settings = s.load_settings()
    assert settings.theme == "dark"
    assert not hasattr(settings, "unknown_future_setting")


def test_load_settings_invalid_json_returns_default():
    s, data_path = _storage_with_data_path()
    Path(data_path, "settings.json").write_text("{broken json", encoding="utf-8")
    settings = s.load_settings()
    assert isinstance(settings, UserSettings)


def test_save_settings_roundtrip():
    s, data_path = _storage_with_data_path()
    s.save_settings(UserSettings(default_path="downloads", theme="dark", auto_update=True))
    reloaded = s.load_settings()
    assert reloaded.theme == "dark"
    assert reloaded.auto_update is True
