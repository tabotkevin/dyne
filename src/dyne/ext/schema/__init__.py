import re
from pathlib import Path

from dyne.fields.pydantic import File

try:
    from typing import _AnnotatedAlias
except ImportError:  # pragma: no cover
    _AnnotatedAlias = None

from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

from dyne import status
from dyne.ext.auth import BasicAuth, DigestAuth, TokenAuth
from dyne.fields.mashmellow import FileField
from dyne.statics import DEFAULT_OPENAPI_THEME, OPENAPI_THEMES
from dyne.templates import Templates


class Schema:
    def __init__(
        self,
        app,
        title,
        version,
        plugins=None,
        description=None,
        terms_of_service=None,
        contact=None,
        license=None,
        openapi=None,
        openapi_route="/schema.yml",
        docs_route="/docs/",
        static_route="/static",
        openapi_theme=DEFAULT_OPENAPI_THEME,
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

        self.docs_theme = (
            openapi_theme if openapi_theme in OPENAPI_THEMES else DEFAULT_OPENAPI_THEME
        )
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
        if self.app.state.doc:
            info["description"] = self.app.state.doc.strip()

        # servers
        servers = [{"url": req.base_url}]

        spec = APISpec(
            title=self.title,
            version=self.version,
            openapi_version=self.openapi_version,
            plugins=self.plugins,
            info=info,
            servers=servers,
        )

        self.ma_plugin.converter.field_mapping[FileField] = ("string", "binary")

        # security schemes
        auth_schemes = []
        auth_names = []
        for route in self.app.router.routes:
            if hasattr(route.endpoint, "_spec"):
                backend = route.endpoint._spec.get("backend")
                if backend is not None and backend not in auth_schemes:
                    auth_schemes.append(backend)
                    if isinstance(backend, BasicAuth):
                        name = "basic_auth"
                    elif isinstance(backend, DigestAuth):
                        name = "digest_auth"
                    elif isinstance(backend, TokenAuth):
                        if backend.scheme == "Bearer":
                            name = "token_auth"
                        else:
                            name = "api_key"
                    else:  # pragma: no cover
                        raise RuntimeError("Unknown authentication scheme")
                    if name in auth_names:
                        v = 2
                        new_name = f"{name}_{v}"
                        while new_name in auth_names:  # pragma: no cover
                            v += 1
                            new_name = f"{name}_{v}"
                        name = new_name
                    auth_names.append(name)
        security = {}
        security_schemes = {}
        for name, backend in zip(auth_names, auth_schemes):
            security[backend] = name
            if isinstance(backend, TokenAuth):
                if backend.scheme == "Bearer":
                    security_schemes[name] = {
                        "type": "http",
                        "scheme": "bearer",
                    }
                else:
                    security_schemes[name] = {
                        "type": "apiKey",
                        "name": backend.header,
                        "in": "header",
                    }
            elif isinstance(backend, BasicAuth):
                security_schemes[name] = {
                    "type": "http",
                    "scheme": "basic",
                }
            else:
                security_schemes[name] = {
                    "type": "http",
                    "scheme": "digest",
                }
            if backend.__doc__:
                security_schemes[name]["description"] = backend.__doc__.strip()
        for prefix in ["basic_auth", "token_auth", "api_key", "digest_auth"]:
            for name, scheme in security_schemes.items():
                if name.startswith(prefix):
                    spec.components.security_scheme(name, scheme)

        # paths
        paths = {}
        for route in self.app.router.routes:

            operations = {}
            is_endpoint = True  # False for webhooks
            endpoint_name = route.endpoint_name
            endpoint = route.endpoint
            if not hasattr(endpoint, "_spec"):
                continue
            _spec = endpoint._spec
            if _spec.get("webhook"):
                is_endpoint = False
                endpoint_name = _spec["webhook"].get("endpoint_name") or endpoint_name
            if "." in endpoint_name:  # Blueprint
                tag, endpoint_name = endpoint_name.rsplit(".", 1)
                tag = tag.title()
            else:
                tag = None
            methods = [
                method
                for method in route.methods
                if method in ["GET", "POST", "PUT", "PATCH", "DELETE"]
            ]
            for method in methods:
                operation_id = endpoint_name.replace(".", "_")
                if len(methods) > 1:
                    operation_id = method.lower() + "_" + operation_id

                operation = {"operationId": operation_id, "parameters": []}
                for schema, location in _spec.get("args", []):
                    if hasattr(schema, "schema"):  # Pydantic schema
                        for name, field in schema.schema()["properties"].items():
                            parameter = {
                                "name": name,
                                "in": location,
                                "schema": field,
                                "description": field.get("description", ""),
                            }
                            operation["parameters"].append(parameter)
                    else:  # Marshmallow schema
                        parameter = {
                            "in": location,
                            "schema": schema,
                        }
                        operation["parameters"].append(parameter)

                if tag:
                    operation["tags"] = [tag]
                docs = [
                    line.strip()
                    for line in (route.description or "").strip().split("\n")
                ]
                if docs[0]:
                    operation["summary"] = docs[0]
                if len(docs) > 1:
                    operation["description"] = "\n".join(docs[1:]).strip()
                if _spec.get("output"):
                    code = str(_spec["status_code"])
                    schema = _spec.get("output")
                    operation["responses"] = {
                        code: {
                            "content": {
                                "application/json": {
                                    "schema": (
                                        schema.schema()
                                        if hasattr(schema, "schema")  # pydantic
                                        else schema
                                    )
                                }
                            }
                        }
                    }
                    operation["responses"][code]["description"] = (
                        _spec["description"] or status.STATUS_CODES[int(code)]
                    )

                    if _spec.get("headers"):
                        schema = _spec.get("headers")
                        if hasattr(schema, "schema"):  # Pydantic schema
                            headers = []
                            for name, field in schema.schema()["properties"].items():
                                parameter = {
                                    "name": name,
                                    "in": "header",
                                    "schema": field,
                                    "description": field.get("description", ""),
                                }
                                headers.append(parameter)

                        else:
                            headers = self.ma_plugin.converter.schema2parameters(
                                schema(), location="headers"
                            )
                        operation["responses"][code]["headers"] = {
                            header["name"]: header for header in headers
                        }
                else:
                    operation["responses"] = {
                        "204": {"description": status.STATUS_CODES[204]}
                    }

                if _spec.get("responses"):
                    for status_code, response in _spec.get("responses").items():
                        if not isinstance(response, (tuple, list)):
                            response = (response,)
                        operation["responses"][status_code] = {}
                        for r in response:
                            if isinstance(r, str):
                                operation["responses"][status_code]["description"] = r
                            else:
                                if isinstance(r, type):
                                    r = r()  # instantiate the schema
                                operation["responses"][status_code]["content"] = {
                                    "application/json": {"schema": r}
                                }
                        if "description" not in operation["responses"][status_code]:
                            operation["responses"][status_code]["description"] = (
                                status.STATUS_CODES[int(status_code)]
                            )

                if _spec.get("input"):
                    schema = _spec.get("input")[0]
                    location = _spec.get("input")[1]
                    media_type = "application/json"
                    if location == "form":
                        has_file = True
                        if hasattr(schema, "_declared_fields"):  # marshmallow
                            for field in schema._declared_fields.values():
                                if isinstance(field, FileField):
                                    has_file = True
                                    break
                        if hasattr(schema, "__fields__"):  # pydantic
                            for _, field_info in schema.model_fields.items():
                                if field_info.annotation == File or (
                                    hasattr(field_info.annotation, "__origin__")
                                    and File in field_info.annotation.__args__
                                ):
                                    has_file = True
                                    break
                        media_type = (
                            "application/x-www-form-urlencoded"
                            if not has_file
                            else "multipart/form-data"
                        )
                    operation["requestBody"] = {
                        "content": {
                            media_type: {
                                "schema": (
                                    schema.schema()
                                    if hasattr(schema, "schema")  # pydantic
                                    else schema
                                ),
                            }
                        },
                        "required": True,
                    }

                if _spec.get("backend"):
                    operation["security"] = [
                        {security[_spec["backend"]]: _spec["roles"]}
                    ]
                operations[method.lower()] = operation

            if is_endpoint:
                path_arguments = re.findall(r"{([^}:]+)(?::([^}]+))?}", route.route)
                if path_arguments:
                    annotations = endpoint.__annotations__ or {}
                    arguments = []
                    for name, type_ in path_arguments:
                        argument = {
                            "in": "path",
                            "name": name,
                        }
                        if type_ == "int":
                            argument["schema"] = {"type": "integer"}
                        elif type_ == "float":
                            argument["schema"] = {"type": "number"}
                        elif type_ == "uuid":
                            argument["schema"] = {"type": "string", "format": "uuid"}
                        elif type_ == "path":
                            argument["schema"] = {"type": "string", "format": "path"}
                        else:
                            argument["schema"] = {"type": "string"}
                        if isinstance(annotations.get(name), str):
                            argument["description"] = annotations[name]
                        elif _AnnotatedAlias and isinstance(
                            annotations.get(name), _AnnotatedAlias
                        ):
                            for annotation in annotations[name].__metadata__:
                                if isinstance(annotation, str):
                                    argument["description"] = annotation
                                    break
                        arguments.append(argument)

                    for method, operation in operations.items():
                        operation["parameters"] = arguments + operation["parameters"]

                path = re.sub(r"<([^<:]+:)?", "{", route.route).replace(">", "}")
                if path not in paths:
                    paths[path] = operations
                else:
                    paths[path].update(operations)
            else:
                # apispec does not support webhooks, so here they are added as
                # paths, and later they are moved to their own section after
                # the spec is generated
                paths["webhook:" + endpoint_name] = operations

            for path, operations in paths.items():
                # sort by method before adding them to the spec
                sorted_operations = {}
                for method in ["get", "post", "put", "patch", "delete"]:
                    if method in operations:
                        sorted_operations[method] = operations[method]
                spec.path(path=path, operations=sorted_operations)

        for name, schema in self.schemas.items():
            if hasattr(schema, "schema"):
                spec.components.schema(name, schema.schema())  # pydantic.
            else:
                spec.components.schema(name, schema=schema)  # marshmallow.

        webhooks = {
            path[8:]: operations
            for path, operations in spec._paths.items()
            if path.startswith("webhook:")
        }
        if webhooks:
            paths = {
                path: operations
                for path, operations in spec._paths.items()
                if not path.startswith("webhook:")
            }
            spec._paths["paths"] = paths
            spec.__dict__["webhooks"] = webhooks

        return spec

    def openapi(self, req):
        return self._apispec(req).to_yaml()

    def add_schema(self, name, schema, check_existing=True):
        """Adds a marshmallow schema to the API specification."""
        if check_existing:
            assert name not in self.schemas

        self.schemas[name] = schema

    def schema(self, name, **options):
        """Decorator for creating new routes around function and class definitions.

        Usage::

            from marshmallow import Schema, fields

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
        resp.status_code = status.HTTP_200_OK
        resp.headers["Content-Type"] = "application/x-yaml"
        resp.content = self.openapi(req)
