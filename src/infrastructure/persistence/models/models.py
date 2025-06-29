from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from src.shared.custom_types import UTCDateTime # Updated import path

Base = declarative_base()


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String, unique=True, index=True)
    color = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    parking_sessions = relationship("ParkingSession", back_populates="vehicle")


class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    spot_number = Column(String, unique=True, index=True)
    is_occupied = Column(Boolean, default=False)
    floor = Column(Integer, default=1)
    spot_type = Column(String, default="regular")  # regular, disabled, vip

    parking_sessions = relationship("ParkingSession", back_populates="parking_spot")


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    parking_spot_id = Column(Integer, ForeignKey("parking_spots.id"))
    entry_time = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    exit_time = Column(UTCDateTime, nullable=True)
    amount_paid = Column(Float, nullable=True)
    payment_status = Column(String, default="pending")  # pending, paid
    hourly_rate = Column(Float, default=5.0)

    vehicle = relationship("Vehicle", back_populates="parking_sessions")
    parking_spot = relationship("ParkingSpot", back_populates="parking_sessions")

    @property
    def duration_hours(self):
        if self.exit_time:
            duration = self.exit_time - self.entry_time
            return duration.total_seconds() / 3600
        return None

    @property
    def calculate_amount(self):
        if self.duration_hours:
            return round(self.duration_hours * self.hourly_rate, 2)
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "vehicle_id": self.vehicle_id,
            "parking_spot_id": self.parking_spot_id,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "amount_paid": self.amount_paid,
            "payment_status": self.payment_status,
            "hourly_rate": self.hourly_rate,
        }