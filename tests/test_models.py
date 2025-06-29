import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.persistence.models.models import Base, Vehicle, ParkingSpot, ParkingSession


@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def test_vehicle_model(db_session):
    vehicle = Vehicle(
        license_plate="TEST123", color="red", brand="Toyota", created_at=datetime.now(timezone.utc)
    )
    db_session.add(vehicle)
    db_session.commit()
    db_session.refresh(vehicle)

    assert vehicle.id is not None
    assert vehicle.license_plate == "TEST123"
    assert vehicle.color == "red"
    assert vehicle.brand == "Toyota"
    assert isinstance(vehicle.created_at, datetime)
    assert vehicle.created_at.tzinfo == timezone.utc


def test_parking_spot_model(db_session):
    spot = ParkingSpot(
        spot_number="A1", floor=1, is_occupied=False, spot_type="regular"
    )
    db_session.add(spot)
    db_session.commit()
    db_session.refresh(spot)

    assert spot.id is not None
    assert spot.spot_number == "A1"
    assert spot.floor == 1
    assert spot.is_occupied is False
    assert spot.spot_type == "regular"


def test_parking_session_model(db_session):
    vehicle = Vehicle(license_plate="TEST456", color="blue", brand="Ford")
    spot = ParkingSpot(spot_number="B2", floor=2)
    db_session.add_all([vehicle, spot])
    db_session.commit()
    db_session.refresh(vehicle)
    db_session.refresh(spot)

    entry_time = datetime.now(timezone.utc)
    session = ParkingSession(
        vehicle_id=vehicle.id,
        parking_spot_id=spot.id,
        entry_time=entry_time,
        hourly_rate=10.0,
        payment_status="pending",
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.id is not None
    assert session.vehicle_id == vehicle.id
    assert session.parking_spot_id == spot.id
    assert session.entry_time == entry_time
    assert session.hourly_rate == 10.0
    assert session.payment_status == "pending"
    assert session.exit_time is None
    assert session.amount_paid is None

    # Test relationships
    assert session.vehicle == vehicle
    assert session.parking_spot == spot


def test_parking_session_duration_hours_property(db_session):
    vehicle = Vehicle(license_plate="TEST789", color="green", brand="BMW")
    spot = ParkingSpot(spot_number="C3", floor=3)
    db_session.add_all([vehicle, spot])
    db_session.commit()
    db_session.refresh(vehicle)
    db_session.refresh(spot)

    entry_time = datetime.now(timezone.utc) - timedelta(hours=2, minutes=30)
    exit_time = datetime.now(timezone.utc)

    session = ParkingSession(
        vehicle_id=vehicle.id,
        parking_spot_id=spot.id,
        entry_time=entry_time,
        exit_time=exit_time,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.duration_hours == pytest.approx(2.5)
    assert session.calculate_amount == pytest.approx(12.5) # 2.5 hours * 5.0 hourly_rate (default)


def test_parking_session_duration_hours_no_exit_time(db_session):
    vehicle = Vehicle(license_plate="TEST000", color="yellow", brand="Audi")
    spot = ParkingSpot(spot_number="D4", floor=4)
    db_session.add_all([vehicle, spot])
    db_session.commit()
    db_session.refresh(vehicle)
    db_session.refresh(spot)

    entry_time = datetime.now(timezone.utc)
    session = ParkingSession(
        vehicle_id=vehicle.id,
        parking_spot_id=spot.id,
        entry_time=entry_time,
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.duration_hours is None
    assert session.calculate_amount is None


def test_parking_session_calculate_amount_property_with_custom_rate(db_session):
    vehicle = Vehicle(license_plate="TEST111", color="orange", brand="Mercedes")
    spot = ParkingSpot(spot_number="E5", floor=5)
    db_session.add_all([vehicle, spot])
    db_session.commit()
    db_session.refresh(vehicle)
    db_session.refresh(spot)

    entry_time = datetime.now(timezone.utc) - timedelta(hours=3)
    exit_time = datetime.now(timezone.utc)

    session = ParkingSession(
        vehicle_id=vehicle.id,
        parking_spot_id=spot.id,
        entry_time=entry_time,
        exit_time=exit_time,
        hourly_rate=7.5
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.duration_hours == pytest.approx(3.0)
    assert session.calculate_amount == pytest.approx(22.5) # 3 hours * 7.5 hourly_rate
