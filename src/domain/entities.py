from datetime import datetime
from typing import Optional

from src.domain.common import SpotType, PaymentStatus


class Vehicle:
    def __init__(
        self, license_plate: str, color: str, brand: str, id: Optional[int] = None, created_at: Optional[datetime] = None
    ):
        self.id = id
        self.license_plate = license_plate
        self.color = color
        self.brand = brand
        self.created_at = created_at


class ParkingSpot:
    def __init__(
        self, spot_number: str, floor: int, spot_type: SpotType, is_occupied: bool, id: Optional[int] = None
    ):
        self.id = id
        self.spot_number = spot_number
        self.floor = floor
        self.spot_type = spot_type
        self.is_occupied = is_occupied


class ParkingSession:
    def __init__(
        self,
        vehicle_id: int,
        parking_spot_id: int,
        entry_time: datetime,
        hourly_rate: float,
        id: Optional[int] = None,
        exit_time: Optional[datetime] = None,
        amount_paid: Optional[float] = None,
        payment_status: Optional[PaymentStatus] = None,
    ):
        self.id = id
        self.vehicle_id = vehicle_id
        self.parking_spot_id = parking_spot_id
        self.entry_time = entry_time
        self.exit_time = exit_time
        self.amount_paid = amount_paid
        self.payment_status = payment_status
        self.hourly_rate = hourly_rate
