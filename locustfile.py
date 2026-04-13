"""
Stage 10 – Performance Tests
Locust headless load test: 10 users, 30 seconds.
Run via Jenkins:  locust -f locustfile.py --headless -u 10 -r 2 -t 30s \
                         --host http://localhost:5000 \
                         --csv=reports/locust
"""

import random
from locust import HttpUser, task, between


class StudentAPIUser(HttpUser):
    wait_time = between(0.5, 1.5)
    _created_ids: list = []

    def on_start(self):
        """Seed a student on user start."""
        r = self.client.post(
            "/students",
            json={
                "name": f"Perf User {random.randint(1, 9999)}",
                "grade": random.choice(["A", "B", "C", "D"]),
                "email": f"perf{random.randint(1, 99999)}@load.test",
            },
            name="/students [POST seed]",
        )
        if r.status_code == 201:
            self._created_ids.append(r.json()["id"])

    @task(3)
    def list_students(self):
        self.client.get("/students", name="/students [GET list]")

    @task(3)
    def health_check(self):
        self.client.get("/health", name="/health [GET]")

    @task(2)
    def add_student(self):
        r = self.client.post(
            "/students",
            json={
                "name": f"Load User {random.randint(1, 9999)}",
                "grade": random.choice(["A", "B", "C"]),
                "email": f"load{random.randint(1, 999999)}@perf.test",
            },
            name="/students [POST]",
        )
        if r.status_code == 201:
            self._created_ids.append(r.json()["id"])

    @task(2)
    def get_student(self):
        if self._created_ids:
            sid = random.choice(self._created_ids)
            self.client.get(f"/students/{sid}", name="/students/<id> [GET]")

    @task(1)
    def delete_student(self):
        if self._created_ids:
            sid = self._created_ids.pop(0)
            self.client.delete(f"/students/{sid}", name="/students/<id> [DELETE]")
