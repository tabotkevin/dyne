from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from dyne.ext.db.alchemical import Alchemical, AlchemicalMiddleware, CRUDMixin
from dyne.models import Request


@pytest.mark.asyncio
async def test_session_is_created_lazily():
    created = False

    class FakeSession:
        async def close(self):
            pass

    class FakeDB:
        def Session(self):
            nonlocal created
            created = True
            return FakeSession()

    async def app(scope, receive, send):
        # Do NOT access req.db
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = AlchemicalMiddleware(app, db=FakeDB())

    scope = {"type": "http", "state": {}}

    await middleware(scope, None, AsyncMock())

    assert created is False


@pytest.mark.asyncio
async def test_session_reused_within_request():
    sessions = []

    class FakeSession:
        async def close(self):
            pass

    class FakeDB:
        def Session(self):
            s = FakeSession()
            sessions.append(s)
            return s

    async def app(scope, receive, send):
        get_session = scope["state"]["db"]
        s1 = await get_session()
        s2 = await get_session()
        assert s1 is s2

        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = AlchemicalMiddleware(app, db=FakeDB())

    scope = {"type": "http", "state": {}}
    await middleware(scope, None, AsyncMock())

    assert len(sessions) == 1


@pytest.mark.asyncio
async def test_rollback_on_exception():
    rolled_back = False

    class FakeSession:
        async def rollback(self):
            nonlocal rolled_back
            rolled_back = True

        async def close(self):
            pass

    class FakeDB:
        def Session(self):
            return FakeSession()

    async def app(scope, receive, send):
        get_session = scope["state"]["db"]
        await get_session()
        raise ValueError("boom")

    middleware = AlchemicalMiddleware(app, db=FakeDB())

    scope = {"type": "http", "state": {}}

    with pytest.raises(ValueError):
        await middleware(scope, None, AsyncMock())

    assert rolled_back is True


@pytest.mark.asyncio
async def test_autocommit_commits_and_closes():
    committed = False
    closed = False

    class FakeSession:
        async def commit(self):
            nonlocal committed
            committed = True

        async def close(self):
            nonlocal closed
            closed = True

    class FakeDB:
        def Session(self):
            return FakeSession()

    async def app(scope, receive, send):
        get_session = scope["state"]["db"]
        await get_session()

        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = AlchemicalMiddleware(
        app,
        db=FakeDB(),
        autocommit=True,
    )

    scope = {"type": "http", "state": {}}
    await middleware(scope, None, AsyncMock())

    assert committed is True
    assert closed is True


class DummyReq:
    state = {}

    @property
    async def db(self):
        get_session = self.state.get("db")
        if get_session is None:
            raise RuntimeError("Database session not available")
        return await get_session()


@pytest.mark.asyncio
async def test_req_db_raises_when_not_in_request():
    req = DummyReq()
    with pytest.raises(RuntimeError):
        await req.db


class AsyncContextManagerMock:
    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, exc_type, exc, tb):
        pass


@pytest.fixture
def db_instance():
    return Alchemical()


@pytest.fixture
def mock_req():
    session = MagicMock()

    session.in_transaction = MagicMock(return_value=False)

    session.begin = MagicMock(return_value=AsyncContextManagerMock())

    req = MagicMock(spec=Request)

    async def get_db_coro():
        return session

    # This ensures that calling req.db (via the property) returns the coroutine
    type(req).db = PropertyMock(side_effect=get_db_coro)

    return req, session


def test_init_app_configuration(db_instance):
    mock_app = MagicMock()
    mock_app.config.require.return_value = "sqlite+aiosqlite:///:memory:"
    mock_app.config.get.side_effect = lambda key, **kwargs: {
        "ALCHEMICAL_BINDS": None,
        "ALCHEMICAL_ENGINE_OPTIONS": {"echo": True},
        "ALCHEMICAL_AUTOCOMMIT": True,
    }.get(key, kwargs.get("default"))

    db_instance.init_app(mock_app)

    assert mock_app.state.db == db_instance
    assert CRUDMixin._session_provider is not None
    mock_app.add_middleware.assert_called_once()


@pytest.mark.asyncio
async def test_transaction_decorator_success(db_instance, mock_req):
    req, session = mock_req

    @db_instance.transaction
    async def my_route(req, resp=None):
        return "done"

    result = await my_route(req)

    assert result == "done"
    session.begin.assert_called_once()
    session.in_transaction.assert_called_once()


@pytest.mark.asyncio
async def test_transaction_discovery_in_args(db_instance, mock_req):
    req, session = mock_req

    class MyView:
        @db_instance.transaction
        async def post(self, req):
            return "ok"

    view = MyView()
    result = await view.post(req)

    assert result == "ok"
    session.begin.assert_called_once()


@pytest.mark.asyncio
async def test_transaction_discovery_in_kwargs(db_instance, mock_req):
    req, session = mock_req

    @db_instance.transaction
    async def kwarg_route(**kwargs):
        return "ok"

    result = await kwarg_route(req=req)

    assert result == "ok"
    session.begin.assert_called_once()


@pytest.mark.asyncio
async def test_transaction_raises_on_non_async(db_instance):
    with pytest.raises(TypeError, match="@transaction requires an async function"):

        @db_instance.transaction
        def sync_route(req):
            pass


@pytest.mark.asyncio
async def test_transaction_raises_when_req_missing(db_instance):
    @db_instance.transaction
    async def ghost_route(something_else):
        pass

    with pytest.raises(RuntimeError, match="could not find the request object"):
        await ghost_route("not a request")


@pytest.mark.asyncio
async def test_nested_transaction_skips_begin(db_instance, mock_req):
    req, session = mock_req

    # Simulate being inside an existing transaction
    session.in_transaction.return_value = True

    @db_instance.transaction
    async def nested_route(req):
        return "ok"

    await nested_route(req)

    # It should enter the IF block and NOT call begin()
    session.begin.assert_not_called()


@pytest.mark.asyncio
async def test_transaction_rollback_on_exception(db_instance, mock_req):
    req, session = mock_req

    @db_instance.transaction
    async def error_route(req):
        raise ValueError("DB Fail")

    with pytest.raises(ValueError, match="DB Fail"):
        await error_route(req)

    # begin was still called; the async context manager handles the rollback
    session.begin.assert_called_once()
