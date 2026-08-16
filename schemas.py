from pydantic import BaseModel, Field
from typing import List, Optional


# --- Authentication Schemas ---

class UserRegisterRequest(BaseModel):
    """Payload for registering a new user."""
    username: str = Field(..., example="warden_smith", min_length=3)
    password: str = Field(..., example="securepassword123", min_length=6)


class UserResponse(BaseModel):
    """Response schema for registered user details."""
    id: int
    username: str


class Token(BaseModel):
    """Bearer token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Extracted claims payload from JWT token."""
    username: Optional[str] = None


# --- Room Allocation Schemas ---

class StudentAllocationRequest(BaseModel):
    """Payload for allocating a room to a student."""
    name: str = Field(..., example="Divya Rao")
    roll_number: str = Field(..., example="22CSE50")
    year: int = Field(..., ge=1, le=4, example=2)
    preferred_floor: int = Field(default=1, ge=1, example=2)


class AllocationSuccessResponse(BaseModel):
    """Response schema for single student allocation success."""
    status: str = "success"
    message: str
    student_name: str
    roll_number: str
    room_number: str
    floor: int


class SingleAllocationResult(BaseModel):
    """Individual item result within a batch allocation response."""
    roll_number: str
    name: str
    status: str  # "allocated" or "failed"
    room_number: Optional[str] = None
    message: str


class BatchAllocationResponse(BaseModel):
    """Summary response for batch room allocation requests."""
    total_processed: int
    successful: int
    failed: int
    results: List[SingleAllocationResult]


# --- Room Management Schemas ---

class RoomResponse(BaseModel):
    """Schema representing a hostel room."""
    room_number: str
    floor: int
    capacity: int
    occupied_beds: int


class RoomListResponse(BaseModel):
    """Response wrapper for a list of hostel rooms."""
    status: str = "success"
    total_rooms: int
    rooms: List[RoomResponse]