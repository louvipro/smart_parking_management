import pytest
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime, timezone

import os
from unittest.mock import patch, MagicMock

# Import the original cleanup_duplicates function
from src.infrastructure.persistence.cleanup import cleanup_duplicates
from src.shared.custom_types import UTCDateTime

# Define a test-specific Base and models
TestBase = declarative_base()

class TestVehicle(TestBase):
    __tablename__ = "vehicles"
    id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String, index=True) # No unique=True
    color = Column(String, nullable=False)
    brand = Column(String, nullable=False)
    created_at = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc))

    parking_sessions = relationship("TestParkingSession", back_populates="vehicle")

class TestParkingSpot(TestBase):
    __tablename__ = "parking_spots"
    id = Column(Integer, primary_key=True, index=True)
    spot_number = Column(String, unique=True, index=True)
    is_occupied = Column(Boolean, default=False)
    floor = Column(Integer, default=1)
    spot_type = Column(String, default="regular")

    parking_sessions = relationship("TestParkingSession", back_populates="parking_spot")

class TestParkingSession(TestBase):
    __tablename__ = "parking_sessions"
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    parking_spot_id = Column(Integer, ForeignKey("parking_spots.id"))
    entry_time = Column(UTCDateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    exit_time = Column(UTCDateTime, nullable=True)
    amount_paid = Column(Float, nullable=True)
    payment_status = Column(String, default="pending")
    hourly_rate = Column(Float, default=5.0)

    vehicle = relationship("TestVehicle", back_populates="parking_sessions")
    parking_spot = relationship("TestParkingSpot", back_populates="parking_sessions")

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

@pytest.fixture(scope="function")
def db_session_cleanup():
    engine = create_engine("sqlite:///:memory:")
    TestBase.metadata.create_all(engine) # Use TestBase
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session, engine # Yield both session and engine
    finally:
        session.close()
        TestBase.metadata.drop_all(engine) # Use TestBase

def test_cleanup_duplicates(db_session_cleanup):
    session, test_engine = db_session_cleanup

    # Create original vehicle using TestVehicle
    original_vehicle = TestVehicle(license_plate="ABC-123", color="red", brand="Honda")
    session.add(original_vehicle)
    session.commit()
    session.refresh(original_vehicle)

    # Create duplicate vehicles using TestVehicle
    duplicate_vehicle_1 = TestVehicle(license_plate="ABC-123", color="blue", brand="Ford")
    duplicate_vehicle_2 = TestVehicle(license_plate="ABC-123", color="green", brand="BMW")
    session.add_all([duplicate_vehicle_1, duplicate_vehicle_2])
    session.commit() # This commit should now succeed because TestVehicle has no unique constraint
    session.refresh(duplicate_vehicle_1)
    session.refresh(duplicate_vehicle_2)

    # Create parking spots for sessions
    spot1_obj = TestParkingSpot(spot_number="A1", floor=1)
    spot2_obj = TestParkingSpot(spot_number="A2", floor=1)
    spot3_obj = TestParkingSpot(spot_number="A3", floor=1)
    session.add_all([spot1_obj, spot2_obj, spot3_obj])
    session.commit()
    session.refresh(spot1_obj)
    session.refresh(spot2_obj)
    session.refresh(spot3_obj)

    # Create parking sessions linked to original and duplicate vehicles
    spot1 = TestParkingSession( # Use TestParkingSession
        vehicle_id=original_vehicle.id,
        parking_spot_id=spot1_obj.id,
        entry_time=datetime.now(timezone.utc),
    )
    spot2 = TestParkingSession( # Use TestParkingSession
        vehicle_id=duplicate_vehicle_1.id,
        parking_spot_id=spot2_obj.id,
        entry_time=datetime.now(timezone.utc),
    )
    spot3 = TestParkingSession( # Use TestParkingSession
        vehicle_id=duplicate_vehicle_2.id,
        parking_spot_id=spot3_obj.id,
        entry_time=datetime.now(timezone.utc),
    )
    session.add_all([spot1, spot2, spot3])
    session.commit()

    # Before cleanup: check counts
    assert session.query(TestVehicle).count() == 3 # Use TestVehicle
    assert session.query(TestParkingSession).count() == 3 # Use TestParkingSession

    # Temporarily override DATABASE_URL for the test
    original_db_url = os.getenv("DATABASE_URL")
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    # Create a mock for the Session object in cleanup.py
    # This mock will be called as Session(engine)
    mock_cleanup_session_factory = MagicMock()

    # Configure the mock so that when it's called (e.g., Session(engine)),
    # it returns a context manager that yields our actual test session.
    # The `engine` argument passed to Session() in cleanup.py will be ignored by our mock.
    mock_cleanup_session_factory.return_value.__enter__.return_value = session
    mock_cleanup_session_factory.return_value.__exit__.return_value = None

    # Patch src.database.cleanup to use our test models and session
    with patch('src.infrastructure.persistence.cleanup.Vehicle', TestVehicle),         patch('src.infrastructure.persistence.cleanup.ParkingSession', TestParkingSession),         patch('src.infrastructure.persistence.cleanup.create_engine', lambda *args, **kwargs: test_engine),         patch('src.infrastructure.persistence.cleanup.Session', mock_cleanup_session_factory): # Patch Session to return the context manager

        cleanup_duplicates()

    # Restore original DATABASE_URL
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        del os.environ["DATABASE_URL"]

    # After cleanup: check counts and updated sessions
    assert session.query(TestVehicle).count() == 1 # Use TestVehicle
    assert session.query(TestVehicle).filter_by(license_plate="ABC-123").one().id == original_vehicle.id # Use TestVehicle

    # All sessions should now point to the original vehicle
    for s in session.query(TestParkingSession).all(): # Use TestParkingSession
        assert s.vehicle_id == original_vehicle.id