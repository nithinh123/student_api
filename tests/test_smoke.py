"""
Stage 6 – Smoke Tests
Fast sanity: health check + one full student transaction.
"""

import os
import requests

BASE = os.environ.get("API_BASE_URL", "http://localhost:5000")


def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "healthy"


def test_smoke_add_and_delete():
    payload = {"name": "Smoke User", "grade": "A", "email": "smoke@test.com"}
    r = requests.post(f"{BASE}/students", json=payload, timeout=5)
    assert r.status_code == 201
    sid = r.json()["id"]

    r2 = requests.delete(f"{BASE}/students/{sid}", timeout=5)
    assert r2.status_code == 200
