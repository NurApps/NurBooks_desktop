import importlib
import json

wl = importlib.import_module("src.core.wishlist")


def _reset(tmp_path):
    wl.wishlist._file_path = str(tmp_path / "wishlist.json")
    wl.wishlist._wishlist = []
    wl.wishlist._loaded = False


def test_load_local_from_file(tmp_path):
    _reset(tmp_path)
    p = tmp_path / "wishlist.json"
    p.write_text(json.dumps(["1", "2"]), encoding="utf-8")
    wl.wishlist._file_path = str(p)
    wl.wishlist._loaded = False
    wl.wishlist._load_local()
    assert wl.wishlist.get_wishlist() == ["1", "2"]


def test_add_and_remove_local(tmp_path, monkeypatch):
    _reset(tmp_path)
    monkeypatch.setattr(wl.wishlist, "_sync_from_server", lambda: False)
    wl.wishlist.add(5)
    wl.wishlist.add("5")
    assert wl.wishlist.get_wishlist() == ["5"]
    wl.wishlist.remove(5)
    assert wl.wishlist.get_wishlist() == []


def test_is_in_wishlist(tmp_path, monkeypatch):
    _reset(tmp_path)
    monkeypatch.setattr(wl.wishlist, "_sync_from_server", lambda: False)
    wl.wishlist.add(7)
    assert wl.wishlist.is_in_wishlist(7) is True
    assert wl.wishlist.is_in_wishlist("8") is False


def test_persists_to_disk(tmp_path):
    _reset(tmp_path)
    wl.wishlist._wishlist = []
    wl.wishlist._loaded = True
    wl.wishlist.add(11)
    data = json.loads((tmp_path / "wishlist.json").read_text(encoding="utf-8"))
    assert data == ["11"]


class _FakeFirebaseClient:
    def __init__(self, wishlist):
        self._wishlist = wishlist
        self._initialized = True

    def is_initialized(self):
        return self._initialized

    def get_wishlist(self):
        return self._wishlist

    def add_wishlist(self, book_id):
        self._wishlist.append(str(book_id))
        return True

    def remove_wishlist(self, book_id):
        self._wishlist.remove(str(book_id))
        return True


def test_sync_from_server_overrides_local(tmp_path, monkeypatch):
    _reset(tmp_path)
    fcm = importlib.import_module("src.core.firebase_client")
    fake = _FakeFirebaseClient(["9"])
    monkeypatch.setattr(fcm, "firebase_client", fake)
    monkeypatch.setattr(wl.wishlist, "_loaded", False)

    wl.wishlist.load()
    assert wl.wishlist.get_wishlist() == ["9"]


def test_add_syncs_to_server(tmp_path, monkeypatch):
    _reset(tmp_path)
    fcm = importlib.import_module("src.core.firebase_client")
    fake = _FakeFirebaseClient([])
    monkeypatch.setattr(fcm, "firebase_client", fake)
    monkeypatch.setattr(wl.wishlist, "_loaded", False)

    wl.wishlist.add(3)
    assert wl.wishlist.is_in_wishlist(3) is True
    assert fake._wishlist == ["3"]
