from functools import wraps

try:
    import marshmallow as ma
except ImportError as exc:
    raise RuntimeError(
        "Marshmallow is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[marshmallow]\n"
    ) from exc

from ..base import BaseIO


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
                        `headers`, `cookies`, `params`, `query`.
        :param key: The keyword argument name used to inject the validated data
                    into the route handler.
                    Defaults to `"data"`.
        :param unknown: Value passed to `Schema.load(unknown=...)`.
                        Defaults to `marshmallow.EXCLUDE` for `headers` and `cookies`.

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
        if location == "params":
            location = "query"
        final_key = key or ("data" if location in ["media", "form"] else location)

        if unknown is None and location.startswith(("header", "cookie")):
            unknown = ma.EXCLUDE

        # Handle Instance vs Class (Support Schema(partial=True))
        if isinstance(schema, type) and issubclass(schema, ma.Schema):
            loader = schema()
        else:
            loader = schema

        def decorator(f):
            spec = cls._ensure_spec(f)
            if spec.get("args") is None:
                spec["args"] = []

            if location not in ["media", "form"]:
                spec["args"].append((loader, location))
            else:
                spec["input"] = (loader, location)

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

        def decorator(f):
            spec = cls._ensure_spec(f)
            spec.update(
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


input = MarshmallowIO.input
output = MarshmallowIO.output
expect = MarshmallowIO.expect
webhook = MarshmallowIO.webhook
