import io

import pytest
from starlette.datastructures import UploadFile

from dyne.ext.io import File
from dyne.ext.io.validators.file import validate_filename


def make_file(filename: str) -> File:
    upload = UploadFile(
        filename=filename,
        file=io.BytesIO(b"dummy"),
    )
    return File(upload)


@pytest.mark.parametrize(
    "filename",
    [
        "../secret.txt",
        "file\nname.txt",
        "résumé.pdf",
        " file.txt ",
        "file?.txt",
        "",
        ".",
        "..",
    ],
)
def test_invalid_filenames_sanitize_false(filename):
    file = make_file(filename)
    with pytest.raises(ValueError):
        validate_filename(file)


def test_invalid_filenames_sanitize_true():
    file = make_file("../secret.txt")
    validate_filename(file, sanitize=True)
    assert file.filename == "secret.txt"

    file = make_file("résumé.pdf")
    validate_filename(file, sanitize=True)
    assert file.filename == "resume.pdf"

    file = make_file(" file.txt ")
    validate_filename(file, sanitize=True)
    assert file.filename == "file.txt"

    file = make_file("file?.txt")
    validate_filename(file, sanitize=True)
    assert file.filename == "file.txt"
