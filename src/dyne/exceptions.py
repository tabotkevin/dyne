from typing import Dict, Optional

from starlette.exceptions import HTTPException


def abort(
    status_code: int,
    detail: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
) -> None:
    raise HTTPException(
        status_code=status_code, detail=detail, headers=headers
    ) from None
