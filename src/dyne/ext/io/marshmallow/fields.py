import io
from typing import Iterable

from starlette.datastructures import Headers, UploadFile

try:
    from marshmallow import ValidationError
    from marshmallow.fields import Field
except ImportError as exc:
    raise RuntimeError(
        "Marshmallow is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[marshmallow]\n"
    ) from exc

from ..base import File


class FileField(Field):
    file_validators = ["validate_size", "validate_extension"]

    def __init__(
        self,
        *,
        max_size: int | None = None,
        allowed_extensions: Iterable[str] | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.max_size = max_size
        self.allowed_extensions = (
            {e.lower().lstrip(".") for e in allowed_extensions}
            if allowed_extensions
            else None
        )
        self.active_file_validators = list(self.file_validators)

    def validate_size(self, file: File):
        if self.max_size is not None and file.size > self.max_size:
            raise ValidationError(
                f"File too large ({file.size} bytes). Maximum allowed is {self.max_size} bytes."
            )

    def validate_extension(self, file: File):
        if self.allowed_extensions is not None:
            if file.extension not in self.allowed_extensions:
                raise ValidationError(
                    f"Invalid type '.{file.extension}'. Allowed: {', '.join(sorted(self.allowed_extensions))}"
                )

    def _deserialize(self, value, attr, data, **kwargs):

        if isinstance(value, dict):
            filename = value.get("filename")
            content = value.get("content")
            content_type = value.get("content-type")

            if not filename or not content:
                raise ValidationError(
                    "File dictionary must contain both 'filename' and 'content'."
                )

            headers = Headers({"content-type": content_type}) if content_type else None
            value = UploadFile(
                file=io.BytesIO(content), filename=filename, headers=headers
            )

        if not isinstance(value, UploadFile):
            raise ValidationError(
                f"Expected an isinstance of starlette's UploadFile, but received {type(value).__name__}."
            )

        file = File(value)

        for validator_name in self.active_file_validators:
            validator = getattr(self, validator_name)
            validator(file)

        return file

    def _jsonschema_type_mapping(self):
        return {"type": "string", "format": "binary"}
