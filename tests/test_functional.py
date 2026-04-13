"""
Stage 7 – Functional Tests
Full CRUD integration tests across all student endpoints.
"""

import os
import pytest
import requests

BASE = os.environ.get("API_BASE_URL", "http://localhost:5000")


@pytest.fixture(scope="module")
def created_student():
    """Create a student once and reuse across tests in this module."""
    payload = {"name": "Alice Smith", "grade": "B+", "email": "alice@uni.ac.uk"}
    r = requests.post(f"{BASE}/students", json=payload, timeout=5)
    assert r.status_code == 201
    yield r.json()


class TestAddStudent:
    def test_add_returns_201(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "Bob Jones", "grade": "A", "email": "bob@uni.ac.uk"},
            timeout=5,
        )
        assert r.status_code == 201

    def test_add_response_has_id(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "Carol White", "grade": "C", "email": "carol@uni.ac.uk"},
            timeout=5,
        )
        assert "id" in r.json()

    def test_add_missing_name_returns_400(self):
        r = requests.post(
            f"{BASE}/students",
            json={"grade": "A", "email": "nobody@uni.ac.uk"},
            timeout=5,
        )
        assert r.status_code == 400

    def test_add_missing_grade_returns_400(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "Nobody", "email": "nobody@uni.ac.uk"},
            timeout=5,
        )
        assert r.status_code == 400

    def test_add_missing_email_returns_400(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "Nobody", "grade": "A"},
            timeout=5,
        )
        assert r.status_code == 400

    def test_add_empty_body_returns_400(self):
        r = requests.post(f"{BASE}/students", json={}, timeout=5)
        assert r.status_code == 400


class TestListStudents:
    def test_list_returns_200(self):
        r = requests.get(f"{BASE}/students", timeout=5)
        assert r.status_code == 200

    def test_list_has_students_key(self):
        r = requests.get(f"{BASE}/students", timeout=5)
        assert "students" in r.json()

    def test_list_has_count_key(self):
        r = requests.get(f"{BASE}/students", timeout=5)
        assert "count" in r.json()

    def test_list_count_matches_students_length(self):
        body = requests.get(f"{BASE}/students", timeout=5).json()
        assert body["count"] == len(body["students"])


class TestGetStudent:
    def test_get_existing_student(self, created_student):
        sid = created_student["id"]
        r = requests.get(f"{BASE}/students/{sid}", timeout=5)
        assert r.status_code == 200
        assert r.json()["id"] == sid

    def test_get_returns_correct_name(self, created_student):
        sid = created_student["id"]
        r = requests.get(f"{BASE}/students/{sid}", timeout=5)
        assert r.json()["name"] == created_student["name"]

    def test_get_nonexistent_returns_404(self):
        r = requests.get(f"{BASE}/students/999999", timeout=5)
        assert r.status_code == 404


class TestDeleteStudent:
    def test_delete_returns_200(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "ToDelete", "grade": "D", "email": "del@uni.ac.uk"},
            timeout=5,
        )
        sid = r.json()["id"]
        rd = requests.delete(f"{BASE}/students/{sid}", timeout=5)
        assert rd.status_code == 200

    def test_delete_removes_from_list(self):
        r = requests.post(
            f"{BASE}/students",
            json={"name": "AlsoDelete", "grade": "D", "email": "del2@uni.ac.uk"},
            timeout=5,
        )
        sid = r.json()["id"]
        requests.delete(f"{BASE}/students/{sid}", timeout=5)
        r2 = requests.get(f"{BASE}/students/{sid}", timeout=5)
        assert r2.status_code == 404

    def test_delete_nonexistent_returns_404(self):
        r = requests.delete(f"{BASE}/students/999999", timeout=5)
        assert r.status_code == 404
