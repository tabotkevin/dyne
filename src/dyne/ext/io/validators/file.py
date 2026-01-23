from ..utils.filename import secure_filename


def validate_filename(
    file,
    *,
    sanitize: bool = False,
):
    if not file.filename:
        raise ValueError("Filename is missing.")

    try:
        safe = secure_filename(file.filename)
    except ValueError as exc:
        raise ValueError(f"Invalid filename: {exc}") from exc

    if safe != file.filename:
        if sanitize:
            file._upload.filename = safe
        else:
            raise ValueError("Filename contains unsafe characters.")
