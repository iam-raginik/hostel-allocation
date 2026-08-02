from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List
import sqlite3
from preference_allocation import allocate_with_preference

app = FastAPI(
    title="Hostel Allocation System API",
    description="REST API with structured response schemas and custom error handling.",
    version="1.1.0"
)


# --- 1. Request Schemas ---
class StudentAllocationRequest(BaseModel):
    name: str = Field(..., example="Divya Rao")
    roll_number: str = Field(..., example="22CSE50")
    year: int = Field(..., ge=1, le=4, example=2)  # Validates year between 1 and 4
    preferred_floor: int = Field(default=1, ge=1, example=2)


# --- 2. Response Schemas ---
class RoomSchema(BaseModel):
    id: int
    room_number: str
    floor: int
    capacity: int
    occupied_beds: int


class RoomListResponse(BaseModel):
    status: str = "success"
    total_rooms: int
    rooms: List[RoomSchema]


class AllocationSuccessResponse(BaseModel):
    status: str = "success"
    message: str
    student_name: str
    roll_number: str


# --- 3. Custom Exceptions & Handlers ---
class AllocationError(Exception):
    def __init__(self, message: str):
        self.message = message


@app.exception_handler(AllocationError)
async def allocation_error_handler(request: Request, exc: AllocationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "error_type": "AllocationFailed",
            "detail": exc.message
        }
    )


# --- Helper Function ---
def get_db_connection():
    conn = sqlite3.connect("hostel.db")
    conn.row_factory = sqlite3.Row
    return conn


# --- 4. API Endpoints ---

@app.get("/")
def home():
    return {"status": "online", "message": "Hostel Allocation API v1.1 is running!"}


@app.get("/rooms", response_model=RoomListResponse)
def list_rooms():
    """Retrieve all rooms with validated schema output."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, room_number, floor, capacity, occupied_beds FROM rooms ORDER BY room_number ASC;")
    rooms = cursor.fetchall()
    conn.close()

    room_list = [dict(room) for room in rooms]
    return {
        "status": "success",
        "total_rooms": len(room_list),
        "rooms": room_list
    }


@app.post("/allocate", response_model=AllocationSuccessResponse)
def allocate_room(student: StudentAllocationRequest):
    """API endpoint to process student room allocation."""
    success = allocate_with_preference(
        student_name=student.name,
        roll_number=student.roll_number,
        year=student.year,
        preferred_floor=student.preferred_floor
    )

    if not success:
        raise AllocationError(
            f"Could not allocate room for roll number '{student.roll_number}'. "
            "Hostel might be full or the roll number is already registered."
        )

    return AllocationSuccessResponse(
        status="success",
        message=f"Successfully allocated room for {student.name}.",
        student_name=student.name,
        roll_number=student.roll_number
    )