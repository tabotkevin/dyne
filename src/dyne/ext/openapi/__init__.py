import re
from http import HTTPStatus
from pathlib import Path
from typing import get_origin

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from dyne.ext.auth import BasicAuth, DigestAuth, TokenAuth
from dyne.templates import Templates

_THEMES = ["elements", "rapidoc", "redoc", "swaggerui"]
_DEFAULT_THEME = "elements"


class OpenAPI:
    """The primary web-service class.

    :param title: The name of the API, displayed in the documentation UI.
    :param version: The current version of your API (e.g., "1.0").
    :param plugins: A list of extensions to be registered and initialized with the app.
    :param description: A short summary describing the purpose and usage of the API.
    :param terms_of_service: A URL pointing to the legal terms for using the API.
    :param contact: A dictionary or string containing contact info (email, name, URL).
    :param license: A dictionary or string containing license info (e.g., MIT, Apache 2.0).
    :param openapi: The version of the OpenAPI specification to use (default "3.0.1").
    :param openapi_route: The URL path where the raw OpenAPI schema (YAML/JSON) is served.
    :param docs_route: The URL path where the interactive documentation (Swagger/Redoc) is hosted.
    :param static_route: The URL prefix used for serving static assets and files.
    :param theme: OpenAPI documentation theme, must be one of ``elements``, ``rapidoc``, ``redoc``, ``swaggerui``
    """

    def __init__(
        self,
        app,
        title="Documentation",
        version="1.0",
        plugins=None,
        description=None,
        terms_of_service=None,
        contact=None,
        license=None,
        openapi="3.0.1",
        openapi_route="/schema.yml",
        docs_route="/docs",
        static_route="/static",
        theme=_DEFAULT_THEME,
    ):
        self.app = app
        self.schemas = {}
        self.title = title
        self.version = version
        self.description = description
        self.terms_of_service = terms_of_service
        self.contact = contact
        self.license = license

        self.openapi_version = openapi
        self.openapi_route = openapi_route

        self.docs_theme = theme if theme in _THEMES else _DEFAULT_THEME
        self.docs_route = docs_route

        self.ma_plugin = MarshmallowPlugin()
        self.plugins = [self.ma_plugin] if plugins is None else plugins

        if self.openapi_version is not None:
            self.app.add_route(self.openapi_route, self.schema_response)

        if self.docs_route is not None:
            self.app.add_route(self.docs_route, self.docs_response)

        theme_path = (Path(__file__).parent / "docs").resolve()
        self.templates = Templates(directory=theme_path)

        self.static_route = static_route

    def _apispec(self, req):

        info = {}
        if self.description is not None:
            info["description"] = self.description
        if self.terms_of_service is not None:
            info["termsOfService"] = self.terms_of_service
        if self.contact is not None:
            info["contact"] = self.contact
        if self.license is not None:
            info["license"] = self.license

        servers = [{"url": req.base_url}]

        spec = APISpec(
            title=self.title,
            version=self.version,
            openapi_version=self.openapi_version,
            plugins=self.plugins,
            info=info,
            servers=servers,
        )

        # ------------------------------------------------------------
        # Global authentication Security Schemes
        # ------------------------------------------------------------

        unique_backends = []
        for route in self.app.router.routes:
            backend = getattr(route.endpoint, "_spec", {}).get("backend")
            if backend and backend not in unique_backends:
                unique_backends.append(backend)

        security = {}
        security_schemes = {}

        for backend in unique_backends:
            base_name, scheme = self.get_backend_info(backend)

            if backend.__doc__:
                scheme["description"] = backend.__doc__.strip()

            name = base_name
            v = 2
            while name in security_schemes:
                name = f"{base_name}_{v}"
                v += 1

            security_schemes[name] = scheme
            security[backend] = name

        for name, scheme in security_schemes.items():
            spec.components.security_scheme(name, scheme)

        # ------------------------------------------------------------
        #  Routes
        # ------------------------------------------------------------
        paths = {}
        webhooks = {}
        allowed_methods = {"get", "post", "put", "patch", "delete"}

        for route in self.app.router.routes:
            operations = {}
            path = route.route
            endpoint = route.endpoint
            endpoint_name = route.endpoint_name
            route_methods = route.methods or ["get"]
            annot = getattr(endpoint, "_spec", None)

            if not annot:
                continue

            methods = [
                method.lower()
                for method in route_methods
                if method.lower() in allowed_methods
            ]

            # Bind input and output adapters to spec.
            for key in ("input_adapter", "output_adapter", "output_headers_adapter"):
                adapter = annot.get(key)
                if adapter and hasattr(adapter, "bind"):
                    adapter.bind(spec)

            # Bind expect adapters to spec.
            for expect in annot.get("expect", {}).values():
                adapter = expect.get("adapter")
                if adapter and hasattr(adapter, "bind"):
                    adapter.bind(spec)

            for method in methods:

                # --------------------------------------------------------
                # OPERATION BASE
                # --------------------------------------------------------

                operation_id = endpoint_name.replace(".", "_")
                if len(methods) > 1:
                    operation_id = method + "_" + operation_id

                operation = {
                    "operationId": operation_id,
                    "parameters": [],
                    "responses": {},
                }

                # --------------------------------------------------------
                # TAGS / SUMMARY / DESCRIPTION
                # --------------------------------------------------------
                tag = None
                if "." in endpoint_name:  # Blueprint
                    tag, name = endpoint_name.rsplit(".", 1)
                    tag = tag.title()

                if tag:
                    operation["tags"] = [tag]

                docs = [line.strip() for line in (route.doc or "").strip().split("\n")]

                if docs[0]:
                    operation["summary"] = docs[0]

                if len(docs) > 1:
                    operation["description"] = "\n".join(docs[1:]).strip()

                # --------------------------------------------------------
                # SECURITY (Authorization roles)
                # --------------------------------------------------------
                if annot.get("backend"):
                    backend = annot["backend"]
                    name, scheme = self.get_backend_info(backend)

                    if "type" not in scheme:  # MultiAuth
                        operation["security"] = [
                            {name: annot.get("roles", [])} for name in scheme.keys()
                        ]
                    else:
                        operation["security"] = [{name: annot.get("roles", [])}]

                # --------------------------------------------------------
                # INPUT (BODY, HEADERS, QUERY PARAMETERS, COOKIES)
                # --------------------------------------------------------
                if annot.get("input_adapter"):
                    input_adapter = annot["input_adapter"]
                    input_location = annot["input_location"]

                    if input_location in ("json", "media", "form"):
                        media_type = input_adapter.media_type(input_location)
                        operation["requestBody"] = {
                            "required": True,
                            "content": {
                                media_type: {
                                    "schema": input_adapter.get_openapi_schema()
                                }
                            },
                        }
                    else:
                        operation.setdefault("parameters", []).extend(
                            input_adapter.get_parameters(input_location)
                        )

                # --------------------------------------------------------
                # OUTPUT
                # --------------------------------------------------------
                if annot.get("output_adapter"):
                    output_adapter = annot["output_adapter"]
                    output_status_code = str(annot.get("output_status_code", 200))

                    operation["responses"][output_status_code] = {
                        "content": {
                            "application/json": {
                                "schema": output_adapter.get_openapi_schema()
                            }
                        }
                    }
                    operation["responses"][output_status_code]["description"] = (
                        annot["output_description"]
                        or HTTPStatus(int(output_status_code)).phrase
                    )

                    if annot.get("output_headers_adapter"):
                        output_headers_adapter = annot["output_headers_adapter"]
                        headers = output_headers_adapter.get_parameters("header")

                        operation["responses"][output_status_code]["headers"] = {
                            header["name"]: header for header in headers
                        }

                else:
                    operation["responses"] = {
                        "204": {"description": HTTPStatus(204).phrase}
                    }

                # --------------------------------------------------------
                # EXPECT (DOCUMENTED ERRORS)
                # --------------------------------------------------------

                for status_code, meta in annot.get("expect", {}).items():
                    response = {
                        "description": meta["description"]
                        or HTTPStatus(int(status_code)).phrase
                    }

                    if meta.get("adapter"):
                        response["content"] = {
                            "application/json": {
                                "schema": meta["adapter"].get_openapi_schema()
                            }
                        }

                    operation["responses"][status_code] = response

                # -------------------------------------------------
                # Path Parameters
                # -------------------------------------------------
                path_arguments = re.findall(r"{([^}:]+)(?::([^}]+))?}", route.route)

                if path_arguments:
                    annotations = endpoint.__annotations__ or {}

                    for name, type_ in path_arguments:
                        types = {
                            "int": {"type": "integer"},
                            "float": {"type": "number"},
                            "uuid": {"type": "string", "format": "uuid"},
                            "path": {"type": "string", "format": "path"},
                        }
                        param = {
                            "in": "path",
                            "name": name,
                            "schema": types.get(type_, {"type": "string"}),
                        }

                        ann = annotations.get(name)

                        if isinstance(ann, str):
                            param["description"] = ann

                        else:
                            origin = get_origin(ann)
                            if origin is not None and hasattr(ann, "__metadata__"):
                                for meta in ann.__metadata__:
                                    if isinstance(meta, str):
                                        param["description"] = meta
                                        break

                        operation["parameters"].append(param)

                # -------------------------------------------------
                # Webhooks vs Standard Paths
                # -------------------------------------------------
                is_webhook = annot.get("webhook", False)

                if is_webhook:
                    name = annot["webhook"].get("endpoint_name") or endpoint_name
                    webhooks[name] = {method: operation}
                else:
                    path = re.sub(r"<([^<:]+:)?", "{", path).replace(">", "}")
                    paths.setdefault(path, {}).update(operations)

                # --------------------------------------------------------
                # REGISTER OPERATION
                # --------------------------------------------------------
                operations[method] = operation
                spec.path(path=path, operations=operations)

        # ------------------------------------------------------------
        # Attach Paths
        # ------------------------------------------------------------
        for path, ops in paths.items():
            sorted_ops = {m: ops[m] for m in allowed_methods if m in ops}
            spec.path(path=path, operations=sorted_ops)

        # ------------------------------------------------------------
        # Attach Webhooks (OpenAPI 3.0.x)
        # ------------------------------------------------------------

        if webhooks:
            spec_dict = spec.to_dict()
            spec_dict["webhooks"] = webhooks

        return spec

    def openapi(self, req):
        return self._apispec(req).to_yaml()

    def add_schema(self, name, schema, check_existing=True):
        if check_existing:
            assert name not in self.schemas

        self.schemas[name] = schema

    def schema(self, name, **options):
        """Decorator for creating new routes around function and class definitions.

        Usage::

            @api.schema("Pet")
            class PetSchema(Schema):
                name = fields.Str()

        """

        def decorator(f):
            self.add_schema(name=name, schema=f, **options)
            return f

        return decorator

    @property
    def docs(self):
        return self.templates.render(
            f"{self.docs_theme}.html",
            title=self.title,
            version=self.version,
            schema_url="/schema.yml",
        )

    def static_url(self, asset):
        """Given a static asset, return its URL path."""
        assert self.static_route is not None
        return f"{self.static_route}/{str(asset)}"

    def docs_response(self, req, resp):
        resp.html = self.docs

    def schema_response(self, req, resp):
        resp.status_code = HTTPStatus.OK
        resp.headers["Content-Type"] = "application/x-yaml"
        resp.content = self.openapi(req)

    def get_backend_info(self, backend):
        if isinstance(backend, BasicAuth):
            return "basic_auth", {"type": "http", "scheme": "basic"}

        if isinstance(backend, DigestAuth):
            return "digest_auth", {"type": "http", "scheme": "digest"}

        if isinstance(backend, TokenAuth):
            if backend.scheme == "Bearer":
                return "token_auth", {"type": "http", "scheme": "bearer"}
            return "api_key", {"type": "apiKey", "name": backend.header, "in": "header"}

        raise RuntimeError(f"Unknown authentication scheme: {type(backend)}")
