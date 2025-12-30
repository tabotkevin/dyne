import io
from typing import Any, ClassVar, Iterable

from starlette.datastructures import Headers, UploadFile

try:
    from pydantic import GetCoreSchemaHandler
    from pydantic_core import core_schema
except ImportError as exc:
    raise RuntimeError(
        "Pydantic is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[pydantic]\n"
    ) from exc

from ..base import File


class FileField:
    max_size: ClassVar[int | None] = None
    allowed_extensions: ClassVar[Iterable[str] | None] = None

    file_validators = ["validate_size", "validate_extension"]

    @classmethod
    def validate_size(cls, file: File):
        if cls.max_size is not None and file.size > cls.max_size:
            raise ValueError(
                f"File too large ({file.size} bytes). Maximum allowed is {cls.max_size} bytes."
            )

    @classmethod
    def validate_extension(cls, file: File):
        if cls.allowed_extensions is not None:
            allowed = {e.lower().lstrip(".") for e in cls.allowed_extensions}
            if file.extension not in allowed:
                raise ValueError(
                    f"Invalid type '.{file.extension}'. Allowed: {', '.join(sorted(allowed))}"
                )

    @classmethod
    def validate(cls, value: Any) -> File:
        if isinstance(value, dict):
            filename = value.get("filename")
            content = value.get("content")
            content_type = value.get("content-type")

            if not filename or not content:
                raise ValueError(
                    "File dictionary must contain both 'filename' and 'content'."
                )

            headers = Headers({"content-type": content_type}) if content_type else None
            value = UploadFile(
                file=io.BytesIO(content), filename=filename, headers=headers
            )

        if not isinstance(value, UploadFile):
            raise ValueError(
                f"Expected a file upload, but received {type(value).__name__}."
            )

        file = File(value)

        for validator_name in cls.file_validators:
            validator = getattr(cls, validator_name)
            validator(file)

        return file

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_plain_validator_function(cls.validate)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string", "format": "binary"}
