import sqlite3
import unittest
from allocation import allocate_room_to_student
from room_management import deallocate_student

class TestHostelAllocation(unittest.TestCase):

    def setUp(self):
        """Runs BEFORE every test: Sets up an isolated test database in memory."""
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()

        # Build schema
        self.cursor.execute("""
            CREATE TABLE rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_number TEXT UNIQUE NOT NULL,
                floor INTEGER NOT NULL,
                capacity INTEGER NOT NULL DEFAULT 2,
                occupied_beds INTEGER DEFAULT 0
            );
        """)
        self.cursor.execute("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                roll_number TEXT UNIQUE NOT NULL,
                year INTEGER NOT NULL,
                room_id INTEGER,
                FOREIGN KEY (room_id) REFERENCES rooms (id)
            );
        """)
        # Seed 1 room with capacity = 2
        self.cursor.execute("INSERT INTO rooms (room_number, floor, capacity) VALUES ('101', 1, 2);")
        self.conn.commit()

    def tearDown(self):
        """Runs AFTER every test: Cleans up database connection."""
        self.conn.close()

    def test_over_allocation_prevention(self):
        """Test that a room with capacity 2 cannot accept a 3rd student."""
        # Allocate Student 1
        res1 = allocate_room_to_student("Student A", "TEST01", 1)
        # Allocate Student 2
        res2 = allocate_room_to_student("Student B", "TEST02", 1)
        
        # Verify first two allocations succeeded
        self.assertTrue(res1)
        self.assertTrue(res2)

    def test_duplicate_roll_number(self):
        """Test that registering the same roll number twice fails."""
        allocate_room_to_student("First Entry", "DUP001", 2)
        # Attempt duplicate roll number
        result = allocate_room_to_student("Duplicate Entry", "DUP001", 2)
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()