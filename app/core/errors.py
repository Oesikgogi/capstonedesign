from typing import Any


def error_detail(code: str, message: str, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "meta": meta or {},
    }
