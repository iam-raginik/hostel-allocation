from contextlib import asynccontextmanager
from typing import List, Optional
import sqlite3
import time

from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse

from database import get_db, init_db, seed_rooms
from schemas import (
    UserRegisterRequest,
    UserResponse,
    Token,
    StudentAllocationRequest,
    AllocationSuccessResponse,
    SingleAllocationResult,
    BatchAllocationResponse,
    RoomListResponse,
    RoomResponse,
)
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle application startup and shutdown events.
    Automatically initializes tables and populates seed rooms on startup.
    """
    # Startup execution
    init_db()
    seed_rooms()
    yield
    # Shutdown logic (if required)


app = FastAPI(
    title="Hostel Room Allocation System API",
    description="Production-ready RESTful API for managing hostel room allocations with JWT Auth.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Day 13: Request Timing & Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    HTTP Middleware to track execution duration, log details of incoming requests,
    and attach 'X-Process-Time-Ms' header to the HTTP response.
    """
    start_time = time.perf_counter()

    response = await call_next(request)

    process_time = (time.perf_counter() - start_time) * 1000  # Convert to milliseconds
    client_ip = request.client.host if request.client else "Unknown"

    logger.info(
        f"METHOD={request.method} PATH={request.url.path} STATUS={response.status_code} "
        f"TIME={process_time:.2f}ms IP={client_ip}"
    )

    # Attach execution time header to the HTTP response
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    return response


# --- Core Endpoints ---

@app.get("/", summary="System Health Check")
def health_check():
    """Returns the operational status of the Hostel Allocation API."""
    return {
        "status": "online",
        "service": "Hostel Room Allocation System API",
        "version": "2.0.0",
    }


# --------------------------------------------------------------------------
# 1. Authentication System
# --------------------------------------------------------------------------

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register_user(
    payload: UserRegisterRequest,
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Registers a new user (e.g. warden/admin) with a bcrypt hashed password.
    Returns HTTP 400 Bad Request if the username is already taken.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?;", (payload.username,))
    if cursor.fetchone() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{payload.username}' is already registered.",
        )

    hashed_pwd = hash_password(payload.password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?);",
            (payload.username, hashed_pwd),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{payload.username}' is already registered.",
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during registration: {str(e)}",
        )

    return UserResponse(id=user_id, username=payload.username)


@app.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and obtain JWT token",
)
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Authenticates user credentials using OAuth2PasswordRequestForm and
    returns a signed JWT Bearer Access Token.
    Logs audit events for failed warnings and successful logins.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (form_data.username,))
    db_user = cursor.fetchone()

    if not db_user or not verify_password(form_data.password, db_user["password_hash"]):
        logger.warning(f"AUDIT | Failed login attempt for username: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"AUDIT | Successful login for user: {db_user['username']}")
    access_token = create_access_token(data={"sub": db_user["username"]})
    return Token(access_token=access_token, token_type="bearer")


# --------------------------------------------------------------------------
# 2. Single Room Allocation (Protected by JWT)
# --------------------------------------------------------------------------

@app.post(
    "/allocate",
    response_model=AllocationSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Allocate room for a single student",
)
def allocate_single_student(
    student: StudentAllocationRequest,
    current_user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Allocates a room to a single student based on floor preference with fallback:
    1. Checks if student roll number already exists (returns HTTP 400).
    2. Searches for an available room on preferred_floor (where occupied_beds < capacity).
    3. Fallback: Searches for any available room on any floor.
    4. Returns HTTP 404 Not Found if no beds are available in the hostel.
    5. Saves student record and increments occupied_beds in rooms table.
    """
    cursor = conn.cursor()

    # Step 1: Check for duplicate roll number
    cursor.execute("SELECT id FROM students WHERE roll_number = ?;", (student.roll_number,))
    if cursor.fetchone() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with roll number '{student.roll_number}' is already registered/allocated.",
        )

    try:
        conn.execute("BEGIN TRANSACTION;")

        # Step 2: Search on preferred floor
        cursor.execute(
            """
            SELECT room_number, floor, capacity, occupied_beds 
            FROM rooms 
            WHERE occupied_beds < capacity AND floor = ? 
            ORDER BY room_number ASC 
            LIMIT 1;
            """,
            (student.preferred_floor,),
        )
        target_room = cursor.fetchone()

        # Step 3: Fallback to any available room across floors
        if not target_room:
            cursor.execute(
                """
                SELECT room_number, floor, capacity, occupied_beds 
                FROM rooms 
                WHERE occupied_beds < capacity 
                ORDER BY floor ASC, room_number ASC 
                LIMIT 1;
                """
            )
            target_room = cursor.fetchone()

        # Step 4: If hostel is full
        if not target_room:
            conn.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hostel is full. No available rooms on any floor.",
            )

        room_number = target_room["room_number"]
        room_floor = target_room["floor"]

        # Step 5: Insert student record and update room occupancy
        cursor.execute(
            """
            INSERT INTO students (name, roll_number, year, room_number, preferred_floor)
            VALUES (?, ?, ?, ?, ?);
            """,
            (student.name, student.roll_number, student.year, room_number, student.preferred_floor),
        )

        cursor.execute(
            """
            UPDATE rooms 
            SET occupied_beds = occupied_beds + 1 
            WHERE room_number = ?;
            """,
            (room_number,),
        )

        conn.commit()

        return AllocationSuccessResponse(
            status="success",
            message=f"Successfully allocated student '{student.name}' to Room {room_number} (Floor {room_floor}).",
            student_name=student.name,
            roll_number=student.roll_number,
            room_number=room_number,
            floor=room_floor,
        )

    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during allocation: {str(e)}",
        )


# --------------------------------------------------------------------------
# 3. Batch Room Allocation (Protected by JWT)
# --------------------------------------------------------------------------

@app.post(
    "/allocate/batch",
    response_model=BatchAllocationResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch allocate rooms for multiple students",
)
def allocate_batch_students(
    students_batch: List[StudentAllocationRequest],
    current_user: dict = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db),
):
    """
    Batch allocates rooms for a list of student requests inside database transaction:
    - Iterates through each student request.
    - Allocates room using preferred floor first, then fallback to any open room.
    - Gracefully records individual student failures (e.g. duplicate roll_number or hostel full)
    - Returns a summary response with total processed, successful, failed count, and individual results.
    - Logs audit details for batch allocation start and completion.
    """
    if not students_batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Batch allocation list cannot be empty.",
        )

    executing_user = current_user.get("username", "Unknown") if isinstance(current_user, dict) else str(current_user)
    total_processed = len(students_batch)

    logger.info(
        f"AUDIT | Starting batch allocation execution by user '{executing_user}' for {total_processed} records."
    )

    cursor = conn.cursor()
    successful = 0
    failed = 0
    results: List[SingleAllocationResult] = []

    try:
        conn.execute("BEGIN TRANSACTION;")

        for student in students_batch:
            # Check duplicate roll number
            cursor.execute("SELECT id FROM students WHERE roll_number = ?;", (student.roll_number,))
            if cursor.fetchone() is not None:
                failed += 1
                results.append(
                    SingleAllocationResult(
                        roll_number=student.roll_number,
                        name=student.name,
                        status="failed",
                        room_number=None,
                        message=f"Duplicate roll number '{student.roll_number}' already allocated.",
                    )
                )
                continue

            # Try preferred floor
            cursor.execute(
                """
                SELECT room_number, floor, capacity, occupied_beds 
                FROM rooms 
                WHERE occupied_beds < capacity AND floor = ? 
                ORDER BY room_number ASC 
                LIMIT 1;
                """,
                (student.preferred_floor,),
            )
            target_room = cursor.fetchone()

            # Fallback to any floor
            if not target_room:
                cursor.execute(
                    """
                    SELECT room_number, floor, capacity, occupied_beds 
                    FROM rooms 
                    WHERE occupied_beds < capacity 
                    ORDER BY floor ASC, room_number ASC 
                    LIMIT 1;
                    """
                )
                target_room = cursor.fetchone()

            # No room available
            if not target_room:
                failed += 1
                results.append(
                    SingleAllocationResult(
                        roll_number=student.roll_number,
                        name=student.name,
                        status="failed",
                        room_number=None,
                        message="No available rooms in the hostel.",
                    )
                )
                continue

            # Perform allocation for this student
            room_number = target_room["room_number"]
            room_floor = target_room["floor"]

            cursor.execute(
                """
                INSERT INTO students (name, roll_number, year, room_number, preferred_floor)
                VALUES (?, ?, ?, ?, ?);
                """,
                (student.name, student.roll_number, student.year, room_number, student.preferred_floor),
            )

            cursor.execute(
                """
                UPDATE rooms 
                SET occupied_beds = occupied_beds + 1 
                WHERE room_number = ?;
                """,
                (room_number,),
            )

            successful += 1
            results.append(
                SingleAllocationResult(
                    roll_number=student.roll_number,
                    name=student.name,
                    status="allocated",
                    room_number=room_number,
                    message=f"Successfully allocated to Room {room_number} (Floor {room_floor}).",
                )
            )

        conn.commit()

        logger.info(
            f"AUDIT | Batch allocation completed for user '{executing_user}': {successful} successful, {failed} failed out of {total_processed} records."
        )

        return BatchAllocationResponse(
            total_processed=total_processed,
            successful=successful,
            failed=failed,
            results=results,
        )

    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction error during batch allocation: {str(e)}",
        )


# --------------------------------------------------------------------------
# 4. Room Management Endpoints
# --------------------------------------------------------------------------

@app.get(
    "/rooms",
    response_model=RoomListResponse,
    summary="List all rooms and current occupancy",
)
def list_rooms(conn: sqlite3.Connection = Depends(get_db)):
    """Retrieves all rooms in the hostel with current bed occupancy details."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT room_number, floor, capacity, occupied_beds FROM rooms ORDER BY room_number ASC;"
    )
    rows = cursor.fetchall()
    rooms_list = [RoomResponse(**dict(row)) for row in rows]
    return RoomListResponse(status="success", total_rooms=len(rooms_list), rooms=rooms_list)