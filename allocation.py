import sqlite3

def allocate_room_to_student(student_name, roll_number, year):
    """
    Finds the first available room with free beds, assigns the student,
    and updates the room's occupied_beds count safely.
    """
    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    try:
        # Enable Foreign Key constraints
        cursor.execute("PRAGMA foreign_keys = ON;")

        # Begin Database Transaction
        cursor.execute("BEGIN TRANSACTION;")

        # 1. Query for the first room where occupied_beds < capacity
        cursor.execute("""
            SELECT id, room_number, capacity, occupied_beds 
            FROM rooms 
            WHERE occupied_beds < capacity 
            ORDER BY room_number ASC 
            LIMIT 1;
        """)
        available_room = cursor.fetchone()

        # Check if any room is available
        if not available_room:
            print(f"❌ Allocation Failed: No available rooms for {student_name} ({roll_number}).")
            conn.rollback()
            return False

        room_id, room_number, capacity, occupied_beds = available_room

        # 2. Add student record assigned to room_id
        cursor.execute("""
            INSERT INTO students (name, roll_number, year, room_id)
            VALUES (?, ?, ?, ?);
        """, (student_name, roll_number, year, room_id))

        # 3. Increment the occupied_beds count in the rooms table
        cursor.execute("""
            UPDATE rooms 
            SET occupied_beds = occupied_beds + 1 
            WHERE id = ?;
        """, (room_id,))

        # Commit all changes as one atomic operation
        conn.commit()
        print(f"✅ Success: Allocated {student_name} ({roll_number}) to Room {room_number}!")
        return True

    except sqlite3.IntegrityError as e:
        # Triggers if duplicate roll number is inserted
        conn.rollback()
        print(f"⚠️ Error allocating {student_name}: Roll number '{roll_number}' already exists.")
        return False
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Unexpected error during allocation: {e}")
        return False
    finally:
        conn.close()

# --- Simple Test Execution ---
if __name__ == "__main__":
    print("--- Running Day 2 Allocation Test ---")
    
    # Test assigning students to available rooms
    allocate_room_to_student("Sita", "25BBTCS166", 2)
    allocate_room_to_student("Priya", "25BBTCS1209", 2)
    allocate_room_to_student("Ananya", "25BBTCS140", 2)