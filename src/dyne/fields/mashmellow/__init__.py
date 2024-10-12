import io

from marshmallow import ValidationError
from marshmallow.fields import Field

from dyne.fields import UploadFile


class FileField(Field):

    def __init__(self, allowed_extensions=None, max_size=None, **kwargs):
        self.allowed_extensions = allowed_extensions
        self.max_size = max_size
        super().__init__(**kwargs)

    def _deserialize(self, value, attr, data, **kwargs):
        if not value or "content" not in value or "filename" not in value:
            if not self.required:
                return None
            raise ValidationError("No file was uploaded.")
        try:
            file = UploadFile(io.BytesIO(value["content"]), filename=value["filename"])
        except Exception as e:
            raise ValidationError(f"Invalid file content: {e}")

        if self.allowed_extensions and file.extension not in self.allowed_extensions:
            raise ValidationError(f"File extension '{file.extension}' is not allowed.")

        if self.max_size and file.size > self.max_size:
            raise ValidationError(
                f"File is too large (max size is {self.max_size} bytes)."
            )

        return file
