import os
from functools import wraps
from pathlib import Path

import marshmallow as ma
import pydantic as pd
import uvicorn
from sqlalchemy.orm import DeclarativeBase, Query
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.testclient import TestClient

from . import status
from .background import BackgroundQueue
from .ext.schema import Schema as OpenAPISchema
from .formats import get_formats
from .routes import Router
from .staticfiles import StaticFiles
from .statics import DEFAULT_CORS_PARAMS, DEFAULT_OPENAPI_THEME, DEFAULT_SECRET_KEY
from .templates import Templates


class API:
    """The primary web-service class.

    :param static_dir: The directory to use for static files. Will be created for you if it doesn't already exist.
    :param templates_dir: The directory to use for templates. Will be created for you if it doesn't already exist.
    :param auto_escape: If ``True``, HTML and XML templates will automatically be escaped.
    :param enable_hsts: If ``True``, send all responses to HTTPS URLs.
    :param openapi_theme: OpenAPI documentation theme, must be one of ``elements``, ``rapidoc``, ``redoc``, ``swaggerui``
    """

    status = status

    class State:
        pass

    def __init__(
        self,
        *,
        debug=False,
        title="Documentation",
        version="1.0",
        description=None,
        terms_of_service=None,
        contact=None,
        license=None,
        openapi="3.0.1",
        openapi_route="/schema.yml",
        static_dir="static",
        static_route="/static",
        templates_dir="templates",
        docs_route="/docs",
        auto_escape=True,
        secret_key=DEFAULT_SECRET_KEY,
        enable_hsts=False,
        cors=False,
        cors_params=DEFAULT_CORS_PARAMS,
        allowed_hosts=None,
        openapi_theme=DEFAULT_OPENAPI_THEME,
    ):
        self.background = BackgroundQueue()

        self.secret_key = secret_key

        self.router = Router()

        if static_dir is not None:
            if static_route is None:
                static_route = static_dir
            static_dir = Path(os.path.abspath(static_dir))

        self.static_dir = static_dir
        self.static_route = static_route

        self.hsts_enabled = enable_hsts
        self.cors = cors
        self.cors_params = cors_params
        self.debug = debug

        if not allowed_hosts:
            # if not debug:
            #     raise RuntimeError(
            #         "You need to specify `allowed_hosts` when debug is set to False"
            #     )
            allowed_hosts = ["*"]
        self.allowed_hosts = allowed_hosts

        if self.static_dir is not None:
            os.makedirs(self.static_dir, exist_ok=True)

        if self.static_dir is not None:
            self.mount(self.static_route, self.static_app)

        self.formats = get_formats()

        # Cached requests session.
        self._session = None

        self.default_endpoint = None
        self.app = ExceptionMiddleware(self.router, debug=debug)
        # A store for applications to retain data for the entire lifecycle.
        self.state = API.State()
        self.add_middleware(GZipMiddleware)

        if self.hsts_enabled:
            self.add_middleware(HTTPSRedirectMiddleware)

        self.add_middleware(TrustedHostMiddleware, allowed_hosts=self.allowed_hosts)

        if self.cors:
            self.add_middleware(CORSMiddleware, **self.cors_params)
        self.add_middleware(ServerErrorMiddleware, debug=debug)
        self.add_middleware(SessionMiddleware, secret_key=self.secret_key)

        self.openapi = OpenAPISchema(
            app=self,
            title=title,
            version=version,
            openapi=openapi,
            docs_route=docs_route,
            description=description,
            terms_of_service=terms_of_service,
            contact=contact,
            license=license,
            openapi_route=openapi_route,
            static_route=static_route,
            openapi_theme=openapi_theme,
        )

        # TODO: Update docs for templates
        self.templates = Templates(directory=templates_dir)
        self.requests = (
            self.session()
        )  #: A Requests session that is connected to the ASGI app.

    @property
    def static_app(self):
        if not hasattr(self, "_static_app"):
            assert self.static_dir is not None
            self._static_app = StaticFiles(directory=self.static_dir)
        return self._static_app

    def before_request(self, websocket=False):
        def decorator(f):
            self.router.before_request(f, websocket=websocket)
            return f

        return decorator

    def add_middleware(self, middleware_cls, **middleware_config):
        self.app = middleware_cls(self.app, **middleware_config)

    def schema(self, name, **options):
        """Decorator for creating new routes around function and class definitions.
        Usage::
            from marshmallow import Schema, fields
            @api.schema("Pet")
            class PetSchema(Schema):
                name = fields.Str()
        """

        def decorator(f):
            self.openapi.add_schema(name=name, schema=f, **options)
            return f

        return decorator

    def path_matches_route(self, path):
        """Given a path portion of a URL, tests that it matches against any registered route.

        :param path: The path portion of a URL, to test all known routes against.
        """
        for route in self.router.routes:
            match, _ = route.matches(path)
            if match:
                return route

    def add_route(
        self,
        route=None,
        endpoint=None,
        *,
        default=False,
        static=True,
        check_existing=True,
        websocket=False,
        before_request=False,
        methods=("GET",),
    ):
        """Adds a route to the API.

        :param route: A string representation of the route.
        :param endpoint: The endpoint for the route -- can be a callable, or a class.
        :param default: If ``True``, all unknown requests will route to this view.
        :param static: If ``True``, and no endpoint was passed, render "static/index.html", and it will become a default route.
        :param methods: A list of supported request methods for this endpoint. e.g ["GET", "POST"].
        """

        # Path
        if static:
            assert self.static_dir is not None
            if not endpoint:
                endpoint = self._static_response
                default = True

        self.router.add_route(
            route,
            endpoint,
            default=default,
            websocket=websocket,
            before_request=before_request,
            check_existing=check_existing,
            methods=methods,
        )

    async def _static_response(self, req, resp):
        assert self.static_dir is not None

        index = (self.static_dir / "index.html").resolve()
        if os.path.exists(index):
            with open(index, "r") as f:
                resp.html = f.read()
        else:
            resp.status_code = status.HTTP_404_NOT_FOUND
            resp.text = "Not found."

    def redirect(
        self,
        resp,
        location,
        *,
        set_text=True,
        status_code=status.HTTP_301_MOVED_PERMANENTLY,
    ):
        """Redirects a given response to a given location.
        :param resp: The Response to mutate.
        :param location: The location of the redirect.
        :param set_text: If ``True``, sets the Redirect body content automatically.
        :param status_code: an `API.status_codes` attribute, or an integer, representing the HTTP status code of the redirect.
        """
        resp.redirect(location, set_text=set_text, status_code=status_code)

    def on_event(self, event_type: str, **args):
        """Decorator for registering functions or coroutines to run at certain events
        Supported events: startup, shutdown

        Usage::

            @api.on_event('startup')
            async def open_database_connection_pool():
                ...

            @api.on_event('shutdown')
            async def close_database_connection_pool():
                ...

        """

        def decorator(func):
            self.add_event_handler(event_type, func, **args)
            return func

        return decorator

    def add_event_handler(self, event_type, handler):
        """Adds an event handler to the API.

        :param event_type: A string in ("startup", "shutdown")
        :param handler: The function to run. Can be either a function or a coroutine.
        """

        self.router.add_event_handler(event_type, handler)

    def route(self, route=None, **options):
        """Decorator for creating new routes around function and class definitions.

        Usage::

            @api.route("/hello")
            def hello(req, resp):
                resp.text = "hello, world!"

        """

        def decorator(f):
            self.add_route(route, f, **options)
            return f

        return decorator

    def mount(self, route, app):
        """Mounts an WSGI / ASGI application at a given route.

        :param route: String representation of the route to be used (shouldn't be parameterized).
        :param app: The other WSGI / ASGI app.
        """
        self.router.apps.update({route: app})

    def session(self, base_url="http://;"):
        """Testing HTTP client. Returns a Requests session object, able to send HTTP requests to the dyne application.

        :param base_url: The URL to mount the connection adaptor to.
        """

        if self._session is None:
            self._session = TestClient(self, base_url=base_url)
        return self._session

    def url_for(self, endpoint, **params):
        # TODO: Absolute_url
        """Given an endpoint, returns a rendered URL for its route.

        :param endpoint: The route endpoint you're searching for.
        :param params: Data to pass into the URL generator (for parameterized URLs).
        """
        return self.router.url_for(endpoint, **params)

    def template(self, filename, *args, **kwargs):
        """Renders the given `jinja2 <http://jinja.pocoo.org/docs/>`_ template, with provided values supplied.
        Note: The current ``api`` instance is by default passed into the view. This is set in the dict ``api.jinja_values_base``.
        :param filename: The filename of the jinja2 template, in ``templates_dir``.
        :param *args: Data to pass into the template.
        :param *kwargs: Date to pass into the template.
        """
        return self.templates.render(filename, *args, **kwargs)

    def template_string(self, source, *args, **kwargs):
        """Renders the given `jinja2 <http://jinja.pocoo.org/docs/>`_ template string, with provided values supplied.
        Note: The current ``api`` instance is by default passed into the view. This is set in the dict ``api.jinja_values_base``.
        :param source: The template to use.
        :param *args: Data to pass into the template.
        :param **kwargs: Data to pass into the template.
        """
        return self.templates.render_string(source, *args, **kwargs)

    def _annotate(self, f, **kwargs):
        """Utilized to store essential route details for later inclusion in the
        OpenAPI documentation of the route."""

        if not hasattr(f, "_spec"):
            f._spec = {}
        for key, value in kwargs.items():
            f._spec[key] = value

    def expect(self, responses):
        """A decorator that receives key pair values of status_codes and descriptions
        for other responses expected the by an endpoint. This decorator is only
        used for OpenAPI documentation.

        :params codes: e.g {401: 'Invalid access or refresh token', 404: 'Item not found'}


        Usage::
            api = dyne.API()

            @api.route("/create")
            @api.input(ItemCreate)
            @api.expect(
                {
                    401: "Invalid access or refresh token",
                    403: "Please verify your account",
                }
            )
            async def create_items(req, resp):
                resp.text = "Item created"
        """

        def decorator(f):
            self._annotate(f, responses=responses)
            return f

        return decorator

    def _parse_request(self, schema, location, key=None, unknown=None):
        """A decorator for parsing and validating input schema from a specified request location.
        Supports both Pydantic and Marshmallow.

        :param schema: Marshmallow or Pydantic model.
        :param location: values must be one of `cookies, headers, media, params or query`.
        :param key: The unique key to use for fetching data from the request (e.g., 'q', 'headers', 'data').
        :param unknown: A value to pass for ``unknown`` when calling the
           marshmallow schema's ``load`` method.
        """

        if location == "params":
            location = "query"

        if not key:
            key = location
            if location in ["media", "form"]:
                key = "data"

        def decorator(f):
            if not hasattr(f, "_spec") or f._spec.get("args") is None:
                self._annotate(f, args=[])
            if location not in ["media", "form"]:
                f._spec["args"].append((schema, location))
            else:
                self._annotate(f, input=(schema, location))

            @wraps(f)
            async def wrapper(req, resp, *args, **kwargs):
                data = await req.validate(schema, location=location, unknown=unknown)
                if "errors" in data:
                    resp.status_code = status.HTTP_400_BAD_REQUEST
                    resp.media = data
                    return

                return await f(req, resp, *args, **kwargs, **{key: data})

            return wrapper

        return decorator

    def input(self, schema, location="media", key=None, unknown=None):
        """A decorator for validating data from a specified request location against a
           Marshmallow or Pydantic schemas.

        :param schema: Marshmallow or Pydantic schemas.
        :param location: media(json, form, yaml), cookies, headers, params or query.
        :param key: The unique key to use for fetching data from the request (e.g., 'q', 'headers', 'data').
        :param unknown: A value to pass for ``unknown`` when calling the
           marshmallow schema's ``load`` method. Defaults to ``marshmallow.EXCLUDE`` for headers and cookies.

           Pydantic and Marshmallow schemas.

        Usage::
            import time
            from pydantic import BaseModel
            import dyne

            class Item(BaseModel)
                price: float
                title: str

            api = dyne.API()

            @api.route("/create")
            @api.input(Item)
            def create_item(req, resp, *, data):
                @api.background.task
                def process_item(item):
                    time.sleep(1)
                    print(item)   # e.g {"price": 9.99, "title": "Pydantic book"}

                process_item(data)
                resp.media = {"msg": "created"}

            r = api.requests.post("http://;/create", json={"price": 9.99, "title": "Pydantic book"})
        """
        return self._parse_request(schema, location=location, key=key, unknown=unknown)

    def output(
        self, schema, status_code=status.HTTP_200_OK, headers=None, description=None
    ):
        """A decorator for serializing response dictionaries or SQLAlchemy objects.
           Supports both Pydantic and Marshmallow.

        Usage::
            from typing import Optional

            from pydantic import BaseModel
            from sqlalchemy import Column, Integer, String
            import dyne

            from .models import Item


            class Item(Base):
                __tablename__ = "items"
                id = Column(Integer, primary_key=True)
                name = Column(String)


            class ItemCreate(BaseModel)
                id: Optional[int]
                name: str

                class Config:
                    from_attributes = True

            api = dyne.API()

            @api.route("/all")
            @api.output(ItemCreate)
            async def all_items(req, resp):
                "Get all items"

            resp.obj = session.query(Item)


            @api.route("/create")
            @api.input(ItemCreate)
            @api.output(ItemCreate)
            async def create(req, resp, *, data):
                "Create item"

                item = Item(**data)
                session.add(item)
                session.commit()

                resp.obj = item
        """

        def decorator(f):
            self._annotate(
                f,
                output=schema,
                status_code=status_code,
                headers=headers,
                description=description,
            )

            @wraps(f)
            async def wrapper(req, resp, *args, **kwargs):
                nonlocal status_code
                await f(req, resp, *args, **kwargs)

                if not hasattr(resp, "obj"):
                    raise TypeError("You must set `resp.obj` when using @output")

                obj = resp.obj
                if obj is None:
                    obj = {}

                if isinstance(obj, (DeclarativeBase, Query, list)):
                    try:
                        if hasattr(schema, "from_orm"):  # pydantic
                            resp.media = (
                                [schema.model_validate(o).model_dump() for o in obj]
                                if isinstance(obj, (Query, list))
                                else schema.model_validate(obj).model_dump()
                            )
                        else:  # marshmallow
                            resp.media = (
                                schema(many=True).dump(obj)
                                if isinstance(obj, (Query, list))
                                else schema().dump(obj)
                            )

                    except (ma.ValidationError, pd.ValidationError) as e:
                        status_code = 400
                        resp.media = {
                            "errors": (
                                {
                                    k: str(v)
                                    for k, v in e.errors()[0].items()
                                    if k != "input"
                                }
                                if isinstance(e, pd.ValidationError)
                                else e.messages
                            )
                        }
                elif isinstance(obj, dict):
                    resp.media = obj
                else:
                    resp.media = dict(errors="Returned obj is not serializable")

                resp.status_code = status_code

                return

            return wrapper

        return decorator

    def authenticate(self, backend, **kwargs):
        def decorator(f):
            roles = kwargs.get("role")
            if not isinstance(roles, list):  # pragma: no cover
                roles = [roles] if roles is not None else []
            self._annotate(f, backend=backend, roles=roles)
            return backend.login_required(**kwargs)(f)

        return decorator

    def webhook(self, method="GET", blueprint=None, endpoint_name=None):
        def decorator(f):
            self._annotate(
                f,
                webhook={
                    "blueprint": blueprint,
                    "endpoint_name": endpoint_name,
                    "methods": [method],
                },
            )
            return f

        if callable(method) and blueprint is None and endpoint_name is None:
            # invoked as a decorator without arguments
            f = method
            method = "GET"
            return decorator(f)
        else:
            # invoked as a decorator with arguments
            return decorator

    def serve(self, *, address=None, port=None, **options):
        """Runs the application with uvicorn. If the ``PORT`` environment
        variable is set, requests will be served on that port automatically to all
        known hosts.

        :param address: The address to bind to.
        :param port: The port to bind to. If none is provided, one will be selected at random.
        :param debug: Run uvicorn server in debug mode.
        :param options: Additional keyword arguments to send to ``uvicorn.run()``.
        """

        if "PORT" in os.environ:
            if address is None:
                address = "0.0.0.0"
            port = int(os.environ["PORT"])

        if address is None:
            address = "127.0.0.1"
        if port is None:
            port = 5042

        def spawn():
            uvicorn.run(self, host=address, port=port, **options)

        spawn()

    def run(self, **kwargs):
        self.serve(**kwargs)

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
