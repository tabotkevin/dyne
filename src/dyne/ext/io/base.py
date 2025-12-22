import abc
import os
from typing import BinaryIO, Optional

from starlette.concurrency import run_in_threadpool
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile as BaseFile


class UploadFile(BaseFile):

    def __init__(
        self,
        file: BinaryIO,
        *,
        size: Optional[int] = None,
        filename: Optional[str] = None,
        headers: Optional[Headers] = None,
    ) -> None:
        super().__init__(file, size=size, filename=filename, headers=headers)
        if not self.size:
            self._size()

    async def save(self, destination, buffer_size=16384):
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

    def _size(self):
        current_position = self.file.tell()
        self.file.seek(0, os.SEEK_END)
        size = self.file.tell()
        self.file.seek(current_position)
        self.size = size

    @property
    def extension(self) -> str:
        return os.path.splitext(self.filename)[1].lower().strip(".")


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
    def _ensure_spec(f):
        """
        Stores metadata about the route for later use during OpenAPI generation.
        """
        if not hasattr(f, "_spec"):
            f._spec = {}
        return f._spec

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

            api = dyne.API()

            @api.route("/create")
            @input(ItemCreate)
            @expect(
                {
                    401: "Invalid access or refresh token",
                    403: "Please verify your account",
                }
            )
            async def create_items(req, resp):
                resp.text = "Item created"
        """

        def decorator(f):
            spec = cls._ensure_spec(f)
            if "responses" not in spec:
                spec["responses"] = {}
            spec["responses"].update(responses)
            return f

        return decorator

    @classmethod
    def webhook(cls, method="GET", blueprint=None, endpoint_name=None):
        def decorator(f):
            spec = cls._ensure_spec(f)
            spec.update(
                webhook={
                    "blueprint": blueprint,
                    "endpoint_name": endpoint_name,
                    "methods": [method],
                }
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

    @classmethod
    @abc.abstractmethod
    def input(cls, schema, location="media", key=None, unknown=None):
        pass

    @classmethod
    @abc.abstractmethod
    def output(cls, schema, status_code=200, headers=None, description=None):
        pass
