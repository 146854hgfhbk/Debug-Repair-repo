#!/usr/bin/env python3
"""
Validator server: HTTP service for remote Defects4J validation.
Listens on loopback interface and spawns isolated worker subprocesses.
"""

import hmac
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional


MAX_REQUEST_BYTES = 10 * 1024 * 1024
TUPLE_OPERATIONS = {"validate_patch", "check_instrumented_compiles"}
ALLOWED_OPERATIONS = TUPLE_OPERATIONS | {"collect_output"}


def _positive_int_from_env(name: str, default: str) -> int:
    try:
        value = int(os.getenv(name, default))
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _valid_result_shape(operation: str, result) -> bool:
    if operation in TUPLE_OPERATIONS:
        return (
            isinstance(result, list)
            and len(result) == 2
            and isinstance(result[0], bool)
            and isinstance(result[1], str)
        )
    return operation == "collect_output" and isinstance(result, str)


class ValidationHandler(BaseHTTPRequestHandler):
    """HTTP request handler for validation operations."""

    # Class variables set by create_handler
    token: str = ""
    work_root: str = ""
    semaphore: Optional[threading.Semaphore] = None
    worker_timeout: int = 1800
    python_executable: str = sys.executable
    worker_script: str = ""
    max_request_bytes: int = MAX_REQUEST_BYTES

    def log_message(self, format, *args):
        """Log messages to stderr."""
        sys.stderr.write(f"{self.address_string()} - [{self.log_date_time_string()}] {format % args}\n")

    def do_GET(self):
        """Handle GET requests (health check)."""
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"status": "ok"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        """Handle POST requests (validation operations)."""
        if self.path != "/validate":
            self.send_error(404, "Not Found")
            return

        # Check authentication
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self.send_error(401, "Unauthorized: missing bearer token")
            return

        provided_token = auth_header[7:]  # Remove "Bearer " prefix
        if not hmac.compare_digest(provided_token, self.token):
            self.send_error(403, "Forbidden: invalid token")
            return

        # Check content type
        content_type = self.headers.get("Content-Type", "")
        if not content_type.startswith("application/json"):
            self.send_error(415, "Unsupported Media Type: expected application/json")
            return

        # Check content length
        content_length_str = self.headers.get("Content-Length")
        if not content_length_str:
            self.send_error(400, "Bad Request: missing Content-Length")
            return

        try:
            content_length = int(content_length_str)
        except ValueError:
            self.send_error(400, "Bad Request: invalid Content-Length")
            return

        if content_length <= 0:
            self.send_error(400, "Bad Request: Content-Length must be positive")
            return

        if content_length > self.max_request_bytes:
            self.send_error(413, "Request Entity Too Large")
            return

        # Read request body
        try:
            body = self.rfile.read(content_length).decode("utf-8")
            request_data = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.send_error(400, f"Bad Request: {exc}")
            return

        # Validate request structure
        if not isinstance(request_data, dict):
            self.send_error(400, "Bad Request: request must be a JSON object")
            return

        operation = request_data.get("operation")
        bug_id = request_data.get("bug_id")
        method = request_data.get("method")
        namespace = request_data.get("namespace", "")

        # Validate field types
        if not isinstance(operation, str):
            self.send_error(400, "Bad Request: operation must be a string")
            return
        if not isinstance(bug_id, str):
            self.send_error(400, "Bad Request: bug_id must be a string")
            return
        if not isinstance(method, str):
            self.send_error(400, "Bad Request: method must be a string")
            return
        if not isinstance(namespace, str):
            self.send_error(400, "Bad Request: namespace must be a string")
            return

        # Validate operation allowlist
        if operation not in ALLOWED_OPERATIONS:
            self.send_error(
                400,
                f"Bad Request: invalid operation (allowed: {', '.join(sorted(ALLOWED_OPERATIONS))})"
            )
            return

        # Acquire semaphore for concurrency control
        if self.semaphore:
            self.semaphore.acquire()

        try:
            result = self._handle_validation(request_data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode("utf-8"))
        except Exception as exc:
            error_msg = str(exc)
            # Sanitize error message
            for env_var in ["DEBUGREPAIR_VALIDATOR_TOKEN", "API_KEY", "SECRET"]:
                env_value = os.getenv(env_var, "")
                if env_value and len(env_value) > 3:
                    error_msg = error_msg.replace(env_value, "[REDACTED]")

            sys.stderr.write(f"[ERROR] Request failed: {error_msg[:200]}\n")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            response = {"ok": False, "error": "infrastructure failure"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
        finally:
            if self.semaphore:
                self.semaphore.release()

    def _handle_validation(self, request_data: dict) -> dict:
        """Execute validation in isolated worker."""
        # Create unique request directory
        request_id = str(uuid.uuid4())
        request_root = os.path.join(self.work_root, request_id)
        os.makedirs(request_root, exist_ok=True)

        try:
            # Prepare worker environment
            worker_env = os.environ.copy()
            worker_env["DEBUGREPAIR_TEMP_PATH"] = os.path.join(request_root, "temp")
            worker_env["DEBUGREPAIR_DEBUG_PATH"] = os.path.join(request_root, "debug")
            # Remove delegation env vars
            worker_env.pop("DEBUGREPAIR_VALIDATOR_URL", None)
            worker_env.pop("DEBUGREPAIR_VALIDATOR_TOKEN", None)

            # Create temp and debug directories
            os.makedirs(worker_env["DEBUGREPAIR_TEMP_PATH"], exist_ok=True)
            os.makedirs(worker_env["DEBUGREPAIR_DEBUG_PATH"], exist_ok=True)

            # Spawn worker
            worker_process = subprocess.Popen(
                [self.python_executable, self.worker_script],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=worker_env,
                text=True,
                start_new_session=True,
            )

            try:
                stdout, stderr = worker_process.communicate(
                    input=json.dumps(request_data),
                    timeout=self.worker_timeout,
                )
            except subprocess.TimeoutExpired:
                # Terminate process group
                self._terminate_worker_group(worker_process)
                raise RuntimeError(
                    f"Worker timed out after {self.worker_timeout} seconds"
                )

            # Parse worker response
            if not stdout.strip():
                raise RuntimeError(f"Worker produced no output (exit {worker_process.returncode})")

            try:
                result = json.loads(stdout)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Worker returned malformed JSON: {exc}")

            if not isinstance(result, dict):
                raise RuntimeError("Worker response must be a JSON object")

            if not isinstance(result.get("ok"), bool):
                raise RuntimeError("Worker response 'ok' field must be boolean")

            # Validate exit code consistency
            if result.get("ok"):
                if worker_process.returncode != 0:
                    raise RuntimeError(
                        f"Worker returned ok=true but exited with code {worker_process.returncode}"
                    )
                if "result" not in result:
                    raise RuntimeError("Worker returned ok=true without result field")
                if not _valid_result_shape(
                    request_data["operation"], result["result"]
                ):
                    raise RuntimeError("Worker returned invalid result shape")
            else:
                if worker_process.returncode == 0:
                    raise RuntimeError(
                        f"Worker returned ok=false but exited with code 0"
                    )
                if not isinstance(result.get("error"), str):
                    raise RuntimeError("Worker returned invalid error field")

                # Sanitize worker error
                error_msg = str(result["error"])
                if self.token and len(self.token) > 3:
                    error_msg = error_msg.replace(self.token, "[REDACTED]")
                result["error"] = error_msg

            return result

        finally:
            # Clean up request directory
            if os.path.exists(request_root):
                shutil.rmtree(request_root, ignore_errors=True)

    def _terminate_worker_group(self, process: subprocess.Popen):
        """Terminate worker and its process group."""
        platform = sys.platform
        grace_seconds = 2.0

        if platform.startswith("linux") and hasattr(os, "killpg"):
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

            deadline = time.monotonic() + grace_seconds
            while time.monotonic() < deadline:
                try:
                    process.wait(timeout=0.1)
                    return
                except subprocess.TimeoutExpired:
                    pass

            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        try:
            process.wait(timeout=max(1.0, grace_seconds))
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def create_handler():
    """Create handler class with configured class variables."""
    token = os.getenv("DEBUGREPAIR_VALIDATOR_TOKEN")
    if not token:
        raise ValueError("DEBUGREPAIR_VALIDATOR_TOKEN is required")

    work_root = os.getenv("DEBUGREPAIR_VALIDATOR_WORK_ROOT")
    if not work_root:
        raise ValueError("DEBUGREPAIR_VALIDATOR_WORK_ROOT is required")

    worker_count = _positive_int_from_env("DEBUGREPAIR_VALIDATOR_WORKERS", "4")
    worker_timeout = _positive_int_from_env(
        "DEBUGREPAIR_VALIDATOR_TIMEOUT", "1800"
    )
    python_executable = os.getenv("DEBUGREPAIR_PYTHON", sys.executable)

    # Worker script path resolved from this file
    worker_script = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "validator-worker.py",
    )

    # Create handler class with configured values
    class ConfiguredHandler(ValidationHandler):
        pass

    ConfiguredHandler.token = token
    ConfiguredHandler.work_root = work_root
    ConfiguredHandler.semaphore = threading.Semaphore(worker_count)
    ConfiguredHandler.worker_timeout = worker_timeout
    ConfiguredHandler.python_executable = python_executable
    ConfiguredHandler.worker_script = worker_script
    ConfiguredHandler.max_request_bytes = MAX_REQUEST_BYTES

    return ConfiguredHandler


def main():
    """Start the validation server."""
    bind_address = os.getenv("DEBUGREPAIR_VALIDATOR_BIND", "127.0.0.1")
    port = int(os.getenv("DEBUGREPAIR_VALIDATOR_PORT", "9001"))

    handler_class = create_handler()
    server = ThreadingHTTPServer((bind_address, port), handler_class)

    print(f"Validation server listening on {bind_address}:{port}", file=sys.stderr)
    print(f"Worker concurrency: {handler_class.semaphore._value}", file=sys.stderr)
    print(f"Worker timeout: {handler_class.worker_timeout}s", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...", file=sys.stderr)
        server.shutdown()


if __name__ == "__main__":
    main()
