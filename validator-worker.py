#!/usr/bin/env python3
"""
Validator worker: reads one JSON request from stdin, executes the operation,
and writes one JSON response to stdout.
"""

import json
import os
import sys


MAX_REQUEST_BYTES = 10 * 1024 * 1024


# Redirect operation stdout to stderr so only JSON goes to stdout
class StdoutRedirector:
    def __init__(self, target):
        self.target = target

    def write(self, text):
        self.target.write(text)

    def flush(self):
        self.target.flush()


def main():
    # Remove remote delegation env vars to prevent recursion
    os.environ.pop("DEBUGREPAIR_VALIDATOR_URL", None)
    os.environ.pop("DEBUGREPAIR_VALIDATOR_TOKEN", None)

    # Redirect stdout to stderr for operation diagnostics
    original_stdout = sys.stdout
    sys.stdout = StdoutRedirector(sys.stderr)

    try:
        # Read bounded JSON from stdin
        input_data = sys.stdin.read(MAX_REQUEST_BYTES + 1)
        if len(input_data) > MAX_REQUEST_BYTES:
            raise ValueError(f"Request exceeds {MAX_REQUEST_BYTES} bytes")

        request = json.loads(input_data)

        # Validate request structure
        if not isinstance(request, dict):
            raise ValueError("Request must be a JSON object")

        operation = request.get("operation")
        bug_id = request.get("bug_id")
        method = request.get("method")

        # Validate types
        if not isinstance(operation, str):
            raise ValueError("operation must be a string")
        if not isinstance(bug_id, str):
            raise ValueError("bug_id must be a string")
        if not isinstance(method, str):
            raise ValueError("method must be a string")

        # Validate operation allowlist
        allowed_operations = {
            "validate_patch",
            "check_instrumented_compiles",
            "collect_output",
        }
        if operation not in allowed_operations:
            raise ValueError(
                f"Invalid operation: {operation}. "
                f"Allowed: {', '.join(sorted(allowed_operations))}"
            )

        # Add src to path (resolved from this file)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, os.path.join(script_dir, "src"))

        # Import operation modules
        from defs.bug_info import BugInfo

        # Construct BugInfo from bug_id
        bug_info = BugInfo(bug_id)

        # Execute the operation
        if operation == "validate_patch":
            from utils.validate import validate_patch
            result = validate_patch(bug_id, method, bug_info)
        elif operation == "check_instrumented_compiles":
            from utils.collect_output import check_instrumented_compiles
            result = check_instrumented_compiles(bug_id, bug_info, method)
        elif operation == "collect_output":
            from utils.collect_output import collect_output
            result = collect_output(bug_id, bug_info, method)
        else:
            raise ValueError(f"Unhandled operation: {operation}")

        # Validate result shape before returning ok=true
        if operation in ("validate_patch", "check_instrumented_compiles"):
            if not isinstance(result, tuple) or len(result) != 2:
                raise ValueError(f"{operation} must return a 2-tuple")
            if not isinstance(result[0], bool) or not isinstance(result[1], str):
                raise ValueError(f"{operation} must return (bool, str)")
            # Convert tuple to list for JSON
            result = list(result)
        elif operation == "collect_output":
            if not isinstance(result, str):
                raise ValueError("collect_output must return a string")

        # Write success response to original stdout
        response = {"ok": True, "result": result}
        original_stdout.write(json.dumps(response))
        original_stdout.write("\n")
        original_stdout.flush()
        sys.exit(0)

    except Exception as exc:
        # Sanitize error message (don't expose env values)
        error_msg = str(exc)
        # Simple sanitization: remove common patterns
        for env_var in os.environ:
            env_value = os.environ[env_var]
            if env_value and len(env_value) > 3:
                error_msg = error_msg.replace(env_value, "[REDACTED]")

        response = {"ok": False, "error": error_msg}
        original_stdout.write(json.dumps(response))
        original_stdout.write("\n")
        original_stdout.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
