from functools import wraps

try:
    import pydantic as pd
except ImportError as exc:
    raise RuntimeError(
        "Pydantic is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[pydantic]\n"
    ) from exc

from ..base import BaseIO


class PydanticIO(BaseIO):

    @staticmethod
    def _parse_error(error: pd.ValidationError):
        """Parse an error to return a dictionary of validation errors"""
        errors = {}
        for e in error.errors():
            loc = str(e.get("loc", ("unknown",))[-1])
            errors.setdefault(loc, []).append(e.get("msg"))
        return errors

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
                        `headers`, `cookies`, `params`, `query`.
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

        if location == "params":
            location = "query"
        final_key = key or ("data" if location in ["media", "form"] else location)

        def decorator(f):
            spec = cls._ensure_spec(f)
            if spec.get("args") is None:
                spec["args"] = []

            if location not in ["media", "form"]:
                spec["args"].append((schema, location))
            else:
                spec["input"] = (schema, location)

            @wraps(f)
            async def wrapper(req, resp, *args, **kwargs):
                raw_data = await cls._get_request_data(req, location)

                try:
                    # Validate (Pydantic V2 specific)
                    if isinstance(schema, type) and issubclass(schema, pd.BaseModel):
                        validated_obj = schema(**raw_data)
                        validated_data = validated_obj.model_dump()
                    else:
                        # Fallback for TypeAdapter or similar
                        validated_data = schema(raw_data)

                except pd.ValidationError as e:
                    resp.status_code = 400
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
                    resp.status_code = 400
                    resp.media = {"errors": cls._parse_error(e)}

            return wrapper

        return decorator


input = PydanticIO.input
output = PydanticIO.output
expect = PydanticIO.expect
