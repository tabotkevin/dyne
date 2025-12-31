import pytest


@pytest.mark.asyncio
async def test_app_state_persistence(api):
    """Test that state persists across multiple different requests."""
    api.state.counter = 0

    @api.route("/increment")
    async def increment(req, resp):
        req.app.state.counter += 1
        resp.media = {"count": req.app.state.counter}

    # First request
    r1 = api.client.get("/increment")
    assert r1.json()["count"] == 1

    # Second request
    r2 = api.client.get("/increment")
    assert r2.json()["count"] == 2
    assert api.state.counter == 2


@pytest.mark.asyncio
async def test_state_isolation(api):
    """Ensure req.state (request) and req.app.state (global) do not interfere."""
    api.state.global_val = "global"

    @api.route("/check-isolation")
    async def check_iso(req, resp):
        req.state.local_val = "local"
        resp.media = {
            "has_global": hasattr(req.state, "global_val"),
            "has_local_in_app": hasattr(req.app.state, "local_val"),
        }

    r = api.client.get("/check-isolation")
    data = r.json()

    assert data["has_global"] is False
    assert data["has_local_in_app"] is False


@pytest.mark.asyncio
async def test_app_state_attribute_error(api):
    """Accessing a non-existent state attribute should raise AttributeError."""

    @api.route("/error")
    async def error_route(req, resp):
        val = req.app.state.missing_key
        resp.text = val

    with pytest.raises(AttributeError) as err:  # noqa: F841
        r = api.client.get("/error")  # noqa: F841


@pytest.mark.asyncio
async def test_lifespan_state_integration(api):
    """Test that startup handlers correctly populate state"""

    @api.on_event("startup")
    async def setup():
        api.state.plugin_loaded = True

    @api.route("/plugin")
    async def get_plugin(req, resp):
        resp.media = {"loaded": getattr(req.app.state, "plugin_loaded", False)}

    await api.router.trigger_event("startup")

    r = api.client.get("/plugin")
    assert r.json()["loaded"] is True


@pytest.mark.asyncio
async def test_shutdown_state_modification(api):
    """Test that shutdown handlers can modify and clean up app.state."""
    api.state.is_active = True

    @api.on_event("shutdown")
    async def teardown():
        api.state.is_active = False
        api.state.cleanup_complete = True

    await api.router.trigger_event("shutdown")

    assert api.state.is_active is False
    assert api.state.cleanup_complete is True


@pytest.mark.asyncio
async def test_shutdown_sync_handler(api):
    """Ensure synchronous shutdown handlers also work with app.state."""
    api.state.processed_items = ["item1", "item2"]

    @api.on_event("shutdown")
    def sync_teardown():
        api.state.processed_items.clear()

    await api.router.trigger_event("shutdown")

    assert len(api.state.processed_items) == 0


@pytest.mark.asyncio
async def test_full_lifespan_flow(api):
    """Test the full flow: Startup sets state, Route uses it, Shutdown cleans it."""

    @api.on_event("startup")
    async def startup():
        api.state.db_session = "CONNECTED"

    @api.on_event("shutdown")
    async def shutdown():
        api.state.db_session = "DISCONNECTED"

    @api.route("/db-status")
    async def db_status(req, resp):
        resp.media = {"status": req.app.state.db_session}

    await api.router.trigger_event("startup")
    assert api.state.db_session == "CONNECTED"

    r = api.client.get("/db-status")
    assert r.json()["status"] == "CONNECTED"

    await api.router.trigger_event("shutdown")
    assert api.state.db_session == "DISCONNECTED"
