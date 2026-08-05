import sqlite3

def init_users_table():
    conn = sqlite3.connect("hostel.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        );
    """)

    conn.commit()
    conn.close()
    print("✅ 'users' table initialized successfully.")

if __name__ == "__main__":
    init_users_table()