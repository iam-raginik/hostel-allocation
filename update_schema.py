import sqlite3

def add_preference_column():
    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    try:
        # Add preferred_floor column to students table
        cursor.execute("ALTER TABLE students ADD COLUMN preferred_floor INTEGER DEFAULT 1;")
        conn.commit()
        print("✅ Database updated: Added 'preferred_floor' column to students table.")
    except sqlite3.OperationalError:
        # Column already exists
        print("ℹ️ Column 'preferred_floor' already exists.")
    finally:
        conn.close()

if __name__ == "__main__":
    add_preference_column()