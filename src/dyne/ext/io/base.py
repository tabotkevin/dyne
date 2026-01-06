import abc
import os

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile


class File:
    def __init__(self, upload: UploadFile):
        self._upload = upload
        self.file = self._upload.file

    def _compute_size(self):
        file = self._upload.file
        pos = file.tell()
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(pos)
        self._upload.size = size

    @property
    def _in_memory(self) -> bool:
        return self._upload._in_memory

    @property
    def filename(self) -> str:
        return self._upload.filename

    @property
    def headers(self):
        return self._upload.headers

    @property
    def content_type(self) -> str | None:
        return self._upload.content_type

    @property
    def size(self) -> int:
        size = getattr(self._upload, "size", None)
        if size is None:
            self._compute_size()
        return self._upload.size

    async def read(self, size: int = -1) -> bytes:
        return await self._upload.read(size)

    async def write(self, data: bytes) -> None:
        return await self._upload.write(data)

    async def seek(self, offset: int) -> None:
        return await self._upload.seek(offset)

    async def close(self) -> None:
        return await self._upload.close()

    async def asave(self, destination, buffer_size=16384):
        close_destination = False

        if hasattr(destination, "__fspath__"):
            destination = os.fspath(destination)

        if isinstance(destination, str):
            destination = await run_in_threadpool(open, destination, "wb")
            close_destination = True

        try:
            while True:
                chunk = await self.read(buffer_size)
                if not chunk:
                    break
                await run_in_threadpool(destination.write, chunk)
        finally:
            if close_destination:
                await run_in_threadpool(destination.close)

    def save(self, destination, buffer_size: int = 16384):
        close_destination = False

        if hasattr(destination, "__fspath__"):
            destination = os.fspath(destination)

        if isinstance(destination, str):
            destination = open(destination, "wb")
            close_destination = True

        try:
            while True:
                chunk = self.file.read(buffer_size)
                if not chunk:
                    break
                destination.write(chunk)
        finally:
            if close_destination:
                destination.close()

    @property
    def extension(self) -> str:
        return os.path.splitext(self.filename or "")[1].lower().lstrip(".")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"filename={self.filename!r}, "
            f"size={self.size!r}, "
            f"headers={self.headers!r})"
        )


class SchemaAdapter(abc.ABC):
    def __init__(self, schema):
        self.schema = schema
        self._bound = False

    @abc.abstractmethod
    def get_openapi_schema(self):
        """Return OpenAPI-compatible schema object/dict."""
        pass

    @abc.abstractmethod
    def has_file(self) -> bool:
        pass

    @abc.abstractmethod
    def get_parameters(self, location: str) -> list:
        pass

    @abc.abstractmethod
    def bind(self, spec):
        """Bind schema(s) to the APISpec instance."""
        pass

    def media_type(self, location: str) -> str:
        if location == "form":
            return (
                "multipart/form-data"
                if self.has_file()
                else "application/x-www-form-urlencoded"
            )

        return "application/json"


class BaseIO(abc.ABC):

    @staticmethod
    async def _get_request_data(req, location):
        if location.startswith("header"):
            return req.headers
        elif location.startswith("cookie"):
            return req.cookies
        elif location.startswith("params") or location == "query":
            return req.params.normalize()
        else:
            # Assumes 'media', 'form', or 'json'
            return await req.media()

    @staticmethod
    def _annotate(f, **kwargs):
        """
        Stores metadata about the route for later use during OpenAPI generation.
        """
        if not hasattr(f, "_spec"):
            f._spec = {}
        for key, value in kwargs.items():
            f._spec[key] = value

    @staticmethod
    def _validate_location(location: str) -> str:
        allowed_locations = (
            "cookie",
            "form",
            "header",
            "json",
            "media",
            "params",
            "query",
            "yaml",
        )

        if not isinstance(location, str):
            raise TypeError(
                f"Invalid location type: expected str, got {type(location).__name__}"
            )

        if location not in allowed_locations:
            allowed = ", ".join(allowed_locations)
            raise ValueError(
                f"Invalid location '{location}'. " f"Expected one of: {allowed}."
            )

        return location

    @staticmethod
    def _normalize_expect(f, responses):
        """
        Normalize expect(...) input into a canonical internal structure.

        Output format:
        {
            "401": {
                "schema": <raw schema or None>,
                "description": <str or None>
            }
        }
        """
        spec = f._spec = getattr(f, "_spec", {})
        expect = spec.setdefault("expect", {})

        for status_code, value in responses.items():
            schema = None
            description = None

            # CASE: (schema, description)
            if isinstance(value, (tuple, list)):
                for v in value:
                    if isinstance(v, str):
                        description = v
                    else:
                        schema = v

            # CASE: description only
            elif isinstance(value, str):
                description = value

            # CASE: schema only
            else:
                schema = value

            expect[str(status_code)] = {
                "schema": schema,
                "description": description,
            }

        return expect

    @staticmethod
    def _apply_adapter(expect, adapter_cls):
        for meta in expect.values():
            schema = meta.pop("schema", None)
            meta["adapter"] = adapter_cls(schema) if schema is not None else None

    @classmethod
    def webhook(cls, name: str | None = None):
        def _apply(f, name=None):
            cls._annotate(f, webhook={"endpoint_name": name})
            return f

        if callable(name):
            return _apply(name)

        def decorator(f):
            return _apply(f, name=name)

        return decorator

    @classmethod
    @abc.abstractmethod
    def expect(cls, responses):
        pass

    @classmethod
    @abc.abstractmethod
    def input(cls, schema, location="media", key=None, unknown=None):
        pass

    @classmethod
    @abc.abstractmethod
    def output(cls, schema, status_code=200, headers=None, description=None):
        pass
