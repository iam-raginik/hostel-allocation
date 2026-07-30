import sqlite3

def setup_database():
    # Connects to (or creates) hostel.db in your project folder
    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    # Enable foreign key constraints in SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Create Rooms Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rooms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        room_number TEXT UNIQUE NOT NULL,
        floor INTEGER NOT NULL,
        capacity INTEGER NOT NULL DEFAULT 2,
        occupied_beds INTEGER DEFAULT 0
    );
    """)

    # 2. Create Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        roll_number TEXT UNIQUE NOT NULL,
        year INTEGER NOT NULL,
        room_id INTEGER,
        FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE SET NULL
    );
    """)

    # 3. Seed sample hostel rooms (1st & 2nd floor rooms with capacity 2)
    sample_rooms = [
        ("101", 1, 2),
        ("102", 1, 2),
        ("103", 1, 2),
        ("201", 2, 2),
        ("202", 2, 2),
    ]

    cursor.executemany("""
    INSERT OR IGNORE INTO rooms (room_number, floor, capacity) 
    VALUES (?, ?, ?)
    """, sample_rooms)

    conn.commit()
    conn.close()
    print("✅ Database initialized! Created 'rooms' and 'students' tables.")

if __name__ == "__main__":
    setup_database()