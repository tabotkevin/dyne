import os
import re
import unicodedata

INVALID_CHARS = re.compile(r"[^\w.\- ]")


def secure_filename(filename: str, *, allow_unicode: bool = False) -> str:
    if not filename:
        raise ValueError("Filename cannot be empty.")

    if allow_unicode:
        filename = unicodedata.normalize("NFC", filename)
    else:
        filename = (
            unicodedata.normalize("NFKD", filename)
            .encode("ascii", "ignore")
            .decode("ascii")
        )

    filename = os.path.basename(filename)

    filename = filename.strip()

    if filename in {"", ".", ".."}:
        raise ValueError("Invalid filename.")

    if any(ord(c) < 32 for c in filename):
        raise ValueError("Filename contains control characters.")

    filename = INVALID_CHARS.sub("", filename)

    return filename
