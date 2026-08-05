from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List
import sqlite3
from preference_allocation import allocate_with_preference
from auth import hash_password, verify_password, create_access_token, get_current_user

app = FastAPI(
    title="Hostel Allocation System API",
    description="REST API with structured response schemas, custom errors, and JWT Authentication.",
    version="1.2.0"
)

# --- Request / Response Schemas ---
class StudentAllocationRequest(BaseModel):
    name: str = Field(..., example="Divya Rao")
    roll_number: str = Field(..., example="22CSE50")
    year: int = Field(..., ge=1, le=4, example=2)
    preferred_floor: int = Field(default=1, ge=1, example=2)


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


class UserRegisterRequest(BaseModel):
    username: str = Field(..., example="warden_smith")
    password: str = Field(..., example="securepassword123")
    role: str = Field(default="warden", example="warden")


class RegisterSuccessResponse(BaseModel):
    status: str = "success"
    message: str


class UserLoginRequest(BaseModel):
    username: str = Field(..., example="warden_smith")
    password: str = Field(..., example="securepassword123")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Custom Exceptions & Handlers ---
class AllocationError(Exception):
    def __init__(self, message: str):
        self.message = message


@app.exception_handler(AllocationError)
async def allocation_error_handler(request: Request, exc: AllocationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"status": "error", "error_type": "AllocationFailed", "detail": exc.message}
    )


def get_db_connection():
    conn = sqlite3.connect("hostel.db")
    conn.row_factory = sqlite3.Row
    return conn


# --- Endpoints ---

@app.get("/")
def home():
    return {"status": "online", "message": "Hostel Allocation API v1.2 is running!"}





@app.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(user: UserRegisterRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        hashed_pwd = hash_password(user.password)
        cursor.execute(
            "INSERT INTO users (username, hashed_password, role) VALUES (?, ?, ?);",
            (user.username, hashed_pwd, user.role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Username already exists."
        )
    except Exception as e:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Database error: {str(e)}"
        )

    conn.close()
    return {"status": "success", "message": f"User '{user.username}' created successfully."}


@app.post("/login", response_model=TokenResponse)
def login_user(user: UserLoginRequest):
    """Authenticates user credentials and returns a JWT token."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?;", (user.username,))
    db_user = cursor.fetchone()
    conn.close()

    if not db_user or not verify_password(user.password, db_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )

    # Generate JWT token with username and role in payload
    access_token = create_access_token(data={"sub": db_user["username"], "role": db_user["role"]})
    return TokenResponse(access_token=access_token)


@app.get("/rooms", response_model=RoomListResponse)
def list_rooms():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, room_number, floor, capacity, occupied_beds FROM rooms ORDER BY room_number ASC;")
    rooms = cursor.fetchall()
    conn.close()

    room_list = [dict(room) for room in rooms]
    return {"status": "success", "total_rooms": len(room_list), "rooms": room_list}


@app.post("/allocate", response_model=AllocationSuccessResponse)
def allocate_room(
    student: StudentAllocationRequest,
    current_user: dict = Depends(get_current_user)  # 👈 Protected with JWT!
):
    success = allocate_with_preference(
        student_name=student.name,
        roll_number=student.roll_number,
        year=student.year,
        preferred_floor=student.preferred_floor
    )

    if not success:
        raise AllocationError(
            f"Could not allocate room for roll number '{student.roll_number}'. Hostel might be full or duplicate roll number."
        )

    return AllocationSuccessResponse(
        status="success",
        message=f"Successfully allocated room for {student.name} (action authorized by {current_user['username']}).",
        student_name=student.name,
        roll_number=student.roll_number
    )