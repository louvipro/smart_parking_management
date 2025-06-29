from datetime import datetime, timedelta, timezone
from src.domain.entities import Vehicle, ParkingSpot, ParkingSession
from src.domain.common import SpotType, PaymentStatus


def test_vehicle_creation():
    """Test that a Vehicle object can be created with correct attributes."""
    now = datetime.now(timezone.utc)
    vehicle = Vehicle(license_plate="TEST123", color="Red", brand="Toyota", id=1, created_at=now)
    assert vehicle.id == 1
    assert vehicle.license_plate == "TEST123"
    assert vehicle.color == "Red"
    assert vehicle.brand == "Toyota"
    assert vehicle.created_at == now

def test_vehicle_creation_defaults():
    """Test Vehicle creation with default optional arguments."""
    vehicle = Vehicle(license_plate="DEF456", color="Blue", brand="Honda")
    assert vehicle.id is None
    assert vehicle.created_at is None

def test_parking_spot_creation():
    """Test that a ParkingSpot object can be created with correct attributes."""
    spot = ParkingSpot(spot_number="A1", floor=1, spot_type=SpotType.REGULAR, is_occupied=False, id=101)
    assert spot.id == 101
    assert spot.spot_number == "A1"
    assert spot.floor == 1
    assert spot.spot_type == SpotType.REGULAR
    assert spot.is_occupied is False

def test_parking_spot_creation_defaults():
    """Test ParkingSpot creation with default optional arguments."""
    spot = ParkingSpot(spot_number="B2", floor=2, spot_type=SpotType.VIP, is_occupied=True)
    assert spot.id is None

def test_parking_session_creation():
    """Test that a ParkingSession object can be created with correct attributes."""
    entry = datetime.now(timezone.utc)
    session = ParkingSession(
        vehicle_id=1,
        parking_spot_id=101,
        entry_time=entry,
        hourly_rate=5.0,
        id=1001,
        exit_time=None,
        amount_paid=None,
        payment_status=PaymentStatus.PENDING
    )
    assert session.id == 1001
    assert session.vehicle_id == 1
    assert session.parking_spot_id == 101
    assert session.entry_time == entry
    assert session.hourly_rate == 5.0
    assert session.exit_time is None
    assert session.amount_paid is None
    assert session.payment_status == PaymentStatus.PENDING

def test_parking_session_creation_with_exit_and_payment():
    """Test ParkingSession creation with exit time and payment details."""
    entry = datetime.now(timezone.utc) - timedelta(hours=2)
    exit_time = datetime.now(timezone.utc)
    session = ParkingSession(
        vehicle_id=2,
        parking_spot_id=102,
        entry_time=entry,
        hourly_rate=5.0,
        exit_time=exit_time,
        amount_paid=10.0,
        payment_status=PaymentStatus.PAID
    )
    assert session.exit_time == exit_time
    assert session.amount_paid == 10.0
    assert session.payment_status == PaymentStatus.PAID

def test_parking_session_creation_defaults():
    """Test ParkingSession creation with default optional arguments."""
    entry = datetime.now(timezone.utc)
    session = ParkingSession(
        vehicle_id=3,
        parking_spot_id=103,
        entry_time=entry,
        hourly_rate=5.0
    )
    assert session.exit_time is None
    assert session.amount_paid is None
    assert session.payment_status is None
