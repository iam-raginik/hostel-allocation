from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from preference_allocation import allocate_with_preference

app = FastAPI(
    title="Hostel Allocation System API",
    description="REST API for managing room allocations, student preferences, and inventory.",
    version="1.0.0"
)

# --- Data Validation Schema (Pydantic) ---
class StudentAllocationRequest(BaseModel):
    name: str
    roll_number: str
    year: int
    preferred_floor: int = 1


# --- Helper Function ---
def get_db_connection():
    conn = sqlite3.connect("hostel.db")
    conn.row_factory = sqlite3.Row  # Returns query results as dictionary-like objects
    return conn


# --- API Endpoints ---

@app.get("/")
def home():
    """Health check endpoint to verify API server is online."""
    return {"status": "online", "message": "Hostel Allocation API is running!"}


@app.get("/rooms")
def list_rooms():
    """Retrieve all rooms and their current occupancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, room_number, floor, capacity, occupied_beds FROM rooms ORDER BY room_number ASC;")
    rooms = cursor.fetchall()
    conn.close()
    
    # Convert database rows into a JSON list
    return {"rooms": [dict(room) for room in rooms]}


@app.post("/allocate")
def allocate_room(student: StudentAllocationRequest):
    """API endpoint to register and allocate a student to a room."""
    success = allocate_with_preference(
        student_name=student.name,
        roll_number=student.roll_number,
        year=student.year,
        preferred_floor=student.preferred_floor
    )

    if not success:
        raise HTTPException(
            status_code=400, 
            detail="Allocation failed. Check if roll number exists or if hostel capacity is full."
        )

    return {
        "status": "success",
        "message": f"Successfully processed allocation for {student.name} ({student.roll_number})."
    }