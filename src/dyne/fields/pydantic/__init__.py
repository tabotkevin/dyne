import io

from dyne.fields import UploadFile


class File(UploadFile):

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, value, self_instance):
        if not value or "content" not in value or "filename" not in value:
            raise ValueError("No file was uploaded.")
        try:
            file = File(io.BytesIO(value["content"]), filename=value["filename"])
        except Exception as e:
            raise ValueError(f"Invalid file content: {e}")

        return file

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        return {"type": "string", "format": "binary"}
