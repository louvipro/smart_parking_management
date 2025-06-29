from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone
from typing import Optional, List
from src.domain.common import SpotType, PaymentStatus





class VehicleBase(BaseModel):
    license_plate: str = Field(..., min_length=1, max_length=20)
    color: str = Field(..., min_length=1, max_length=50)
    brand: str = Field(..., min_length=1, max_length=50)

    @field_validator('license_plate')
    def validate_license_plate(cls, v):  # pylint: disable=no-self-argument
        return v.upper().strip()


class VehicleCreate(VehicleBase):
    pass


class VehicleResponse(VehicleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ParkingSpotBase(BaseModel):
    spot_number: str
    floor: int = Field(..., ge=1, le=10)
    spot_type: SpotType = SpotType.REGULAR


class ParkingSpotResponse(ParkingSpotBase):
    id: int
    is_occupied: bool

    model_config = ConfigDict(from_attributes=True)


class VehicleEntry(BaseModel):
    license_plate: str = Field(..., min_length=1, max_length=20)
    color: str = Field(..., min_length=1, max_length=50)
    brand: str = Field(..., min_length=1, max_length=50)
    spot_type: Optional[SpotType] = SpotType.REGULAR

    @field_validator('license_plate')
    def validate_license_plate(cls, v):  # pylint: disable=no-self-argument
        return v.upper().strip()


class VehicleExit(BaseModel):
    license_plate: str = Field(..., min_length=1, max_length=20)

    @field_validator('license_plate')
    def validate_license_plate(cls, v):  # pylint: disable=no-self-argument
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

    @field_validator('entry_time', 'exit_time')
    @classmethod
    def make_datetime_aware(cls, dt: datetime) -> datetime:
        if dt is None:
            return dt
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    model_config = ConfigDict(from_attributes=True)


class PaymentInfo(BaseModel):
    session_id: int
    license_plate: str
    entry_time: datetime
    exit_time: datetime
    duration_hours: float
    amount_due: float
    spot_number: str

    @field_validator('license_plate')
    def validate_license_plate(cls, v):  # pylint: disable=no-self-argument
        return v.upper().strip()


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
