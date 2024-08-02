from starlette.exceptions import HTTPException


def abort(
    status_code: int, detail: str | None = None, headers: dict[str, str] | None = None
) -> None:
    raise HTTPException(
        status_code=status_code, detail=detail, headers=headers
    ) from None
