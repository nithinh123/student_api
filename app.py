"""
Student Management System - Flask API
Endpoints: POST /students, GET /students, GET /students/<id>, DELETE /students/<id>
"""

import time
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory store  {id: {id, name, grade, email}}
_students: dict = {}
_next_id: int = 1


def _new_id() -> int:
    global _next_id
    sid = _next_id
    _next_id += 1
    return sid


# ── Health ────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "timestamp": time.time()}), 200


# ── Students ──────────────────────────────────────────────────────────────────

@app.route("/students", methods=["GET"])
def list_students():
    return jsonify({"students": list(_students.values()), "count": len(_students)}), 200


@app.route("/students/<int:student_id>", methods=["GET"])
def get_student(student_id: int):
    student = _students.get(student_id)
    if not student:
        return jsonify({"error": f"Student {student_id} not found"}), 404
    return jsonify(student), 200


@app.route("/students", methods=["POST"])
def add_student():
    data = request.get_json(silent=True) or {}
    name  = (data.get("name") or "").strip()
    grade = (data.get("grade") or "").strip()
    email = (data.get("email") or "").strip()

    if not name or not grade or not email:
        return jsonify({"error": "name, grade and email are required"}), 400

    sid = _new_id()
    student = {"id": sid, "name": name, "grade": grade, "email": email}
    _students[sid] = student
    return jsonify(student), 201


@app.route("/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id: int):
    if student_id not in _students:
        return jsonify({"error": f"Student {student_id} not found"}), 404
    del _students[student_id]
    return jsonify({"message": f"Student {student_id} deleted"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
