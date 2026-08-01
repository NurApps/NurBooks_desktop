import importlib
import json
from unittest.mock import patch

import pytest

fc = importlib.import_module("src.core.firebase_client")


@pytest.fixture(autouse=True)
def _reset_session(tmp_path):
    fc.auth_session.clear()
    fc._AUTH_TOKEN_FILE = str(tmp_path / "auth.json")
    yield
    fc.auth_session.clear()


def _fake_response(payload: dict, status: int = 200):
    class FakeResp:
        def __init__(self):
            self.status = status

        def read(self):
            return json.dumps(payload).encode()

    return FakeResp()


def test_auth_request_success():
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({"idToken": "tok", "localId": "u1"})):
        data = fc._auth_request("signUp", {"returnSecureToken": True})
    assert data["idToken"] == "tok"


def test_sign_in_anonymous(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "_AUTH_TOKEN_FILE", str(tmp_path / "auth.json"))
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({
        "idToken": "tok-anon", "localId": "u-anon", "expiresIn": "3600",
    })):
        uid = fc.firebase_client.sign_in_anonymous()
    assert uid == "u-anon"
    assert fc.auth_session.token == "tok-anon"
    assert fc.firebase_client.get_current_user()["uid"] == "u-anon"


def test_sign_in_email(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "_AUTH_TOKEN_FILE", str(tmp_path / "auth.json"))
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({
        "idToken": "tok-mail", "localId": "u-mail", "email": "a@b.c", "expiresIn": "3600",
    })):
        uid = fc.firebase_client.sign_in_with_email("a@b.c", "secret")
    assert uid == "u-mail"
    assert fc.firebase_client.get_current_user()["email"] == "a@b.c"


def test_sign_in_auth_error_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "_AUTH_TOKEN_FILE", str(tmp_path / "auth.json"))

    class FakeHTTPError(Exception):
        code = 400

        def read(self):
            return b'{"error": {"message": "INVALID_PASSWORD"}}'

    with patch.object(fc.urllib.request, "urlopen", side_effect=FakeHTTPError()):
        uid = fc.firebase_client.sign_in_with_email("a@b.c", "wrong")
    assert uid is None
    assert fc.firebase_client.get_current_user() is None


def test_sign_out(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "_AUTH_TOKEN_FILE", str(tmp_path / "auth.json"))
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({
        "idToken": "tok", "localId": "u1", "expiresIn": "3600",
    })):
        fc.firebase_client.sign_in_anonymous()
    fc.firebase_client.sign_out()
    assert fc.auth_session.token is None
    assert fc.firebase_client.get_current_user() is None


def test_request_attaches_bearer_token(monkeypatch, tmp_path):
    monkeypatch.setattr(fc, "_AUTH_TOKEN_FILE", str(tmp_path / "auth.json"))
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({
        "idToken": "tok", "localId": "u1", "expiresIn": "3600",
    })):
        fc.firebase_client.sign_in_anonymous()

    captured = {}

    def fake_urlopen(req, timeout=10):
        captured["headers"] = dict(req.headers)
        return _fake_response([{"id": 1, "title": "T"}])

    with patch.object(fc.urllib.request, "urlopen", side_effect=fake_urlopen):
        fc._get("/books")
    assert captured["headers"].get("Authorization") == "Bearer tok"


def test_get_favorites(monkeypatch):
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({"favorites": [1, 2]})):
        assert fc.firebase_client.get_favorites() == ["1", "2"]


def test_get_favorites_empty(monkeypatch):
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({})):
        assert fc.firebase_client.get_favorites() == []


def test_add_favorite(monkeypatch):
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({"status": "success"})):
        assert fc.firebase_client.add_favorite(42) is True


def test_remove_favorite(monkeypatch):
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response({}, status=200)):
        assert fc.firebase_client.remove_favorite(42) is True


def test_get_reading_history(monkeypatch):
    payload = [{"bookId": 1, "page": 5, "book": {"id": 1}}]
    with patch.object(fc.urllib.request, "urlopen", return_value=_fake_response(payload)):
        assert fc.firebase_client.get_reading_history() == payload
