"""Remote validation client for delegating Defects4J operations."""

import json
import os
import urllib.request
from typing import Any
from urllib.error import HTTPError, URLError


class RemoteValidationError(Exception):
    """Raised when remote validation infrastructure fails."""
    pass


def is_remote_validation_enabled() -> bool:
    """Check if remote validation is configured."""
    return bool(os.getenv("DEBUGREPAIR_VALIDATOR_URL"))


def request_remote_validation(
    operation: str,
    bug_id: str,
    method: str,
) -> Any:
    """
    Send a validation request to the remote service.

    Args:
        operation: One of validate_patch, check_instrumented_compiles, collect_output
        bug_id: Defects4J bug identifier like Chart-1
        method: The method source code to validate

    Returns:
        The operation result (tuple or string depending on operation)

    Raises:
        RemoteValidationError: On transport, HTTP, or worker failures
    """
    url = os.getenv("DEBUGREPAIR_VALIDATOR_URL")
    token = os.getenv("DEBUGREPAIR_VALIDATOR_TOKEN", "")
    timeout_str = os.getenv("DEBUGREPAIR_REMOTE_VALIDATION_TIMEOUT", "1860")
    namespace = os.getenv("DEBUGREPAIR_LLM_LABEL", "")

    if not url:
        raise RemoteValidationError("DEBUGREPAIR_VALIDATOR_URL not configured")

    if not token:
        raise RemoteValidationError("DEBUGREPAIR_VALIDATOR_TOKEN required")

    try:
        timeout = int(timeout_str)
        if timeout <= 0:
            raise ValueError("timeout must be positive")
    except (ValueError, TypeError) as exc:
        raise RemoteValidationError(f"Invalid timeout configuration") from exc

    url = url.rstrip("/")
    if not url.endswith("/validate"):
        url += "/validate"

    payload = {
        "operation": operation,
        "bug_id": bug_id,
        "method": method,
        "namespace": namespace,
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )

    try:
        response = urllib.request.urlopen(request, timeout=timeout)
        response_data = response.read().decode("utf-8")
        response.close()
    except HTTPError as exc:
        raise RemoteValidationError(
            f"Remote validator HTTP {exc.code}: {exc.reason}"
        ) from exc
    except URLError as exc:
        raise RemoteValidationError(
            f"Remote validator connection failed: {exc.reason}"
        ) from exc
    except Exception as exc:
        raise RemoteValidationError(
            f"Remote validator request failed: {exc}"
        ) from exc

    try:
        response_obj = json.loads(response_data)
    except json.JSONDecodeError as exc:
        raise RemoteValidationError(
            f"Remote validator returned malformed JSON: {exc}"
        ) from exc

    if not isinstance(response_obj, dict):
        raise RemoteValidationError(
            "Remote validator response must be a JSON object"
        )

    if not response_obj.get("ok"):
        error_msg = response_obj.get("error", "unknown error")
        raise RemoteValidationError(f"Remote validator worker error: {error_msg}")

    if "result" not in response_obj:
        raise RemoteValidationError(
            "Remote validator response missing result field"
        )

    result = response_obj["result"]

    # Validate result shape by operation
    if operation in ("validate_patch", "check_instrumented_compiles"):
        if not isinstance(result, list) or len(result) != 2:
            raise RemoteValidationError(
                f"Invalid {operation} result: expected [bool, str]"
            )
        if not isinstance(result[0], bool) or not isinstance(result[1], str):
            raise RemoteValidationError(
                f"Invalid {operation} result types: expected [bool, str]"
            )
    elif operation == "collect_output":
        if not isinstance(result, str):
            raise RemoteValidationError(
                "Invalid collect_output result: expected string"
            )

    return result
