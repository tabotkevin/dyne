from functools import wraps

try:
    import pydantic as pd
    from pydantic import TypeAdapter
except ImportError as exc:
    raise RuntimeError(
        "Pydantic is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[pydantic]\n"
    ) from exc

from http import HTTPStatus
from inspect import isclass
from typing import Any, get_args, get_origin

from ..base import BaseIO, SchemaAdapter
from .fields import FileField


class PydanticSchemaAdapter(SchemaAdapter):
    def get_openapi_schema(self):
        if hasattr(self.schema, "model_json_schema"):  # v2
            return self.schema.model_json_schema()
        return self.schema.schema()  # v1

    def get_schema(self):
        return self.schema.schema()

    def _is_file_field(self, annotation: Any) -> bool:
        try:
            if isclass(annotation) and issubclass(annotation, FileField):
                return True
        except TypeError:
            pass

        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)
            return any(self._is_file_field(arg) for arg in args)

        return False

    def has_file(self):
        # v2 and V1
        fields = getattr(self.schema, "model_fields", None) or getattr(
            self.schema, "__fields__", {}
        )

        for field in fields.values():
            annotation = getattr(field, "annotation", None)  # v2
            if annotation is None:
                annotation = getattr(field, "type_", None)  # v1

            if annotation and self._is_file_field(annotation):
                return True

        return False

    def get_parameters(self, location):
        params = []

        # v2
        if hasattr(self.schema, "model_fields"):
            for name, field in self.schema.model_fields.items():
                schema = TypeAdapter(field.annotation).json_schema()

                params.append(
                    {
                        "name": name,
                        "in": location,
                        "required": field.is_required(),
                        "schema": schema,
                        "description": field.description or "",
                    }
                )

        # v1
        elif hasattr(self.schema, "__fields__"):
            for name, field in self.schema.__fields__.items():
                schema = field.schema()

                params.append(
                    {
                        "name": name,
                        "in": location,
                        "required": field.required,
                        "schema": schema,
                        "description": field.field_info.description or "",
                    }
                )

        return params

    def bind(self, spec):
        if self._bound:
            return

        model = self.schema
        name = model.__name__

        if hasattr(model, "model_json_schema"):
            schema = model.model_json_schema()
        else:
            schema = model.schema(ref_template="#/components/schemas/{model}")

        if name not in spec.components.schemas:
            spec.components.schemas[name] = schema

        self._bound = True


class PydanticIO(BaseIO):

    @staticmethod
    def _parse_error(error: pd.ValidationError):
        errors = {}

        for e in error.errors():
            loc = e.get("loc") or ()
            key = ".".join(map(str, loc)) if loc else "non_field_error"
            errors.setdefault(key, []).append(e.get("msg"))

        return errors

    @staticmethod
    def _normalize_data(data: dict) -> dict:
        normalized = {}
        for key, value in data.items():
            if isinstance(value, bytes):
                normalized[key] = value.decode()
            elif isinstance(value, list):
                normalized[key] = [
                    v.decode() if isinstance(v, bytes) else v for v in value
                ]
            else:
                normalized[key] = value
        return normalized

    @classmethod
    def input(cls, schema, location="media", key=None, unknown=None):
        """
        Decorator for validating request data using a **Pydantic schema**.

        The request data is extracted from the specified location, validated against
        the given Pydantic model, and then injected into the route handler as a
        keyword-only argument.

        On successful validation:
        - The validated data is provided as a plain Python `dict`
        (via `model_dump()`).

        On validation failure:
        - A `400 Bad Request` response is returned with validation error details.

        :param schema: A subclass of `pydantic.BaseModel`.
        :param location: Where to read data from.
                        Supported values: `media` (json, form, yaml),
                        `header`, `cookie`, `params`, `query`.
        :param key: The keyword argument name used to inject the validated data
                    into the route handler.
                    Defaults to `"data"`.

        Usage::

            import time
            from pydantic import BaseModel
            import dyne

            class Item(BaseModel):
                price: float
                title: str

            api = dyne.API()

            @api.route("/create")
            @input(Item)
            async def create_item(req, resp, *, data):
                @api.background.task
                def process_item(item):
                    time.sleep(1)
                    print(item)  # {"price": 9.99, "title": "Pydantic book"}

                process_item(data)
                resp.media = {"msg": "created"}

            # Client request
            r = api.client.post("http://;/create", json={"price": 9.99, "title": "Pydantic book"})
        """

        cls._validate_location(location)

        if location == "params":
            location = "query"
        final_key = key or ("data" if location in ["media", "form"] else location)

        input_adapter = PydanticSchemaAdapter(schema)

        def decorator(f):

            cls._annotate(
                f,
                input_adapter=input_adapter,
                input_location=location,
            )

            @wraps(f)
            async def wrapper(req, resp, *args, **kwargs):
                raw_data = await cls._get_request_data(req, location)
                data = cls._normalize_data(raw_data)

                try:
                    # Validate (Pydantic V2 specific)
                    if isinstance(schema, type) and issubclass(schema, pd.BaseModel):
                        validated_obj = schema.model_validate(data)
                    else:
                        validated_obj = schema(**data)

                    validated_data = validated_obj.model_dump()
                except pd.ValidationError as e:
                    resp.status_code = HTTPStatus.BAD_REQUEST
                    resp.media = {"errors": cls._parse_error(e)}
                    return

                return await f(
                    req, resp, *args, **kwargs, **{final_key: validated_data}
                )

            return wrapper

        return decorator

    @classmethod
    def output(cls, schema, status_code=200, headers=None, description=None):
        """
        A decorator for serializing response data using a **Pydantic model**.

        This decorator validates and serializes response objects (such as dictionaries
        or ORM/SQLAlchemy models) into the specified Pydantic schema before sending
        the response to the client.

        Features:
        - Supports dictionaries and ORM objects
        - Uses Pydantic's validation and type coercion
        - Works seamlessly with SQLAlchemy models via `from_attributes = True`
        - Used only for **response serialization**, not request validation

        :param schema: A Pydantic `BaseModel` used to serialize the response object.

        Usage::
            from typing import Optional
            from pydantic import BaseModel
            from sqlalchemy import Column, Integer, String
            import dyne

            from .database import session, Base


            class Item(Base):
                __tablename__ = "items"
                id = Column(Integer, primary_key=True)
                name = Column(String)


            class ItemSchema(BaseModel):
                id: Optional[int]
                name: str

                class Config:
                    from_attributes = True


            api = dyne.API()


            @api.route("/items")
            @output(ItemSchema)
            async def all_items(req, resp):
                resp.obj = session.query(Item).all()


            @api.route("/items/create")
            @input(ItemSchema)
            @output(ItemSchema)
            async def create_item(req, resp, *, data):
                item = Item(**data)
                session.add(item)
                session.commit()

                resp.obj = item
        """

        output_adapter = PydanticSchemaAdapter(schema)
        if headers:
            headers = PydanticSchemaAdapter(headers)

        def decorator(f):

            cls._annotate(
                f,
                output_adapter=output_adapter,
                output_headers_adapter=headers,
                output_status_code=status_code,
                output_description=description,
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

                is_list = isinstance(obj, list) or hasattr(obj, "count")

                try:
                    if is_list:
                        resp.media = [
                            schema.model_validate(o).model_dump() for o in obj
                        ]
                    else:
                        resp.media = schema.model_validate(obj).model_dump()

                    resp.status_code = status_code

                except pd.ValidationError as e:
                    resp.status_code = HTTPStatus.BAD_REQUEST
                    resp.media = {"errors": cls._parse_error(e)}

            return wrapper

        return decorator

    @classmethod
    def expect(cls, responses):
        """
        Decorator for declaring **additional HTTP responses** that an endpoint may return.

        This decorator is used **only for OpenAPI documentation generation** and does not
        affect runtime behavior. It allows you to describe non-success responses
        (such as authentication or authorization errors) that clients should expect.

        :param codes: A mapping of HTTP status codes to human-readable descriptions.
                    Example: {401: "Invalid token", 404: "Item not found"}

        Usage::

            import dyne
            from dyne.ext.io.pydantic import expect

            api = dyne.API()

            @api.route("/secure-data")
            @expect(
                {
                    401: "Invalid access or refresh token",
                    403: "Insufficient permissions",
                }
            )
            async def get_data(req, resp):
                pass


            @api.route("/secure-data", methods=["GET"])
            @expect({
                401: InvalidTokenSchema,
                403: InsufficientPermissionsSchema
            })
            async def get_data(req, resp):
                pass


            @api.route("/secure-data", methods=["GET"])
            @expect({
                401: (InvalidTokenSchema, 'Invalid access or refresh token'),
                403: (InsufficientPermissionsSchema, 'Requires elevated administrative privileges')
            })
            async def get_data(req, resp):
                pass
        """

        def decorator(f):

            expect = cls._normalize_expect(f, responses)
            cls._apply_adapter(expect, PydanticSchemaAdapter)

            return f

        return decorator


input = PydanticIO.input
output = PydanticIO.output
expect = PydanticIO.expect
webhook = PydanticIO.webhook
