"""Spins up the real quote-service (provided by the challenge, unmodified)
as a subprocess with controlled instability env vars, so integration and
e2e tests exercise the agent-service's HTTP client against genuine
quote-service behavior — not a mock of it — while still being 100%
deterministic via QUOTE_SEED and the failure/slow-rate env vars documented
in main.py. Shared at the top level so both tests/integration and tests/e2e
can use it.
"""
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path

import httpx
import pytest

QUOTE_SERVICE_DIR = Path(__file__).resolve().parents[2] / "quote-service"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_health(base_url: str, timeout_seconds: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url}/health", timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.2)
    raise RuntimeError(f"quote-service did not become healthy in time: {last_error}")


@pytest.fixture
def quote_service_factory():
    processes: list[subprocess.Popen] = []

    def _start(**env_overrides: str) -> str:
        port = _free_port()
        env = os.environ.copy()
        env.update({k: str(v) for k, v in env_overrides.items()})
        process = subprocess.Popen(
            ["uv", "run", "uvicorn", "app.main:app", "--port", str(port)],
            cwd=QUOTE_SERVICE_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        processes.append(process)
        base_url = f"http://127.0.0.1:{port}"
        _wait_for_health(base_url)
        return base_url

    yield _start

    for process in processes:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
