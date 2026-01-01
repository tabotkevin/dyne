import io
import os
import random
import string

import pytest
import yaml
from marshmallow import Schema, fields
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient as StarletteTestClient

import dyne
from dyne import status
from dyne.routes import Route, WebSocketRoute
from dyne.templates import Templates


def test_api_basic_route(app):
    @app.route("/")
    def home(req, resp):
        resp.text = "hello world!"


def test_route_repr():
    def home(req, resp):
        """Home page"""
        resp.text = "Hello !"

    route = Route("/", home)

    assert route.__repr__() == f"<Route '/'={home!r}>"

    assert route.endpoint_name == home.__name__
    assert route.doc == home.__doc__


def test_websocket_route_repr():
    def chat_endpoint(ws):
        """Chat"""
        pass

    route = WebSocketRoute("/", chat_endpoint)

    assert route.__repr__() == f"<Route '/'={chat_endpoint!r}>"

    assert route.endpoint_name == chat_endpoint.__name__
    assert route.description == chat_endpoint.__doc__


def test_route_eq():
    def home(req, resp):
        resp.text = "Hello !"

    assert Route("/", home) == Route("/", home)

    def chat(ws):
        pass

    assert WebSocketRoute("/", home) == WebSocketRoute("/", home)


def test_class_based_view_registration(app):
    @app.route("/")
    class ThingsResource:
        def on_request(req, resp):
            resp.text = "42"


def test_class_based_view_parameters(app):
    @app.route("/{greeting}")
    class Greeting:
        pass

    resp = app.session().get("http://;/Hello")
    assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


def test_requests_session(app):
    assert app.session()
    assert app.client


def test_requests_session_works(app):
    TEXT = "spiral out"

    @app.route("/")
    def hello(req, resp):
        resp.text = TEXT

    assert app.client.get("/").text == TEXT


def test_status_code(app):
    @app.route("/")
    def hello(req, resp):
        resp.text = "keep going"
        resp.status_code = status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE

    assert app.client.get("http://;/").status_code == 416


def test_json_media(app):
    dump = {"life": 42}

    @app.route("/")
    def media(req, resp):
        resp.media = dump

    r = app.client.get("http://;/")

    assert "json" in r.headers["Content-Type"]
    assert r.json() == dump


def test_yaml_media(app):
    dump = {"life": 42}

    @app.route("/")
    def media(req, resp):
        resp.media = dump

    r = app.client.get("http://;/", headers={"Accept": "yaml"})

    assert "yaml" in r.headers["Content-Type"]
    assert yaml.load(r.content, Loader=yaml.FullLoader) == dump


def test_graphql_schema_query_querying(app, schema):
    app.add_route("/graphql", dyne.ext.GraphQLView(schema=schema, app=app))

    r = app.client.get("http://;/graphql?q={ hello }", headers={"Accept": "json"})
    assert r.json() == {"data": {"hello": "Hello stranger"}}


def test_argumented_routing(app):
    @app.route("/{name}")
    def hello(req, resp, *, name):
        resp.text = f"Hello, {name}."

    r = app.client.get(app.url_for(hello, name="sean"))
    assert r.text == "Hello, sean."


def test_mote_argumented_routing(app):
    @app.route("/{greeting}/{name}")
    def hello(req, resp, *, greeting, name):
        resp.text = f"{greeting}, {name}."

    r = app.client.get(app.url_for(hello, greeting="hello", name="lyndsy"))
    assert r.text == "hello, lyndsy."


def test_request_and_get(app):
    @app.route("/")
    class ThingsResource:
        def on_request(self, req, resp):
            resp.headers.update({"DEATH": "666"})

        def on_get(self, req, resp):
            resp.headers.update({"LIFE": "42"})

    r = app.client.get(app.url_for(ThingsResource))
    assert "DEATH" in r.headers
    assert "LIFE" in r.headers


def test_class_based_view_status_code(app):
    @app.route("/")
    class ThingsResource:
        def on_request(self, req, resp):
            resp.status_code = app.status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE

    assert app.client.get("http://;/").status_code == 416


def test_query_params(app, url):
    @app.route("/")
    def route(req, resp):
        resp.media = {"params": req.params}

    r = app.client.get(app.url_for(route), params={"q": "q"})
    assert r.json()["params"] == {"q": "q"}

    r = app.client.get(url("/?q=1&q=2&q=3"))
    assert r.json()["params"] == {"q": "3"}


# Requires https://github.com/encode/starlette/pull/102
def test_form_data(app):
    @app.route("/", methods=["POST"])
    async def route(req, resp):
        resp.media = {"form": await req.media("form")}

    dump = {"q": "q"}
    r = app.client.post(app.url_for(route), data=dump)
    assert r.json()["form"] == dump


def test_async_function(app):
    content = "The Emerald Tablet of Hermes"

    @app.route("/")
    async def route(req, resp):
        resp.text = content

    r = app.client.get(app.url_for(route))
    assert r.text == content


def test_media_parsing(app):
    dump = {"hello": "sam"}

    @app.route("/")
    def route(req, resp):
        resp.media = dump

    r = app.client.get(app.url_for(route))
    assert r.json() == dump

    r = app.client.get(app.url_for(route), headers={"Accept": "application/x-yaml"})
    assert r.text == "hello: sam\n"


def test_background(app):
    @app.route("/")
    def route(req, resp):
        @app.background.task
        def task():
            import time

            time.sleep(3)

        task()
        app.text = "ok"

    r = app.client.get(app.url_for(route))
    assert r.status_code == 200


def test_multiple_routes(app):
    @app.route("/1")
    def route1(req, resp):
        resp.text = "1"

    @app.route("/2")
    def route2(req, resp):
        resp.text = "2"

    r = app.client.get(app.url_for(route1))
    assert r.text == "1"

    r = app.client.get(app.url_for(route2))
    assert r.text == "2"


def test_graphql_schema_json_query(app, schema):
    app.add_route("/", dyne.ext.GraphQLView(schema=schema, app=app), methods=["POST"])

    r = app.client.post("http://;/", json={"query": "{ hello }"})
    assert r.status_code == 200


def test_graphiql(app, schema):
    app.add_route("/", dyne.ext.GraphQLView(schema=schema, app=app))

    r = app.client.get("http://;/", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert "GraphiQL" in r.text


def test_json_uploads(app):
    @app.route("/", methods=["POST"])
    async def route(req, resp):
        resp.media = await req.media()

    dump = {"complicated": "times"}
    r = app.client.post(app.url_for(route), json=dump)
    assert r.json() == dump


def test_yaml_uploads(app):
    @app.route("/", methods=["POST"])
    async def route(req, resp):
        resp.media = await req.media()

    dump = {"complicated": "times"}
    r = app.client.post(
        app.url_for(route),
        content=yaml.dump(dump),
        headers={"Content-Type": "application/x-yaml"},
    )
    assert r.json() == dump


def test_form_uploads(app):
    @app.route("/", methods=["POST"])
    async def route(req, resp):
        resp.media = await req.media()

    dump = {"complicated": "times"}
    r = app.client.post(app.url_for(route), data=dump)
    assert r.json() == dump

    # requests with boundary
    files = {"complicated": (None, "times")}
    with pytest.raises(Exception) as err:  # noqa: F841
        r = app.client.post(app.url_for(route), files=files)


def test_json_downloads(app):
    dump = {"testing": "123"}

    @app.route("/")
    def route(req, resp):
        resp.media = dump

    r = app.client.get(app.url_for(route), headers={"Content-Type": "application/json"})
    assert r.json() == dump


def test_yaml_downloads(app):
    dump = {"testing": "123"}

    @app.route("/")
    def route(req, resp):
        resp.media = dump

    r = app.client.get(
        app.url_for(route), headers={"Content-Type": "application/x-yaml"}
    )
    assert yaml.safe_load(r.content) == dump


def test_documentation_explicit():
    import marshmallow

    import dyne
    from dyne.ext.openapi import OpenAPI

    description = "This is a sample server for a pet store."
    terms_of_service = "http://example.com/terms/"
    contact = {
        "name": "API Support",
        "url": "http://www.example.com/support",
        "email": "support@example.com",
    }
    license = {
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    }

    app = dyne.App(allowed_hosts=["testserver", ";"])

    api = OpenAPI(
        app=app,
        title="Web Service",
        version="1.0",
        openapi="3.0.2",
        docs_route="/doc",
        description=description,
        terms_of_service=terms_of_service,
        openapi_route="/schema.yaml",
        contact=contact,
        license=license,
    )

    @api.schema("Pet")
    class PetSchema(marshmallow.Schema):
        name = marshmallow.fields.Str()

    @app.route("/")
    def route(req, resp):
        """A cute furry animal endpoint.
        ---
        get:
            description: Get a random pet
            responses:
                200:
                    description: A pet to be returned
                    schema:
                        $ref: "#/components/schemas/Pet"
        """
        resp.media = PetSchema().dump({"name": "little orange"})

    r = app.client.get("/doc")
    assert "html" in r.text


def test_documentation():
    from marshmallow import Schema, fields

    import dyne
    from dyne.ext.openapi import OpenAPI

    description = "This is a sample server for a pet store."
    terms_of_service = "http://example.com/terms/"
    contact = {
        "name": "API Support",
        "url": "http://www.example.com/support",
        "email": "support@example.com",
    }
    license = {
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    }

    app = dyne.App(allowed_hosts=["testserver", ";"])

    api = OpenAPI(
        app=app,
        title="Web Service",
        version="1.0",
        openapi="3.0.2",
        docs_route="/docs",
        description=description,
        terms_of_service=terms_of_service,
        openapi_route="/schema.yaml",
        contact=contact,
        license=license,
    )

    @api.schema("Pet")
    class PetSchema(Schema):
        name = fields.Str()

    @app.route("/")
    def route(req, resp):
        """A cute furry animal endpoint.
        ---
        get:
            description: Get a random pet
            responses:
                200:
                    description: A pet to be returned
                    schema:
                        $ref: "#/components/schemas/Pet"
        """
        resp.media = PetSchema().dump({"name": "little orange"})

    r = app.client.get("/docs")
    assert "html" in r.text


def test_mount_wsgi_app(app, flask):
    @app.route("/")
    def hello(req, resp):
        resp.text = "hello"

    app.mount("/flask", flask)

    r = app.client.get("http://;/flask")
    assert r.status_code == 200


def test_async_class_based_views(app):
    @app.route("/")
    class Resource:
        async def on_post(self, req, resp):
            resp.text = await req.text

    data = "frame"
    r = app.client.post(app.url_for(Resource), content=data)
    assert r.text == data


def test_cookies(app):
    @app.route("/")
    def home(req, resp):
        resp.media = {"cookies": req.cookies}
        resp.cookies["sent"] = "true"
        resp.set_cookie(
            "hello",
            "world",
            expires=123,
            path="/",
            max_age=123,
            secure=False,
            httponly=True,
        )

    client = app.client
    client.cookies = {"hello": "universe"}
    r = client.get(app.url_for(home))
    assert r.json() == {"cookies": {"hello": "universe"}}
    assert "sent" in r.cookies
    assert "hello" in r.cookies

    r = app.client.get(app.url_for(home))
    assert r.json() == {"cookies": {"hello": "world", "sent": "true"}}


@pytest.mark.xfail
def test_sessions(app):
    @app.route("/")
    def view(req, resp):
        resp.session["hello"] = "world"
        resp.media = resp.session

    r = app.client.get(app.url_for(view))
    assert app.session_cookie in r.cookies

    r = app.client.get(app.url_for(view))
    assert (
        r.cookies[app.session_cookie]
        == '{"hello": "world"}.r3EB04hEEyLYIJaAXCEq3d4YEbs'
    )
    assert r.json() == {"hello": "world"}


def test_template_string_rendering(app):
    @app.route("/")
    def view(req, resp):
        resp.content = app.template_string("{{ var }}", var="hello")

    r = app.client.get(app.url_for(view))
    assert r.text == "hello"


def test_template_rendering(template_path):
    app = dyne.App(templates_dir=template_path.dirpath())

    @app.route("/")
    def view(req, resp):
        resp.content = app.template(template_path.basename, var="hello")

    r = app.client.get(app.url_for(view))
    assert r.text == "hello"


def test_template(app, template_path):
    templates = Templates(directory=template_path.dirpath())

    @app.route("/{var}/")
    def view(req, resp, var):
        resp.html = templates.render(template_path.basename, var=var)

    r = app.client.get("/test/")
    assert r.text == "test"


def test_template_async(app, template_path):
    templates = Templates(directory=template_path.dirpath(), enable_async=True)

    @app.route("/{var}/async")
    async def view_async(req, resp, var):
        resp.html = await templates.render_async(template_path.basename, var=var)

    r = app.client.get("/test/async")
    assert r.text == "test"


def test_file_uploads(app):
    @app.route("/", methods=["POST"])
    async def upload(req, resp):
        files = await req.media("files")
        result = {}
        result["hello"] = files["hello"]["content"].decode("utf-8")
        resp.media = {"files": result}

    world = io.BytesIO(b"world")
    data = {"hello": ("hello.txt", world, "text/plain")}
    r = app.client.post(app.url_for(upload), files=data)
    assert r.json() == {"files": {"hello": "world"}}

    @app.route("/not_file", methods=["POST"])
    async def upload_not_file(req, resp):
        files = await req.media("files")
        result = {}
        result["not-a-file"] = files["not-a-file"].decode("utf-8")
        resp.media = {"files": result}

    world = io.BytesIO(b"world")
    data = {"not-a-file": b"data only"}
    with pytest.raises(Exception) as err:  # noqa: F841
        r = app.client.post(app.url_for(upload_not_file), files=data)


def test_500(app):
    @app.route("/")
    def view(req, resp):
        raise ValueError

    dumb_client = dyne.app.TestClient(
        app, base_url="http://;", raise_server_exceptions=False
    )
    r = dumb_client.get(app.url_for(view))
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


def test_404(app):
    r = app.client.get("/foo")

    assert r.status_code == status.HTTP_404_NOT_FOUND


def test_websockets_text(app):
    payload = "Hello via websocket!"

    @app.route("/ws", websocket=True)
    async def websocket(ws):
        await ws.accept()
        await ws.send_text(payload)
        await ws.close()

    client = StarletteTestClient(app)
    with client.websocket_connect("ws://;/ws") as websocket:  # noqa: F811
        data = websocket.receive_text()
        assert data == payload


def test_websockets_bytes(app):
    payload = b"Hello via websocket!"

    @app.route("/ws", websocket=True)
    async def websocket(ws):
        await ws.accept()
        await ws.send_bytes(payload)
        await ws.close()

    client = StarletteTestClient(app)
    with client.websocket_connect("ws://;/ws") as websocket:  # noqa: F811
        data = websocket.receive_bytes()
        assert data == payload


def test_websockets_json(app):
    payload = {"Hello": "via websocket!"}

    @app.route("/ws", websocket=True)
    async def websocket(ws):
        await ws.accept()
        await ws.send_json(payload)
        await ws.close()

    client = StarletteTestClient(app)
    with client.websocket_connect("ws://;/ws") as websocket:  # noqa: F811
        data = websocket.receive_json()
        assert data == payload


def test_before_websockets(app):
    payload = {"Hello": "via websocket!"}

    @app.route("/ws", websocket=True)
    async def websocket(ws):
        await ws.send_json(payload)
        await ws.close()

    @app.before_request(websocket=True)
    async def before_request(ws):
        await ws.accept()
        await ws.send_json({"before": "request"})

    client = StarletteTestClient(app)
    with client.websocket_connect("ws://;/ws") as websocket:  # noqa: F811
        data = websocket.receive_json()
        assert data == {"before": "request"}
        data = websocket.receive_json()
        assert data == payload


def test_startup(app):
    who = [None]

    @app.route("/{greeting}")
    async def greet_world(req, resp, *, greeting):
        resp.text = f"{greeting}, {who[0]}!"

    @app.on_event("startup")
    async def run_startup():
        who[0] = "world"

    with app.client as session:
        r = session.get("http://;/hello")
        assert r.text == "hello, world!"


def test_redirects(app, session):
    @app.route("/2")
    def two(req, resp):
        app.redirect(resp, location="/1")

    @app.route("/1")
    def one(req, resp):
        resp.text = "redirected"

    assert session.get("/2").url == "http://;/1"


def test_session_thoroughly(app, session):
    @app.route("/set")
    def set(req, resp):
        resp.session["hello"] = "world"
        app.redirect(resp, location="/get")

    @app.route("/get")
    def get(req, resp):
        resp.media = {"session": req.session}

    r = session.get(app.url_for(set))
    r = session.get(app.url_for(get))
    assert r.json() == {"session": {"hello": "world"}}


def test_before_response(app, session):
    @app.route("/get")
    def get(req, resp):
        resp.media = req.session

    @app.route(before_request=True)
    async def async_before_request(req, resp):
        resp.headers["x-pizza"] = "1"

    @app.route(before_request=True)
    def before_request(req, resp):
        resp.headers["x-pizza"] = "1"

    r = session.get(app.url_for(get))
    assert "x-pizza" in r.headers


@pytest.mark.parametrize("enable_hsts", [True, False])
@pytest.mark.parametrize("cors", [True, False])
def test_allowed_hosts(enable_hsts, cors):
    app = dyne.App(allowed_hosts=[";", "tenant.;"], enable_hsts=enable_hsts, cors=cors)

    @app.route("/")
    def get(req, resp):
        pass

    # Exact match
    r = app.client.get(app.url_for(get))
    assert r.status_code == 200

    # Reset the session
    app._session = None
    r = app.session(base_url="http://tenant.;").get(app.url_for(get))
    assert r.status_code == 200

    # Reset the session
    app._session = None
    r = app.session(base_url="http://unkownhost").get(app.url_for(get))
    assert r.status_code == 400

    # Reset the session
    app._session = None
    r = app.session(base_url="http://unkown_tenant.;").get(app.url_for(get))
    assert r.status_code == 400

    app = dyne.App(allowed_hosts=["*.;"])

    @app.route("/")
    def get(req, resp):
        pass

    # Wildcard domains
    # Using http://;
    r = app.client.get(app.url_for(get))
    assert r.status_code == 400

    # Reset the session
    app._session = None
    r = app.session(base_url="http://tenant1.;").get(app.url_for(get))
    assert r.status_code == 200

    # Reset the session
    app._session = None
    r = app.session(base_url="http://tenant2.;").get(app.url_for(get))
    assert r.status_code == 200


def create_asset(static_dir, name=None, parent_dir=None):
    if name is None:
        name = random.choices(string.ascii_letters, k=6)
        # :3
        ext = random.choices(string.ascii_letters, k=2)
        name = f"{name}.{ext}"

    if parent_dir is None:
        parent_dir = static_dir
    else:
        parent_dir = static_dir.mkdir(parent_dir)

    asset = parent_dir.join(name)
    asset.write("body { color: blue; }")
    return asset


@pytest.mark.parametrize("static_route", [None, "/static", "/custom/static/route"])
def test_staticfiles(tmpdir, static_route):
    static_dir = tmpdir.mkdir("static")

    asset1 = create_asset(static_dir)
    parent_dir = "css"
    asset2 = create_asset(static_dir, name="asset2", parent_dir=parent_dir)

    app = dyne.App(static_dir=str(static_dir), static_route=static_route)
    session = app.session()

    static_route = app.static_route

    # ok
    r = session.get(f"{static_route}/{asset1.basename}")
    assert r.status_code == app.status.HTTP_200_OK

    r = session.get(f"{static_route}/{parent_dir}/{asset2.basename}")
    assert r.status_code == app.status.HTTP_200_OK

    # Asset not found
    r = session.get(f"{static_route}/not_found.css")
    assert r.status_code == app.status.HTTP_404_NOT_FOUND

    # Not found on dir listing
    r = session.get(f"{static_route}")
    assert r.status_code == app.status.HTTP_404_NOT_FOUND

    r = session.get(f"{static_route}/{parent_dir}")
    assert r.status_code == app.status.HTTP_404_NOT_FOUND


def test_response_html_property(app):
    @app.route("/")
    def view(req, resp):
        resp.html = "<h1>Hello !</h1>"

        assert resp.content == "<h1>Hello !</h1>"
        assert resp.mimetype == "text/html"

    r = app.client.get(app.url_for(view))
    assert r.content == b"<h1>Hello !</h1>"
    assert r.headers["Content-Type"] == "text/html"


def test_response_text_property(app):
    @app.route("/")
    def view(req, resp):
        resp.text = "<h1>Hello !</h1>"

        assert resp.content == "<h1>Hello !</h1>"
        assert resp.mimetype == "text/plain"

    r = app.client.get(app.url_for(view))
    assert r.content == b"<h1>Hello !</h1>"
    assert r.headers["Content-Type"] == "text/plain"


def test_stream(app, session):
    async def shout_stream(who):
        for c in who.upper():
            yield c

    @app.route("/{who}")
    async def greeting(req, resp, *, who):
        resp.stream(shout_stream, who)

    r = session.get("/morocco")
    assert r.text == "MOROCCO"

    @app.route("/")
    async def home(req, resp):
        # Raise when it's not an async generator
        with pytest.raises(AssertionError):

            def foo():
                pass

            resp.stream(foo)

        with pytest.raises(AssertionError):

            async def foo():
                pass

            resp.stream(foo)

        with pytest.raises(AssertionError):

            def foo():
                yield "oopsie"

            resp.stream(foo)


def test_empty_req_text(app):
    content = "It's working"

    @app.route("/", methods=["POST"])
    async def home(req, resp):
        await req.text
        resp.text = content

    r = app.client.post("/")
    assert r.text == content

    def test_api_request_state(api, url):
        class StateMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                request.state.test1 = 42
                request.state.test2 = "Foo"

                response = await call_next(request)
                return response

        api.add_middleware(StateMiddleware)

        @api.route("/")
        def home(req, resp):
            resp.text = "{}_{}".format(req.state.test2, req.state.test1)

        assert api.client.get(url("/")).text == "Foo_42"


def test_path_matches_route(app):
    @app.route("/hello")
    def home(req, resp):
        resp.text = "hello world!"

    route = app.path_matches_route({"type": "http", "path": "/hello"})
    assert route.endpoint_name == "home"

    assert not app.path_matches_route({"type": "http", "path": "/foo"})


def test_route_without_endpoint(app):
    app.add_route("/")
    route = app.router.routes[0]
    assert route.endpoint_name == "_static_response"


def test_pydantic_input_request_validation(app):
    from pydantic import AliasGenerator, BaseModel, ConfigDict

    from dyne.ext.io.pydantic import input

    class BookSchema(BaseModel):
        title: str
        price: float

    class HeaderSchema(BaseModel):
        x_version: str

        model_config = ConfigDict(
            # Accept the alias even if the framework lowercased it and try converting 'x-version' to 'x_version'
            alias_generator=AliasGenerator(
                validation_alias=lambda field_name: field_name.replace("_", "-"),
            ),
            populate_by_name=True,
        )

    class CookiesSchema(BaseModel):
        max_age: int
        is_cheap: bool

    class QuerySchema(BaseModel):
        page: int = 1
        limit: int = 10

    # Media (JSON body)
    @app.route("/book", methods=["POST"])
    @input(BookSchema)
    async def create_book(req, resp, *, data):
        resp.text = "created"

        assert data == {"price": 39.99, "title": "Pragmatic Programmer"}

    # Query parameters
    @app.route("/books")
    @input(QuerySchema, location="query")
    async def list_books(req, resp, *, query):
        assert query == {"page": 2, "limit": 20}

    # Headers
    @app.route("/book/{id}", methods=["POST"])
    @input(HeaderSchema, location="header")
    async def book_version(req, resp, *, id, header):
        assert header == {"x_version": "2.4.5"}

    # Cookies
    @app.route("/")
    @input(CookiesSchema, location="cookie")
    async def home(req, resp, *, cookie):
        print(cookie)
        resp.text = "Welcome (Pydantic)"
        assert cookie == {"max_age": 123, "is_cheap": True}

    # Stacked inputs (cookies + body)
    @app.route("/store", methods=["POST"])
    @input(CookiesSchema, location="cookie", key="cookies")
    @input(BookSchema)
    async def store(req, resp, *, cookies, data):
        print(f"Cookies: {cookies}")
        assert data == {"title": "Pragmatic Programmer", "price": 39.99}
        assert cookies == {"max_age": 123, "is_cheap": True}

    # Valid media
    data = {"price": 39.99, "title": "Pragmatic Programmer"}
    response = app.client.post(app.url_for(create_book), json=data)
    assert response.status_code == app.status.HTTP_200_OK
    assert response.text == "created"

    # Valid params(query)
    response = app.client.get(app.url_for(list_books), params={"page": 2, "limit": 20})
    assert response.status_code == app.status.HTTP_200_OK

    # Valid headers
    response = app.client.post(
        app.url_for(book_version, id=1), headers={"X-Version": "2.4.5"}
    )
    assert response.status_code == app.status.HTTP_200_OK

    # Valid  cookies
    client = app.client
    client.cookies = {"max_age": "123", "is_cheap": "True"}
    response = client.get(app.url_for(home))
    assert response.status_code == app.status.HTTP_200_OK
    assert response.text == "Welcome (Pydantic)"

    # Valid  input stacking
    client = app.client
    client.cookies = {"max_age": "123", "is_cheap": "True"}
    response = client.post(
        app.url_for(store), json={"price": 39.99, "title": "Pragmatic Programmer"}
    )
    assert response.status_code == app.status.HTTP_200_OK

    # Invalid book data
    data = {"title": 123}  # Invalid data
    response = app.client.post(app.url_for(create_book), json=data)
    assert response.status_code == app.status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "errors": {
            "title": ["Input should be a valid string"],
            "price": ["Field required"],
        }
    }


def test_marshmallow_input_request_validation(app):
    from marshmallow import Schema, fields

    from dyne.ext.io.marshmallow import input

    class BookSchema(Schema):
        title = fields.String(required=True)
        price = fields.Float(required=True)

    class HeaderSchema(Schema):
        x_version = fields.String(
            data_key="X-Version",
            required=True,
        )

    class CookiesSchema(Schema):
        max_age = fields.Int(required=True)
        is_cheap = fields.Bool(required=True)

    class QuerySchema(Schema):
        page = fields.Int(load_default=1)
        limit = fields.Int(load_default=10)

    # Media (JSON body)
    @app.route("/book", methods=["POST"])
    @input(BookSchema)
    async def create_book(req, resp, *, data):
        resp.text = "created"

        assert data == {"price": 39.99, "title": "Pragmatic Programmer"}

    # Query parameters
    @app.route("/books")
    @input(QuerySchema, location="query")
    async def list_books(req, resp, *, query):
        assert query == {"page": 2, "limit": 20}

    # Headers
    @app.route("/book/{id}", methods=["POST"])
    @input(HeaderSchema, location="header")
    async def book_version(req, resp, *, id, header):
        assert header == {"x_version": "2.4.5"}

    # Cookies
    @app.route("/")
    @input(CookiesSchema, location="cookie")
    async def home(req, resp, *, cookie):
        print(cookie)
        resp.text = "Welcome (Marshmallow)"
        assert cookie == {"max_age": 123, "is_cheap": True}

    # Stacked inputs (cookies + body)
    @app.route("/store", methods=["POST"])
    @input(CookiesSchema, location="cookie", key="cookies")
    @input(BookSchema)
    async def store(req, resp, *, cookies, data):
        print(f"Cookies: {cookies}")
        assert data == {"title": "Pragmatic Programmer", "price": 39.99}
        assert cookies == {"max_age": 123, "is_cheap": True}

    # Valid media
    data = {"price": 39.99, "title": "Pragmatic Programmer"}
    response = app.client.post(app.url_for(create_book), json=data)
    assert response.status_code == app.status.HTTP_200_OK
    assert response.text == "created"

    # Valid params(query)
    response = app.client.get(app.url_for(list_books), params={"page": 2, "limit": 20})
    assert response.status_code == app.status.HTTP_200_OK

    # Valid headers
    response = app.client.post(
        app.url_for(book_version, id=1), headers={"X-Version": "2.4.5"}
    )
    assert response.status_code == app.status.HTTP_200_OK

    # Valid  cookies
    client = app.client
    client.cookies = {"max_age": "123", "is_cheap": "True"}
    response = client.get(app.url_for(home))
    assert response.status_code == app.status.HTTP_200_OK
    assert response.text == "Welcome (Marshmallow)"

    # Valid  input stacking
    client = app.client
    client.cookies = {"max_age": "123", "is_cheap": "True"}
    response = client.post(
        app.url_for(store), json={"price": 39.99, "title": "Pragmatic Programmer"}
    )
    assert response.status_code == app.status.HTTP_200_OK

    # Invalid book data
    data = {"title": 123}  # Invalid data
    response = app.client.post(app.url_for(create_book), json=data)
    assert response.status_code == app.status.HTTP_400_BAD_REQUEST
    assert response.json() == {
        "errors": {
            "title": ["Not a valid string."],
            "price": ["Missing data for required field."],
        }
    }


def test_endpoint_request_methods(app):
    @app.route("/{greeting}")
    async def greet(req, resp, *, greeting):  # defaults to get.
        resp.text = f"{greeting}, world!"

    @app.route("/me/{greeting}", methods=["POST"])
    async def greet_me(req, resp, *, greeting):
        resp.text = f"POST - {greeting}, world!"

    @app.route("/no/{greeting}")
    class NoGreeting:
        pass

    @app.route("/person/{greeting}")
    class GreetingResource:
        def on_get(self, req, resp, *, greeting):
            resp.text = f"GET person - {greeting}, world!"
            resp.headers.update({"X-Life": "41"})
            resp.status_code = app.status.HTTP_201_CREATED

        def on_post(self, req, resp, *, greeting):
            resp.text = f"POST person - {greeting}, world!"
            resp.headers.update({"X-Life": "42"})

        def on_request(self, req, resp, *, greeting):  # any request method.
            resp.text = f"any person - {greeting}, world!"
            resp.headers.update({"X-Life": "43"})

    resp = app.client.get("http://;/Hello")
    assert resp.status_code == app.status.HTTP_200_OK
    assert resp.text == "Hello, world!"

    resp = app.client.post("http://;/Hello")
    assert resp.status_code == app.status.HTTP_405_METHOD_NOT_ALLOWED

    resp = app.client.get("http://;/me/Hey")
    assert resp.status_code == app.status.HTTP_405_METHOD_NOT_ALLOWED

    resp = app.client.post("http://;/me/Hey")
    assert resp.status_code == app.status.HTTP_200_OK
    assert resp.text == "POST - Hey, world!"

    resp = app.client.get("http://;/no/Hello")
    assert resp.status_code == app.status.HTTP_405_METHOD_NOT_ALLOWED

    resp = app.client.post("http://;/no/Hello")
    assert resp.status_code == app.status.HTTP_405_METHOD_NOT_ALLOWED

    resp = app.client.get("http://;/person/Hi")
    assert resp.text == "GET person - Hi, world!"
    assert resp.headers["X-Life"] == "41"
    assert resp.status_code == app.status.HTTP_201_CREATED

    resp = app.client.post("http://;/person/Hi")
    assert resp.text == "POST person - Hi, world!"
    assert resp.headers["X-Life"] == "42"
    assert resp.status_code == app.status.HTTP_200_OK

    resp = app.client.put("http://;/person/Hi")
    assert resp.text == "any person - Hi, world!"
    assert resp.headers["X-Life"] == "43"
    assert resp.status_code == app.status.HTTP_200_OK


def test_pydantic_response_schema_serialization(app):
    from dyne.ext.io.pydantic import input, output

    class Base(DeclarativeBase):
        pass

    # Define an example SQLAlchemy model
    class Book(Base):
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)

    # Create tables in the database
    engine = create_engine("sqlite:///py.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    book1 = Book(price=9.99, title="Harry Potter")
    book2 = Book(price=10.99, title="Pirates of the sea")
    session.add(book1)
    session.add(book2)
    session.commit()

    class BaseBookSchema(BaseModel):
        price: float
        title: str
        model_config = ConfigDict(from_attributes=True)

    class BookIn(BaseBookSchema): ...

    class BookOut(BaseBookSchema):
        id: int

    @app.route("/create", methods=["POST"])
    @input(BookIn)
    @output(BookOut)
    async def create_book(req, resp, *, data):
        """Create book"""

        book = Book(**data)
        session.add(book)
        session.commit()

        resp.obj = book

    @app.route("/all")
    @output(BookOut)
    async def all_books(req, resp):
        """Get all books"""

        resp.obj = session.query(Book)

    data = {"title": "Learning dyne", "price": 39.99}
    response = app.client.post(app.url_for(create_book), json=data)
    assert response.status_code == app.status.HTTP_200_OK
    assert response.json() == {"id": 3, "price": 39.99, "title": "Learning dyne"}

    response = app.client.get(app.url_for(all_books))
    assert response.status_code == app.status.HTTP_200_OK
    rs = response.json()
    assert len(rs) == 3
    ids = sorted([book["id"] for book in rs])
    prices = sorted([book["price"] for book in rs])
    titles = sorted([book["title"] for book in rs])
    assert ids == [1, 2, 3]
    assert prices == [9.99, 10.99, 39.99]
    assert titles == ["Harry Potter", "Learning dyne", "Pirates of the sea"]
    os.remove("py.db")


def test_marshmallow_response_schema_serialization(app):
    from dyne.ext.io.marshmallow import input, output

    class Base(DeclarativeBase):
        pass

    # Define an example SQLAlchemy model
    class Book(Base):
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)

    # Create tables in the database
    engine = create_engine("sqlite:///ma.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    book1 = Book(price=9.99, title="Harry Potter")
    book2 = Book(price=10.99, title="Pirates of the sea")
    session.add(book1)
    session.add(book2)
    session.commit()

    class BookSchema(Schema):
        id = fields.Integer(dump_only=True)
        price = fields.Float()
        title = fields.Str()

        class Meta:
            model = Book

    @app.route("/create", methods=["POST"])
    @input(BookSchema)
    @output(BookSchema)
    async def create_book(req, resp, *, data):
        """Create book"""

        book = Book(**data)
        session.add(book)
        session.commit()

        resp.obj = book

    @app.route("/all")
    @output(BookSchema(many=True))
    async def all_books(req, resp):
        """Get all books"""

        resp.obj = session.query(Book)

    data = {"title": "Python Programming", "price": 11.99}
    response = app.client.post(app.url_for(create_book), json=data)
    assert response.status_code == app.status.HTTP_200_OK
    assert response.json() == {"id": 3, "price": 11.99, "title": "Python Programming"}

    response = app.client.get(app.url_for(all_books))
    assert response.status_code == app.status.HTTP_200_OK
    rs = response.json()
    assert len(rs) == 3
    ids = sorted([book["id"] for book in rs])
    prices = sorted([book["price"] for book in rs])
    titles = sorted([book["title"] for book in rs])
    assert ids == [1, 2, 3]
    assert prices == [9.99, 10.99, 11.99]
    assert titles == ["Harry Potter", "Pirates of the sea", "Python Programming"]
    os.remove("ma.db")
