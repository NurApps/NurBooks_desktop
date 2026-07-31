from rate_limit import RateLimitMiddleware
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.testclient import TestClient


def _make_client(max_requests: int = 3):
    app = Starlette()

    async def route(request):
        return JSONResponse({"ok": True})

    app.add_route("/test", route, methods=["GET"])
    app.add_middleware(RateLimitMiddleware, max_requests=max_requests, window_seconds=60)
    return TestClient(app)


def test_under_limit_ok():
    client = _make_client(max_requests=3)
    for _ in range(3):
        assert client.get("/test").status_code == 200


def test_over_limit_429():
    client = _make_client(max_requests=3)
    for _ in range(3):
        client.get("/test")
    r = client.get("/test")
    assert r.status_code == 429


def test_window_expires():
    client = _make_client(max_requests=1)
    assert client.get("/test").status_code == 200
    assert client.get("/test").status_code == 429
    client.app.state = None
    client.close()
    new_client = _make_client(max_requests=1)
    assert new_client.get("/test").status_code == 200


def test_exempt_path_not_limited():
    app = Starlette()

    async def route(request):
        return JSONResponse({"ok": True})

    app.add_route("/health", route, methods=["GET"])
    app.add_middleware(RateLimitMiddleware, max_requests=1, window_seconds=60, exempt_paths=["/health"])
    client = TestClient(app)
    for _ in range(3):
        assert client.get("/health").status_code == 200
