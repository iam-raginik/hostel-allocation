import sqlite3

conn = sqlite3.connect("hostel.db")
cursor = conn.cursor()

# Clear all students and reset room occupancy
cursor.execute("DELETE FROM students;")
cursor.execute("UPDATE rooms SET occupied_beds = 0;")

conn.commit()
conn.close()
print("✅ Database reset successfully! All rooms are empty.")