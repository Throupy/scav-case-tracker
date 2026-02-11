from __future__ import annotations
from typing import Any

from flask import jsonify


def success_response(*, data: Any = None, message: str = "OK", status_code: int = 200):
    """standard success payload for JSON endpoints..."""
    payload = {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
    }
    return jsonify(payload), status_code


def error_response(
    *,
    message: str,
    error_code: str,
    status_code: int,
    details: dict[str, Any] | None = None,
):
    """Standard error payload for JSON endpoints"""
    payload = {
        "success": False,
        "message": message,
        "data": None,
        "error": {
            "code": error_code,
            "details": details or {}
        },
    }
    return jsonify(payload), status_code