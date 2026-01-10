from unittest.mock import AsyncMock

import pytest

from dyne.ext.db.alchemical import AlchemicalMiddleware


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
