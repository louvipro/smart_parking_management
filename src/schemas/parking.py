from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SpotType(str, Enum):
    REGULAR = "regular"
    DISABLED = "disabled"
    VIP = "vip"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"


class VehicleBase(BaseModel):
    license_plate: str = Field(..., min_length=1, max_length=20)
    color: str = Field(..., min_length=1, max_length=50)
    brand: str = Field(..., min_length=1, max_length=50)

    @validator('license_plate')
    def validate_license_plate(cls, v):
        return v.upper().strip()


class VehicleCreate(VehicleBase):
    pass


class VehicleResponse(VehicleBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ParkingSpotBase(BaseModel):
    spot_number: str
    floor: int = Field(..., ge=1, le=10)
    spot_type: SpotType = SpotType.REGULAR


class ParkingSpotResponse(ParkingSpotBase):
    id: int
    is_occupied: bool

    class Config:
        from_attributes = True


class VehicleEntry(BaseModel):
    license_plate: str = Field(..., min_length=1, max_length=20)
    color: str = Field(..., min_length=1, max_length=50)
    brand: str = Field(..., min_length=1, max_length=50)
    spot_type: Optional[SpotType] = SpotType.REGULAR

    @validator('license_plate')
    def validate_license_plate(cls, v):
        return v.upper().strip()


class VehicleExit(BaseModel):
    license_plate: str = Field(..., min_length=1, max_length=20)

    @validator('license_plate')
    def validate_license_plate(cls, v):
        return v.upper().strip()


class ParkingSessionBase(BaseModel):
    vehicle_id: int
    parking_spot_id: int
    entry_time: datetime
    hourly_rate: float = 5.0


class ParkingSessionCreate(ParkingSessionBase):
    pass


class ParkingSessionResponse(ParkingSessionBase):
    id: int
    exit_time: Optional[datetime] = None
    amount_paid: Optional[float] = None
    payment_status: PaymentStatus
    vehicle: VehicleResponse
    parking_spot: ParkingSpotResponse

    class Config:
        from_attributes = True


class PaymentInfo(BaseModel):
    session_id: int
    license_plate: str
    entry_time: datetime
    exit_time: datetime
    duration_hours: float
    amount_due: float
    spot_number: str


class ParkingStatus(BaseModel):
    total_spots: int
    occupied_spots: int
    available_spots: int
    occupancy_rate: float
    floors: List[dict]


class ParkingAnalytics(BaseModel):
    total_revenue: float
    average_duration_hours: float
    total_vehicles_today: int
    current_occupancy: int
    peak_hours: List[dict]
    revenue_by_day: List[dict]