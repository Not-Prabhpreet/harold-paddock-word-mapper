"""Shared helpers for the asset tools: API keys from .env, JSON HTTP calls, downloads, polling."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    """Read KEY=value lines from the project's .env file into os.environ (never overrides)."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def require_key(name: str) -> str:
    load_env()
    key = os.environ.get(name, "")
    if not key:
        sys.exit(f"Missing {name}. Copy .env.example to .env and paste your key there.")
    return key


def request(method: str, url: str, headers: dict, body: dict | None = None, raw: bool = False, timeout: int = 120):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={**headers, **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:800]
        sys.exit(f"HTTP {e.code} from {url}\n{detail}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error calling {url}: {e.reason}")
    return payload if raw else json.loads(payload or b"{}")


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as resp, open(dest, "wb") as f:
        while chunk := resp.read(1 << 16):
            f.write(chunk)
    return dest


def data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def poll(fetch, label: str, interval: float = 5.0, timeout: float = 1800.0) -> dict:
    """Call fetch() until status is SUCCEEDED; exit on FAILED/CANCELED/timeout."""
    start = time.time()
    last = None
    while True:
        task = fetch()
        status = task.get("status")
        progress = task.get("progress", 0)
        if (status, progress) != last:
            print(f"  {label}: {status} {progress}%")
            last = (status, progress)
        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELED", "EXPIRED"):
            sys.exit(f"{label} {status}: {task.get('task_error') or task}")
        if time.time() - start > timeout:
            sys.exit(f"{label} timed out after {int(timeout)}s; task id {task.get('id')}")
        time.sleep(interval)


def read_json(path: Path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
