"""One-shot runner for the controlled demo telemetry source."""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error

BASE = os.getenv("BACKEND_URL", "https://vitalguard-risk-api-bhavithav.onrender.com").rstrip("/")
USERNAME = os.getenv("VITALGUARD_DEMO_USERNAME", "").strip()
PASSWORD = os.getenv("VITALGUARD_DEMO_PASSWORD", "").strip()

def post(path: str, payload: dict, token: str | None = None) -> dict:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())

if not USERNAME or not PASSWORD:
    raise SystemExit("Demo credentials are not configured")

try:
    login = post("/api/v1/auth/login", {"username": USERNAME, "password": PASSWORD})
    token = login.get("access_token")
    if not token:
        raise SystemExit("Authentication succeeded without an access token")
    result = post("/api/v1/demo/telemetry/tick", {}, token)
    print(json.dumps(result, separators=(",", ":")))
except urllib.error.HTTPError as exc:
    detail = exc.read().decode(errors="replace")
    raise SystemExit(f"Demo telemetry request failed: HTTP {exc.code} {detail}")
