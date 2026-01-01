import pytest


@pytest.mark.asyncio
async def test_app_state_persistence(app):
    """Test that state persists across multiple different requests."""
    app.state.counter = 0

    @app.route("/increment")
    async def increment(req, resp):
        req.app.state.counter += 1
        resp.media = {"count": req.app.state.counter}

    # First request
    r1 = app.client.get("/increment")
    assert r1.json()["count"] == 1

    # Second request
    r2 = app.client.get("/increment")
    assert r2.json()["count"] == 2
    assert app.state.counter == 2


@pytest.mark.asyncio
async def test_state_isolation(app):
    """Ensure req.state (request) and req.app.state (global) do not interfere."""
    app.state.global_val = "global"

    @app.route("/check-isolation")
    async def check_iso(req, resp):
        req.state.local_val = "local"
        resp.media = {
            "has_global": hasattr(req.state, "global_val"),
            "has_local_in_app": hasattr(req.app.state, "local_val"),
        }

    r = app.client.get("/check-isolation")
    data = r.json()

    assert data["has_global"] is False
    assert data["has_local_in_app"] is False


@pytest.mark.asyncio
async def test_app_state_attribute_error(app):
    """Accessing a non-existent state attribute should raise AttributeError."""

    @app.route("/error")
    async def error_route(req, resp):
        val = req.app.state.missing_key
        resp.text = val

    with pytest.raises(AttributeError) as err:  # noqa: F841
        r = app.client.get("/error")  # noqa: F841


@pytest.mark.asyncio
async def test_lifespan_state_integration(app):
    """Test that startup handlers correctly populate state"""

    @app.on_event("startup")
    async def setup():
        app.state.plugin_loaded = True

    @app.route("/plugin")
    async def get_plugin(req, resp):
        resp.media = {"loaded": getattr(req.app.state, "plugin_loaded", False)}

    await app.router.trigger_event("startup")

    r = app.client.get("/plugin")
    assert r.json()["loaded"] is True


@pytest.mark.asyncio
async def test_shutdown_state_modification(app):
    """Test that shutdown handlers can modify and clean up app.state."""
    app.state.is_active = True

    @app.on_event("shutdown")
    async def teardown():
        app.state.is_active = False
        app.state.cleanup_complete = True

    await app.router.trigger_event("shutdown")

    assert app.state.is_active is False
    assert app.state.cleanup_complete is True


@pytest.mark.asyncio
async def test_shutdown_sync_handler(app):
    """Ensure synchronous shutdown handlers also work with app.state."""
    app.state.processed_items = ["item1", "item2"]

    @app.on_event("shutdown")
    def sync_teardown():
        app.state.processed_items.clear()

    await app.router.trigger_event("shutdown")

    assert len(app.state.processed_items) == 0


@pytest.mark.asyncio
async def test_full_lifespan_flow(app):
    """Test the full flow: Startup sets state, Route uses it, Shutdown cleans it."""

    @app.on_event("startup")
    async def startup():
        app.state.db_session = "CONNECTED"

    @app.on_event("shutdown")
    async def shutdown():
        app.state.db_session = "DISCONNECTED"

    @app.route("/db-status")
    async def db_status(req, resp):
        resp.media = {"status": req.app.state.db_session}

    await app.router.trigger_event("startup")
    assert app.state.db_session == "CONNECTED"

    r = app.client.get("/db-status")
    assert r.json()["status"] == "CONNECTED"

    await app.router.trigger_event("shutdown")
    assert app.state.db_session == "DISCONNECTED"
