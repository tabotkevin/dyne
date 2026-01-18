from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from itsdangerous import TimestampSigner

from dyne.ext.auth import AuthFailureReason, LoginManager, LoginMiddleware
from dyne.models import Request, Response


@pytest.fixture
def app_mock():
    class App:
        def __init__(self):
            self.state = SimpleNamespace()
            self._middleware = []

        @property
        def config(self):
            class Cfg:
                @staticmethod
                def require(key):
                    return "secret"

            return Cfg()

        def add_middleware(self, cls, **kwargs):
            self._middleware.append((cls, kwargs))

        def has_middleware(self, cls):
            return any(m[0] == cls for m in self._middleware)

    return App()


@pytest.fixture
def login_manager(app_mock):
    lm = LoginManager(login_url="/login")
    lm.init_app(app_mock)
    return lm


@pytest.fixture
def dummy_user():
    return {"id": "123", "name": "Alice"}


@pytest.fixture
def request_mock():
    scope = {"type": "http", "headers": [], "path": "/home", "query_string": b""}
    req = Request(scope, receive=lambda: None)

    # Add session dict (SessionMiddleware would do this normally)
    req._starlette.scope["session"] = {}
    return req


@pytest.fixture
def response_mock(request_mock):
    return Response(req=request_mock, formats={})


@pytest.mark.asyncio
async def test_safe_url_check(login_manager):
    assert login_manager._is_safe_url("/local/path", "testserver") is True
    assert login_manager._is_safe_url("http://testserver/path", "testserver") is True
    assert login_manager._is_safe_url("http://malicious.com", "testserver") is False
    assert login_manager._is_safe_url("//malicious.com", "testserver") is False


@pytest.mark.asyncio
async def test_load_current_user_session(login_manager, request_mock, dummy_user):
    @login_manager.user_loader
    async def load(uid):
        assert uid == "123"
        return dummy_user

    request_mock.session[login_manager.USER_ID_KEY] = "123"

    user = await login_manager._load_current_user(request_mock)
    assert user == dummy_user
    assert request_mock.state.user == dummy_user


@pytest.mark.asyncio
async def test_load_current_user_cookie(login_manager, request_mock, dummy_user):
    @login_manager.user_loader
    async def load(uid):
        return dummy_user

    signer = TimestampSigner(
        str(login_manager.secret_key), salt=login_manager.remember_me_cookie_name
    )
    request_mock._starlette._headers = {}  # no headers
    request_mock._cookies = {
        login_manager.remember_me_cookie_name: signer.sign(b"123").decode()
    }

    user = await login_manager._load_current_user(request_mock)
    assert user == dummy_user
    assert request_mock.session[login_manager.USER_ID_KEY] == "123"
    assert request_mock.state.user == dummy_user


@pytest.mark.asyncio
async def test_login_sets_session_and_cookie(
    login_manager, request_mock, response_mock, dummy_user
):
    await login_manager.login(
        request_mock,
        response_mock,
        dummy_user,
        remember_me=True,
        redirect_url="/dashboard",
    )

    assert request_mock.session[login_manager.USER_ID_KEY] == "123"
    assert request_mock.state.user == dummy_user

    cookie = response_mock.cookies[login_manager.remember_me_cookie_name]
    assert cookie.value != ""
    assert cookie["httponly"]
    assert cookie["samesite"] == "lax"
    assert response_mock.status_code == HTTPStatus.FOUND
    assert response_mock.headers["Location"] == "/dashboard"


@pytest.mark.asyncio
async def test_logout_clears_session_and_cookie(
    login_manager, request_mock, response_mock, dummy_user
):
    request_mock.session[login_manager.USER_ID_KEY] = "123"
    request_mock.state.user = dummy_user

    await login_manager.logout(request_mock, response_mock)

    assert login_manager.USER_ID_KEY not in request_mock.session
    assert request_mock.state.user is None
    cookie = response_mock.cookies[login_manager.remember_me_cookie_name]
    assert cookie["max-age"] == 0
    assert "1970" in cookie["expires"]


@pytest.mark.asyncio
async def test_login_required_decorator_allows_authenticated(
    login_manager, request_mock, response_mock, dummy_user
):
    @login_manager.user_loader
    async def load(uid):
        return dummy_user

    @login_manager.login_required()
    async def view(req, resp):
        return "ok"

    request_mock.session[LoginManager.USER_ID_KEY] = "123"
    result = await view(request_mock, response_mock)
    assert result == "ok"


@pytest.mark.asyncio
async def test_login_required_decorator_blocks_unauthenticated(
    login_manager, request_mock, response_mock
):
    @login_manager.user_loader
    async def load(uid):
        return None

    @login_manager.login_required()
    async def view(req, resp):
        return "ok"

    r = await view(request_mock, response_mock)
    assert isinstance(r, type(response_mock))
    assert r.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FOUND)


@pytest.mark.asyncio
async def test_authorization_or_and_roles(login_manager, dummy_user):
    @login_manager.get_user_roles
    async def roles(user):
        return ["editor", "user"]

    # OR
    assert await login_manager._authorize(["admin", "editor"], dummy_user)
    # AND
    assert await login_manager._authorize([["editor", "user"]], dummy_user)
    # Not authorized
    assert not await login_manager._authorize([["admin", "editor"]], dummy_user)


@pytest.mark.asyncio
async def test_default_failure_redirect(login_manager, request_mock, response_mock):
    resp = await login_manager.default_failure(
        request_mock, response_mock, AuthFailureReason.UNAUTHENTICATED
    )

    assert response_mock.status_code == HTTPStatus.FOUND
    assert resp.headers["Location"] == "/login?next=/home"


@pytest.mark.asyncio
async def test_unsign_cookie_invalid(login_manager, request_mock):
    request_mock.cookies[login_manager.remember_me_cookie_name] = "invalid"
    val = login_manager._unsign_cookie(
        request_mock, login_manager.remember_me_cookie_name
    )
    assert val is None


@pytest.mark.asyncio
async def test_login_logout_hooks(
    login_manager, request_mock, response_mock, dummy_user
):
    login_hook = AsyncMock()
    logout_hook = AsyncMock()

    login_manager.on_login(login_hook)
    login_manager.on_logout(logout_hook)

    await login_manager.login(request_mock, response_mock, dummy_user)
    login_hook.assert_called_once_with(request_mock, response_mock, dummy_user)

    request_mock.state.user = dummy_user
    await login_manager.logout(request_mock, response_mock)
    logout_hook.assert_called_once_with(request_mock, response_mock, dummy_user)


@pytest.mark.asyncio
async def test_middleware_injection(login_manager, dummy_user):
    """Fixes KeyError: 'headers' by providing minimal scope requirements."""
    mock_app = AsyncMock()
    middleware = LoginMiddleware(mock_app, login_manager)

    scope = {"type": "http", "method": "GET", "path": "/", "headers": [], "state": {}}
    receive = AsyncMock()
    send = AsyncMock()

    with patch.object(login_manager, "_load_current_user", return_value=dummy_user):
        await middleware(scope, receive, send)
        assert scope["state"]["user"] == dummy_user
        mock_app.assert_called_once()
