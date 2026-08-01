import sqlite3

def allocate_with_preference(student_name, roll_number, year, preferred_floor):
    """
    Allocates a student based on floor preference:
    1. Tries to find an open room on the preferred_floor first.
    2. Fallback: If preferred floor is full, assigns to any other room with free beds.
    """
    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("BEGIN TRANSACTION;")

        # Priority 1: Match preferred floor first
        cursor.execute("""
            SELECT id, room_number, floor, capacity, occupied_beds 
            FROM rooms 
            WHERE occupied_beds < capacity AND floor = ?
            ORDER BY room_number ASC 
            LIMIT 1;
        """, (preferred_floor,))
        
        target_room = cursor.fetchone()

        # Priority 2: Fallback to any available floor if preferred floor is full
        if not target_room:
            print(f"ℹ️ Floor {preferred_floor} full/unavailable for {student_name}. Checking fallback rooms...")
            cursor.execute("""
                SELECT id, room_number, floor, capacity, occupied_beds 
                FROM rooms 
                WHERE occupied_beds < capacity 
                ORDER BY room_number ASC 
                LIMIT 1;
            """)
            target_room = cursor.fetchone()

        if not target_room:
            print(f"❌ Allocation Failed: No beds available in the entire hostel for {student_name}.")
            conn.rollback()
            return False

        room_id, room_number, floor, capacity, occupied_beds = target_room

        # Insert student record with preference stored
        cursor.execute("""
            INSERT INTO students (name, roll_number, year, room_id, preferred_floor)
            VALUES (?, ?, ?, ?, ?);
        """, (student_name, roll_number, year, room_id, preferred_floor))

        # Update room occupancy
        cursor.execute("""
            UPDATE rooms 
            SET occupied_beds = occupied_beds + 1 
            WHERE id = ?;
        """, (room_id,))

        conn.commit()
        print(f"✅ Success: Allocated {student_name} to Room {room_number} (Floor {floor})!")
        return True

    except sqlite3.IntegrityError:
        conn.rollback()
        print(f"⚠️ Error: Roll number '{roll_number}' already registered.")
        return False
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Error during allocation: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("--- Running Day 3 Preference Allocation Test ---")
    
    # Student requests Floor 2 specifically
    allocate_with_preference("Kavya Reddy", "22CSE450", 2, preferred_floor=2)
    # Student requests Floor 1
    allocate_with_preference("Meera Nair", "22CSE115", 2, preferred_floor=1)