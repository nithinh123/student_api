"""
Stage 8 – Contract Tests
JSON schema validation + SLA response-time assertions.
"""

import os
import time
import requests
import jsonschema
import pytest

BASE = os.environ.get("API_BASE_URL", "http://localhost:5000")

SLA_MS = int(os.environ.get("SLA_MS", "300"))  # 300 ms default

# ── Schemas ───────────────────────────────────────────────────────────────────

STUDENT_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "grade", "email"],
    "properties": {
        "id":    {"type": "integer"},
        "name":  {"type": "string", "minLength": 1},
        "grade": {"type": "string", "minLength": 1},
        "email": {"type": "string", "minLength": 1},
    },
    "additionalProperties": False,
}

LIST_SCHEMA = {
    "type": "object",
    "required": ["students", "count"],
    "properties": {
        "students": {"type": "array", "items": STUDENT_SCHEMA},
        "count":    {"type": "integer", "minimum": 0},
    },
    "additionalProperties": False,
}

HEALTH_SCHEMA = {
    "type": "object",
    "required": ["status", "timestamp"],
    "properties": {
        "status":    {"type": "string"},
        "timestamp": {"type": "number"},
    },
}

ERROR_SCHEMA = {
    "type": "object",
    "required": ["error"],
    "properties": {
        "error": {"type": "string"},
    },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _timed_get(url):
    t0 = time.monotonic()
    r = requests.get(url, timeout=5)
    elapsed_ms = (time.monotonic() - t0) * 1000
    return r, elapsed_ms


def _timed_post(url, payload):
    t0 = time.monotonic()
    r = requests.post(url, json=payload, timeout=5)
    elapsed_ms = (time.monotonic() - t0) * 1000
    return r, elapsed_ms


def _timed_delete(url):
    t0 = time.monotonic()
    r = requests.delete(url, timeout=5)
    elapsed_ms = (time.monotonic() - t0) * 1000
    return r, elapsed_ms


# ── Schema Tests ──────────────────────────────────────────────────────────────

class TestSchemaContracts:
    def test_health_schema(self):
        r, _ = _timed_get(f"{BASE}/health")
        jsonschema.validate(r.json(), HEALTH_SCHEMA)

    def test_list_schema_empty(self):
        r, _ = _timed_get(f"{BASE}/students")
        jsonschema.validate(r.json(), LIST_SCHEMA)

    def test_add_student_schema(self):
        r, _ = _timed_post(
            f"{BASE}/students",
            {"name": "Schema User", "grade": "A", "email": "schema@test.com"},
        )
        assert r.status_code == 201
        jsonschema.validate(r.json(), STUDENT_SCHEMA)
        # cleanup
        requests.delete(f"{BASE}/students/{r.json()['id']}", timeout=5)

    def test_get_student_schema(self):
        r, _ = _timed_post(
            f"{BASE}/students",
            {"name": "Schema Get", "grade": "B", "email": "sget@test.com"},
        )
        sid = r.json()["id"]
        r2, _ = _timed_get(f"{BASE}/students/{sid}")
        jsonschema.validate(r2.json(), STUDENT_SCHEMA)
        requests.delete(f"{BASE}/students/{sid}", timeout=5)

    def test_404_error_schema(self):
        r, _ = _timed_get(f"{BASE}/students/999999")
        jsonschema.validate(r.json(), ERROR_SCHEMA)

    def test_400_error_schema(self):
        r, _ = _timed_post(f"{BASE}/students", {})
        jsonschema.validate(r.json(), ERROR_SCHEMA)

    def test_list_with_data_schema(self):
        r, _ = _timed_post(
            f"{BASE}/students",
            {"name": "Schema List", "grade": "C", "email": "slist@test.com"},
        )
        sid = r.json()["id"]
        r2, _ = _timed_get(f"{BASE}/students")
        jsonschema.validate(r2.json(), LIST_SCHEMA)
        requests.delete(f"{BASE}/students/{sid}", timeout=5)


# ── SLA Tests ─────────────────────────────────────────────────────────────────

class TestSLAContracts:
    def test_health_sla(self):
        _, ms = _timed_get(f"{BASE}/health")
        assert ms < SLA_MS, f"Health check took {ms:.1f}ms (SLA={SLA_MS}ms)"

    def test_list_students_sla(self):
        _, ms = _timed_get(f"{BASE}/students")
        assert ms < SLA_MS, f"List students took {ms:.1f}ms (SLA={SLA_MS}ms)"

    def test_add_student_sla(self):
        r, ms = _timed_post(
            f"{BASE}/students",
            {"name": "SLA User", "grade": "A", "email": "sla@test.com"},
        )
        sid = r.json().get("id")
        if sid:
            requests.delete(f"{BASE}/students/{sid}", timeout=5)
        assert ms < SLA_MS, f"Add student took {ms:.1f}ms (SLA={SLA_MS}ms)"

    def test_get_student_sla(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "SLA Get", "grade": "B", "email": "sla_get@test.com"},
            timeout=5,
        )
        sid = r.json()["id"]
        _, ms = _timed_get(f"{BASE}/students/{sid}")
        requests.delete(f"{BASE}/students/{sid}", timeout=5)
        assert ms < SLA_MS, f"Get student took {ms:.1f}ms (SLA={SLA_MS}ms)"

    def test_delete_student_sla(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "SLA Del", "grade": "C", "email": "sla_del@test.com"},
            timeout=5,
        )
        sid = r.json()["id"]
        _, ms = _timed_delete(f"{BASE}/students/{sid}")
        assert ms < SLA_MS, f"Delete student took {ms:.1f}ms (SLA={SLA_MS}ms)"
