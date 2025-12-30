from functools import wraps

try:
    import marshmallow as ma
except ImportError as exc:
    raise RuntimeError(
        "Marshmallow is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[marshmallow]\n"
    ) from exc


from ..base import BaseIO, SchemaAdapter
from .fields import FileField


class MarshmallowSchemaAdapter(SchemaAdapter):
    def __init__(self, schema):
        super().__init__(schema=schema)
        self.ma_plugin = None

    def bind(self, spec):
        if self._bound:
            return

        from apispec.ext.marshmallow import MarshmallowPlugin

        for plugin in spec.plugins:
            if isinstance(plugin, MarshmallowPlugin):
                self.ma_plugin = plugin
                break

        if not self.ma_plugin:
            raise RuntimeError("MarshmallowPlugin not registered with APISpec")

        self.ma_plugin.converter.field_mapping[FileField] = ("string", "binary")

    def get_openapi_schema(self):
        return self.schema

    def has_file(self):
        fields = getattr(self.schema, "_declared_fields", {})
        return any(isinstance(f, FileField) for f in fields.values())

    def get_parameters(self, location):
        if not self.ma_plugin:
            raise RuntimeError("MarshmallowPlugin not registered with APISpec")

        schema = self.schema() if isinstance(self.schema, type) else self.schema
        return self.ma_plugin.converter.schema2parameters(
            schema,
            location=location,
        )


class MarshmallowIO(BaseIO):

    @classmethod
    def input(cls, schema, location="media", key=None, unknown=None):
        """
        Decorator for validating request data using a **Marshmallow schema**.

        The request data is extracted from the specified location, validated using
        the provided Marshmallow schema, and injected into the route handler as a
        keyword-only argument.

        On successful validation:
        - The deserialized Python `dict` returned by `Schema.load()` is injected.

        On validation failure:
        - A `400 Bad Request` response is returned with Marshmallow error messages.

        :param schema: A subclass of `marshmallow.Schema`.
        :param location: Where to read data from.
                        Supported values: `media` (json, form, yaml),
                        `header`, `cookie`, `param`, `query`.
        :param key: The keyword argument name used to inject the validated data
                    into the route handler.
                    Defaults to `"data"`.
        :param unknown: Value passed to `Schema.load(unknown=...)`.
                        Defaults to `marshmallow.EXCLUDE` for `header` and `cookie`.

        Usage::

            import time
            from marshmallow import Schema, fields
            import dyne

            class ItemSchema(Schema):
                price = fields.Float(required=True)
                title = fields.String(required=True)

            api = dyne.API()

            @api.route("/create")
            @api.input(ItemSchema)
            async def create_item(req, resp, *, data):
                @api.background.task
                def process_item(item):
                    time.sleep(1)
                    print(item)  # {"price": 9.99, "title": "Marshmallow book"}

                process_item(data)
                resp.media = {"msg": "created"}

            # Client request
            r = api.client.post("http://;/create", json={"price": 9.99, "title": "Marshmallow book"})
        """
        cls._validate_location(location)

        if location == "params":
            location = "query"
        final_key = key or ("data" if location in ["media", "form"] else location)

        if unknown is None and location in {"header", "cookie"}:
            unknown = ma.EXCLUDE

        if isinstance(schema, type) and issubclass(schema, ma.Schema):
            loader = schema()
        else:
            loader = schema

        input_adapter = MarshmallowSchemaAdapter(schema)

        def decorator(f):

            cls._annotate(
                f,
                input_adapter=input_adapter,
                input_location=location,
            )

            @wraps(f)
            async def wrapper(req, resp, *args, **kwargs):
                raw_data = await cls._get_request_data(req, location)

                try:
                    validated_data = loader.load(raw_data, unknown=unknown)
                except ma.ValidationError as e:
                    resp.status_code = 400
                    resp.media = {"errors": e.messages}
                    return

                return await f(
                    req, resp, *args, **kwargs, **{final_key: validated_data}
                )

            return wrapper

        return decorator

    @classmethod
    def output(cls, schema, status_code=200, headers=None, description=None):
        """
        A decorator for serializing response data using a **Marshmallow schema**.

        This decorator serializes response objects (such as dictionaries or ORM/
        SQLAlchemy models) using the provided Marshmallow schema before returning
        the response.

        Features:
        - Supports dictionaries and ORM objects
        - Uses Marshmallow's `dump` mechanism
        - Can serialize single objects or collections
        - Used only for **response serialization**, not request validation

        :param schema: A Marshmallow `Schema` instance or class used to serialize
                    the response object.

        Usage::
            from marshmallow import Schema, fields
            from sqlalchemy import Column, Integer, String
            import dyne

            from .database import session, Base


            class Item(Base):
                __tablename__ = "items"
                id = Column(Integer, primary_key=True)
                name = Column(String)


            class ItemSchema(Schema):
                id = fields.Int()
                name = fields.Str()


            api = dyne.API()


            @api.route("/items")
            @output(ItemSchema(many=True))
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

        output_adapter = MarshmallowSchemaAdapter(schema)
        if headers:
            headers = MarshmallowSchemaAdapter(headers)

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

                if isinstance(schema, ma.Schema):
                    dumper = schema
                else:
                    is_list = isinstance(obj, list) or hasattr(obj, "count")
                    dumper = schema(many=is_list)

                try:
                    resp.media = dumper.dump(obj)
                    resp.status_code = status_code
                except ma.ValidationError as e:
                    resp.status_code = 400
                    resp.media = {"errors": e.messages}

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
            from dyne.ext.io.marshmallow import expect

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
            cls._apply_adapter(expect, MarshmallowSchemaAdapter)

            return f

        return decorator


input = MarshmallowIO.input
output = MarshmallowIO.output
expect = MarshmallowIO.expect
webhook = MarshmallowIO.webhook
