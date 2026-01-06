import pytest

from dyne.app import App
from dyne.exceptions import abort


def test_custom_404_handler():
    app = App(debug=False)

    @app.error_handler(404)
    async def not_found(req, resp, exc):
        resp.status_code = 404
        resp.text = "Oops! We couldn't find that page."

    r = app.client.get("/this-route-does-not-exist")

    assert r.status_code == 404
    assert r.text == "Oops! We couldn't find that page."


def test_custom_500_handler():
    app = App(debug=False)

    @app.error_handler(500)
    async def server_error(req, resp, exc):
        resp.status_code = 500
        resp.text = f"Server Error: {str(exc)}"

    @app.route("/crash")
    async def crash_route(req, resp):
        raise ValueError("Database connection failed")

    r = app.client.get("/crash")

    assert r.status_code == 500
    assert "Database connection failed" in r.text


def test_debug_mode_re_raises():
    app = App(debug=True)

    @app.route("/error")
    async def error_route(req, resp):
        raise TypeError("Something went wrong")

    with pytest.raises(TypeError):
        app.client.get("/error")


def test_specific_status_handler():
    app = App(debug=False)

    @app.error_handler(403)
    async def forbidden(req, resp, exc):
        resp.status_code = 403
        resp.media = {"error": "Access Denied"}

    @app.route("/secret")
    async def secret(req, resp):
        abort(403)

    r = app.client.get("/secret")

    assert r.status_code == 403
    assert r.json() == {"error": "Access Denied"}


def test_no_error_no_debug(app):
    app.debug = False

    @app.route("/", methods=["POST"])
    async def route(req, resp):
        resp.media = await req.media()

    dump = {"complicated": "times"}
    r = app.client.post(app.url_for(route), data=dump)
    assert r.json() == dump

    files = {"complicated": (None, "times")}
    r = app.client.post(app.url_for(route), files=files)

    assert r.status_code == 500
    assert r.text == "500 Internal Server Error"
