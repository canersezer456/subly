"""Pre-scaffolded pytest fixtures for the FastAPI backend.

Tests hit the live uvicorn process managed by supervisor (not an in-process ASGI app), so
the app under test is the same one the frontend and Playwright see. Do NOT re-create this
file — add app-specific fixtures below the marker at the bottom.
"""

import os

# Router-level unit tests import lib.db, which reads MONGO_URL/DB_NAME at import time.
# Those tests swap in fake collections, and Motor never connects on construction, so a
# deliberately unreachable placeholder is enough — no real MongoDB is ever contacted.
os.environ["MONGO_URL"] = "mongodb://127.0.0.1:1/?serverSelectionTimeoutMS=100"
os.environ["DB_NAME"] = "subly_unit_tests"
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

# Never import Motor or connect to an existing application's database in tests.
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from isolated_store import install
isolated_db = install()

# Legacy HTTP suites require a separately provisioned disposable server. Their
# default target must never be a developer's already-running application.
import socket
import threading
import time
import atexit
import uvicorn
from isolated_store import create_app

# Reserve our own socket: never reuse a pre-existing localhost service.
_test_socket = socket.socket()
_test_socket.bind(("127.0.0.1", 0))
_test_server = uvicorn.Server(uvicorn.Config(create_app(), log_level="error", access_log=False))
_test_thread = threading.Thread(target=lambda: _test_server.run(sockets=[_test_socket]), daemon=True)
_test_thread.start()
for _ in range(100):
    if _test_server.started:
        break
    time.sleep(0.02)
else:
    raise RuntimeError("Disposable test server failed to start")
_test_url = f"http://127.0.0.1:{_test_socket.getsockname()[1]}"
os.environ["BACKEND_URL"] = _test_url
os.environ["REACT_APP_BACKEND_URL"] = _test_url


def _stop_test_server():
    _test_server.should_exit = True
    _test_thread.join(timeout=5)


atexit.register(_stop_test_server)

import httpx
import pytest
import pytest_asyncio

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
API_URL = f"{BACKEND_URL}/api"


def api_url(path: str = "") -> str:
    """Absolute URL for an /api route: api_url("/status") -> http://localhost:8001/api/status."""
    return f"{API_URL}{path}"


@pytest.fixture(scope="session")
def backend_url() -> str:
    return BACKEND_URL


@pytest.fixture
def client():
    """Sync httpx client rooted at /api — the default for endpoint tests.

    Example:
        def test_status(client):
            assert client.get("/status").status_code == 200
    """
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        yield c


@pytest_asyncio.fixture
async def aclient():
    """Async variant, for tests that also await motor/backend helpers directly."""
    async with httpx.AsyncClient(base_url=API_URL, timeout=30.0) as c:
        yield c


# --- app-specific fixtures below this line ---

import uuid  # noqa: E402


def _register_and_auth(prefix: str = "isotest") -> httpx.Client:
    """Register a brand-new, uniquely-emailed user and return an httpx.Client
    authenticated as that user via an Authorization: Bearer header.

    Why Bearer and not the cookie jar: /auth/register's session cookie is
    Secure + SameSite=None (correct, required behavior for a real browser
    over production HTTPS). httpx's cookie jar will not re-attach a Secure
    cookie to a plain http://localhost request, so a client relying on the
    jar would get 401 on every request after a successful register/login.
    get_current_user() (lib/auth.py) already supports a Bearer token as a
    fallback, so tests use that instead of weakening any cookie attribute.
    """
    c = httpx.Client(base_url=API_URL, timeout=30.0)
    email = f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"
    r = c.post("/auth/register", json={"name": "Isolation Test User", "email": email, "password": "TestPass123!"})
    assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
    token = r.cookies.get("session_token")
    assert token, "no session_token cookie returned from register"
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def _self_delete(c: httpx.Client) -> None:
    # Each test account deletes only itself (DELETE /account, scoped to the
    # calling user's own user_id) so repeated test runs don't leave orphan
    # throwaway accounts piling up in the real database. Best-effort: a
    # failed cleanup must never fail the test that already passed/failed.
    try:
        c.delete("/account")
    except Exception:
        pass
    c.close()


@pytest.fixture
def new_user() -> httpx.Client:
    """A single fresh, isolated, authenticated user session for the test."""
    c = _register_and_auth()
    yield c
    _self_delete(c)


@pytest.fixture
def make_user():
    """Factory fixture: call make_user() as many times as needed in one test
    to get independent, isolated authenticated users (e.g. User A / User B
    for cross-user isolation tests). Each call registers a brand-new account.
    """
    clients: list[httpx.Client] = []

    def _make(prefix: str = "isotest") -> httpx.Client:
        c = _register_and_auth(prefix)
        clients.append(c)
        return c

    yield _make
    for c in clients:
        _self_delete(c)
