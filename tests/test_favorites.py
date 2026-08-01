import importlib
import json

fav = importlib.import_module("src.core.favorites")


def _reset(tmp_path):
    fav.favorites._file_path = str(tmp_path / "favorite_books.json")
    fav.favorites._favorites = []
    fav.favorites._loaded = False


def test_load_local_from_file(tmp_path):
    _reset(tmp_path)
    p = tmp_path / "favorite_books.json"
    p.write_text(json.dumps(["1", "2"]), encoding="utf-8")
    fav.favorites._file_path = str(p)
    fav.favorites._loaded = False
    fav.favorites._load_local()
    assert fav.favorites.get_favorites() == ["1", "2"]


def test_add_and_remove_local(tmp_path, monkeypatch):
    _reset(tmp_path)
    monkeypatch.setattr(fav.favorites, "_sync_from_server", lambda: False)
    fav.favorites.add(5)
    fav.favorites.add("5")
    assert fav.favorites.get_favorites() == ["5"]
    fav.favorites.remove(5)
    assert fav.favorites.get_favorites() == []


def test_is_favorite(tmp_path, monkeypatch):
    _reset(tmp_path)
    monkeypatch.setattr(fav.favorites, "_sync_from_server", lambda: False)
    fav.favorites.add(7)
    assert fav.favorites.is_favorite(7) is True
    assert fav.favorites.is_favorite("8") is False


def test_persists_to_disk(tmp_path):
    _reset(tmp_path)
    fav.favorites._favorites = []
    fav.favorites._loaded = True
    fav.favorites.add(11)
    data = json.loads((tmp_path / "favorite_books.json").read_text(encoding="utf-8"))
    assert data == ["11"]


class _FakeFirebaseClient:
    def __init__(self, favorites):
        self._favorites = favorites
        self._initialized = True

    def is_initialized(self):
        return self._initialized

    def get_favorites(self):
        return self._favorites

    def add_favorite(self, book_id):
        self._favorites.append(str(book_id))
        return True

    def remove_favorite(self, book_id):
        self._favorites.remove(str(book_id))
        return True


def test_sync_from_server_overrides_local(tmp_path, monkeypatch):
    _reset(tmp_path)
    fcm = importlib.import_module("src.core.firebase_client")
    fake = _FakeFirebaseClient(["9"])
    monkeypatch.setattr(fcm, "firebase_client", fake)
    monkeypatch.setattr(fav.favorites, "_loaded", False)

    fav.favorites.load()
    assert fav.favorites.get_favorites() == ["9"]
    assert json.loads((tmp_path / "favorite_books.json").read_text(encoding="utf-8")) == ["9"]


def test_add_syncs_to_server(tmp_path, monkeypatch):
    _reset(tmp_path)
    fcm = importlib.import_module("src.core.firebase_client")
    fake = _FakeFirebaseClient([])
    monkeypatch.setattr(fcm, "firebase_client", fake)
    monkeypatch.setattr(fav.favorites, "_loaded", False)

    fav.favorites.add(3)
    assert fav.favorites.is_favorite(3) is True
    assert fake._favorites == ["3"]
