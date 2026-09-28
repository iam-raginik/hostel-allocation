import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

import database
from main import app
from database import get_db, init_db, seed_rooms

TEST_DB_NAME = "test_hostel.db"


def override_get_db():
    """Dependency override providing an isolated test database connection."""
    conn = sqlite3.connect(TEST_DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_database():
    """
    Automated fixture ensuring each test function runs against
    a fresh, isolated test database with initialized schema and seed data.
    """
    database.DB_NAME = TEST_DB_NAME
    if os.path.exists(TEST_DB_NAME):
        try:
            os.remove(TEST_DB_NAME)
        except PermissionError:
            pass

    init_db()
    seed_rooms()
    yield
    if os.path.exists(TEST_DB_NAME):
        try:
            os.remove(TEST_DB_NAME)
        except PermissionError:
            pass


# --- Helper Function ---

def get_auth_headers(username: str = "testuser", password: str = "password123") -> dict:
    """Helper function to register, login, and obtain valid JWT Authorization headers."""
    client.post("/register", json={"username": username, "password": password})
    response = client.post(
        "/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# --- 1. Authentication Tests ---

def test_register_user_success():
    """Verify user registration returns HTTP 201 Created and user details."""
    payload = {"username": "qa_admin", "password": "securepass"}
    response = client.post("/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "qa_admin"
    assert "id" in data


def test_register_duplicate_username():
    """Verify registering an existing username returns HTTP 400 Bad Request."""
    payload = {"username": "qa_admin", "password": "securepass"}
    client.post("/register", json=payload)

    response = client.post("/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success():
    """Verify valid credentials return an HTTP 200 response with JWT access token."""
    client.post("/register", json={"username": "loginuser", "password": "securepass"})
    response = client.post(
        "/login",
        data={"username": "loginuser", "password": "securepass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    """Verify invalid credentials return HTTP 401 Unauthorized."""
    client.post("/register", json={"username": "loginuser", "password": "securepass"})
    response = client.post(
        "/login",
        data={"username": "loginuser", "password": "wrongpassword"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_register_and_login():
    """Integrated test for user registration followed by immediate login."""
    reg_resp = client.post("/register", json={"username": "qa_admin2", "password": "securepass"})
    assert reg_resp.status_code == 201

    login_resp = client.post(
        "/login",
        data={"username": "qa_admin2", "password": "securepass"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


# --- 2. Authorization Tests ---

def test_unauthorized_allocation():
    """Verify accessing /allocate without a Bearer token returns HTTP 401 Unauthorized."""
    payload = {
        "name": "Unauthorized Student",
        "roll_number": "99NOAUTH",
        "year": 1,
        "preferred_floor": 1
    }
    response = client.post("/allocate", json=payload)
    assert response.status_code == 401


def test_unauthorized_access():
    """Verify protected route access fails without authorization headers."""
    response = client.post("/allocate", json={
        "name": "Unauthorized Student",
        "roll_number": "99NOAUTH",
        "year": 1,
        "preferred_floor": 1
    })
    assert response.status_code == 401


# --- 3. Room Allocation Tests ---

def test_allocate_single_student_success():
    """Verify single student room allocation returns success status code and allocation details."""
    headers = get_auth_headers()
    payload = {
        "name": "John Doe",
        "roll_number": "ROLL001",
        "year": 1,
        "preferred_floor": 1
    }
    response = client.post("/allocate", json=payload, headers=headers)
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["status"] == "success"
    assert data["roll_number"] == "ROLL001"
    assert "room_number" in data


def test_allocate_duplicate_roll_number():
    """Verify attempting to allocate the same roll number twice returns HTTP 400 Bad Request."""
    headers = get_auth_headers()
    payload = {
        "name": "John Doe",
        "roll_number": "ROLL001",
        "year": 1,
        "preferred_floor": 1
    }
    first_resp = client.post("/allocate", json=payload, headers=headers)
    assert first_resp.status_code in [200, 201]

    second_resp = client.post("/allocate", json=payload, headers=headers)
    assert second_resp.status_code == 400
    assert "already registered/allocated" in second_resp.json()["detail"]


def test_allocate_batch_success():
    """Verify batch allocation processes all students and returns valid count summary."""
    headers = get_auth_headers()
    payload = [
        {"name": "Student A", "roll_number": "BATCH001", "year": 1, "preferred_floor": 1},
        {"name": "Student B", "roll_number": "BATCH002", "year": 1, "preferred_floor": 2}
    ]
    response = client.post("/allocate/batch", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert data["successful"] == 2
    assert data["failed"] == 0
    assert len(data["results"]) == 2


def test_allocate_batch_empty_list():
    """Verify sending an empty array [] to /allocate/batch returns HTTP 400 Bad Request."""
    headers = get_auth_headers()
    response = client.post("/allocate/batch", json=[], headers=headers)
    assert response.status_code == 400


def test_batch_allocation_flow():
    """Integrated test for batch room allocation flow."""
    headers = get_auth_headers()
    payload = [
        {"name": "Student A", "roll_number": "TEST001", "year": 1, "preferred_floor": 1},
        {"name": "Student B", "roll_number": "TEST002", "year": 1, "preferred_floor": 2}
    ]
    response = client.post("/allocate/batch", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_processed"] == 2
    assert data["successful"] == 2


# --- 4. Middleware & Logging Tests ---

def test_request_timing_middleware_header():
    """Verify that HTTP responses include the X-Process-Time-Ms custom header."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Process-Time-Ms" in response.headers
    assert float(response.headers["X-Process-Time-Ms"]) >= 0.0

