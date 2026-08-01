import sqlite3

def deallocate_student(roll_number):
    """
    Vacates a student from their allocated room and decrements occupied_beds.
    """
    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("BEGIN TRANSACTION;")

        # Find student and their currently assigned room
        cursor.execute("""
            SELECT id, name, room_id FROM students WHERE roll_number = ?;
        """, (roll_number,))
        student = cursor.fetchone()

        if not student:
            print(f"⚠️ Student with roll number {roll_number} not found.")
            conn.rollback()
            return False

        student_id, student_name, room_id = student

        if not room_id:
            print(f"ℹ️ {student_name} is not currently allocated to any room.")
            conn.rollback()
            return False

        # 1. Unlink room from student
        cursor.execute("""
            UPDATE students SET room_id = NULL WHERE id = ?;
        """, (student_id,))

        # 2. Decrement occupied_beds count in rooms table
        cursor.execute("""
            UPDATE rooms SET occupied_beds = occupied_beds - 1 WHERE id = ?;
        """, (room_id,))

        conn.commit()
        print(f"✅ Success: Vacated {student_name} ({roll_number}) from Room ID {room_id}.")
        return True

    except Exception as e:
        conn.rollback()
        print(f"⚠️ Error during checkout: {e}")
        return False
    finally:
        conn.close()


def swap_rooms(roll_number_1, roll_number_2):
    """
    Swaps assigned rooms between two allocated students in a single transaction.
    """
    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("BEGIN TRANSACTION;")

        # Get room details for student 1
        cursor.execute("SELECT id, name, room_id FROM students WHERE roll_number = ?;", (roll_number_1,))
        student_1 = cursor.fetchone()

        # Get room details for student 2
        cursor.execute("SELECT id, name, room_id FROM students WHERE roll_number = ?;", (roll_number_2,))
        student_2 = cursor.fetchone()

        if not student_1 or not student_2:
            print("⚠️ Swap Failed: One or both students do not exist.")
            conn.rollback()
            return False

        s1_id, s1_name, s1_room = student_1
        s2_id, s2_name, s2_room = student_2

        if not s1_room or not s2_room:
            print("⚠️ Swap Failed: Both students must be allocated to a room before swapping.")
            conn.rollback()
            return False

        # Perform atomic room exchange
        cursor.execute("UPDATE students SET room_id = ? WHERE id = ?;", (s2_room, s1_id))
        cursor.execute("UPDATE students SET room_id = ? WHERE id = ?;", (s1_room, s2_id))

        conn.commit()
        print(f"🔄 Success: Swapped rooms between {s1_name} and {s2_name}!")
        return True

    except Exception as e:
        conn.rollback()
        print(f"⚠️ Error during room swap: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("--- Running Day 4 Management Functions Test ---")
    
    # Test swapping rooms between two students allocated in previous days
    swap_rooms("22CSE450", "25BBTCS166")
    
    # Test vacating a room
    deallocate_student("22CSE450")