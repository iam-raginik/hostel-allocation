import os
import sqlite3
from typing import Generator
from passlib.context import CryptContext
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./hostel.db")
DB_NAME = DATABASE_URL.replace("sqlite:///", "") if DATABASE_URL.startswith("sqlite:///") else DATABASE_URL

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db_connection() -> sqlite3.Connection:
    """
    Creates and returns a SQLite database connection with row factory
    enabled for column name access and foreign keys enabled.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency that yields a database connection and ensures
    it is closed after request processing.
    """
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """
    Automated initialization of database tables on startup.
    Creates 'users', 'rooms', and 'students' tables if they do not exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL
    );
    """)

    # 2. Rooms Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        room_number TEXT PRIMARY KEY,
        floor INTEGER NOT NULL,
        capacity INTEGER NOT NULL DEFAULT 2,
        occupied_beds INTEGER NOT NULL DEFAULT 0
    );
    """)

    # 3. Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        year INTEGER NOT NULL,
        room_number TEXT NOT NULL,
        preferred_floor INTEGER NOT NULL,
        FOREIGN KEY (room_number) REFERENCES rooms (room_number) ON DELETE SET NULL
    );
    """)

    conn.commit()
    conn.close()


def seed_rooms() -> None:
    """
    Auto-populates the rooms table with sample rooms across floors 1 to 3
    if the table is empty. Also ensures a default admin user exists.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS count FROM rooms;")
    count = cursor.fetchone()["count"]

    if count == 0:
        sample_rooms = [
            # Floor 1
            ("101", 1, 2, 0),
            ("102", 1, 2, 0),
            ("103", 1, 2, 0),
            # Floor 2
            ("201", 2, 2, 0),
            ("202", 2, 2, 0),
            ("203", 2, 2, 0),
            # Floor 3
            ("301", 3, 2, 0),
            ("302", 3, 2, 0),
            ("303", 3, 2, 0),
        ]

        cursor.executemany("""
        INSERT INTO rooms (room_number, floor, capacity, occupied_beds)
        VALUES (?, ?, ?, ?);
        """, sample_rooms)

        conn.commit()
        print("[SEED] Database seeded with sample rooms across floors 1 to 3.")

    # Seed default user if users table is empty
    cursor.execute("SELECT COUNT(*) AS count FROM users;")
    user_count = cursor.fetchone()["count"]
    if user_count == 0:
        default_user = "admin_warden"
        default_pass = pwd_context.hash("securepassword123")
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?);",
            (default_user, default_pass)
        )
        conn.commit()
        print("[SEED] Created default user 'admin_warden'.")

    conn.close()


if __name__ == "__main__":
    init_db()
    seed_rooms()
    print("[OK] Database initialization and seeding completed.")
