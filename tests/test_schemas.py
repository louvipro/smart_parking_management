from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from src.infrastructure.api.schemas.parking import (
    VehicleBase,
    VehicleCreate,
    VehicleResponse,
    ParkingSpotBase,
    ParkingSpotResponse,
    VehicleEntry,
    VehicleExit,
    ParkingSessionBase,
    ParkingSessionCreate,
    ParkingSessionResponse,
    PaymentInfo,
    ParkingStatus,
    ParkingAnalytics,
)
from src.domain.common import SpotType, PaymentStatus


def test_spot_type_enum():
    assert SpotType.REGULAR == "regular"
    assert SpotType.DISABLED == "disabled"
    assert SpotType.VIP == "vip"


def test_payment_status_enum():
    assert PaymentStatus.PENDING == "pending"
    assert PaymentStatus.PAID == "paid"


def test_vehicle_base_valid():
    vehicle = VehicleBase(license_plate="abc-123", color="red", brand="honda")
    assert vehicle.license_plate == "ABC-123"
    assert vehicle.color == "red"
    assert vehicle.brand == "honda"


def test_vehicle_base_license_plate_validation():
    with pytest.raises(ValidationError):
        VehicleBase(license_plate="", color="red", brand="honda")
    with pytest.raises(ValidationError):
        VehicleBase(license_plate="a" * 21, color="red", brand="honda")


def test_vehicle_create_valid():
    vehicle_create = VehicleCreate(license_plate="xyz-789", color="blue", brand="ford")
    assert vehicle_create.license_plate == "XYZ-789"


def test_vehicle_response_valid():
    now = datetime.now(timezone.utc)
    vehicle_response = VehicleResponse(
        id=1, license_plate="def-456", color="green", brand="toyota", created_at=now
    )
    assert vehicle_response.id == 1
    assert vehicle_response.license_plate == "DEF-456"
    assert vehicle_response.created_at == now


def test_parking_spot_base_valid():
    spot = ParkingSpotBase(spot_number="A1", floor=1, spot_type=SpotType.REGULAR)
    assert spot.spot_number == "A1"
    assert spot.floor == 1
    assert spot.spot_type == SpotType.REGULAR


def test_parking_spot_base_floor_validation():
    with pytest.raises(ValidationError):
        ParkingSpotBase(spot_number="A1", floor=0)
    with pytest.raises(ValidationError):
        ParkingSpotBase(spot_number="A1", floor=11)


def test_parking_spot_response_valid():
    spot_response = ParkingSpotResponse(
        id=1, spot_number="B2", floor=2, spot_type=SpotType.DISABLED, is_occupied=True
    )
    assert spot_response.id == 1
    assert spot_response.spot_number == "B2"
    assert spot_response.is_occupied is True


def test_vehicle_entry_valid():
    entry = VehicleEntry(
        license_plate="ghi-789", color="black", brand="bmw", spot_type=SpotType.VIP
    )
    assert entry.license_plate == "GHI-789"
    assert entry.spot_type == SpotType.VIP


def test_vehicle_entry_default_spot_type():
    entry = VehicleEntry(license_plate="jkl-000", color="white", brand="audi")
    assert entry.spot_type == SpotType.REGULAR


def test_vehicle_exit_valid():
    exit_data = VehicleExit(license_plate="mno-111")
    assert exit_data.license_plate == "MNO-111"


def test_parking_session_base_valid():
    now = datetime.now(timezone.utc)
    session = ParkingSessionBase(
        vehicle_id=1, parking_spot_id=1, entry_time=now, hourly_rate=10.0
    )
    assert session.vehicle_id == 1
    assert session.parking_spot_id == 1
    assert session.entry_time == now
    assert session.hourly_rate == 10.0


def test_parking_session_create_valid():
    now = datetime.now(timezone.utc)
    session_create = ParkingSessionCreate(
        vehicle_id=2, parking_spot_id=2, entry_time=now
    )
    assert session_create.vehicle_id == 2


def test_parking_session_response_valid():
    now = datetime.now(timezone.utc)
    exit_time = now + timedelta(hours=2)
    vehicle_response = VehicleResponse(
        id=1, license_plate="test-1", color="red", brand="test", created_at=now
    )
    parking_spot_response = ParkingSpotResponse(
        id=1, spot_number="C3", floor=3, is_occupied=False
    )
    session_response = ParkingSessionResponse(
        id=1,
        vehicle_id=1,
        parking_spot_id=1,
        entry_time=now,
        exit_time=exit_time,
        amount_paid=20.0,
        payment_status=PaymentStatus.PAID,
        vehicle=vehicle_response,
        parking_spot=parking_spot_response,
    )
    assert session_response.id == 1
    assert session_response.exit_time == exit_time
    assert session_response.amount_paid == 20.0
    assert session_response.payment_status == PaymentStatus.PAID
    assert session_response.vehicle == vehicle_response
    assert session_response.parking_spot == parking_spot_response


def test_parking_session_response_datetime_awareness():
    # Test with naive datetime
    naive_dt = datetime.now()
    session_response = ParkingSessionResponse(
        id=1,
        vehicle_id=1,
        parking_spot_id=1,
        entry_time=naive_dt,
        payment_status=PaymentStatus.PENDING,
        vehicle=VehicleResponse(
            id=1, license_plate="test-1", color="red", brand="test", created_at=naive_dt
        ),
        parking_spot=ParkingSpotResponse(
            id=1, spot_number="C3", floor=3, is_occupied=False
        ),
    )
    assert session_response.entry_time.tzinfo == timezone.utc

    # Test with aware datetime
    aware_dt = datetime.now(timezone.utc)
    session_response = ParkingSessionResponse(
        id=1,
        vehicle_id=1,
        parking_spot_id=1,
        entry_time=aware_dt,
        payment_status=PaymentStatus.PENDING,
        vehicle=VehicleResponse(
            id=1, license_plate="test-1", color="red", brand="test", created_at=aware_dt
        ),
        parking_spot=ParkingSpotResponse(
            id=1, spot_number="C3", floor=3, is_occupied=False
        ),
    )
    assert session_response.entry_time == aware_dt


def test_payment_info_valid():
    now = datetime.now(timezone.utc)
    exit_time = now + timedelta(hours=1)
    payment_info = PaymentInfo(
        session_id=1,
        license_plate="xyz-789",
        entry_time=now,
        exit_time=exit_time,
        duration_hours=1.0,
        amount_due=5.0,
        spot_number="A1",
    )
    assert payment_info.session_id == 1
    assert payment_info.license_plate == "XYZ-789"
    assert payment_info.duration_hours == 1.0
    assert payment_info.amount_due == 5.0


def test_parking_status_valid():
    parking_status = ParkingStatus(
        total_spots=100,
        occupied_spots=50,
        available_spots=50,
        occupancy_rate=0.5,
        floors=[{"floor": 1, "available": 20, "occupied": 30}],
    )
    assert parking_status.total_spots == 100
    assert parking_status.occupancy_rate == 0.5


def test_parking_analytics_valid():
    analytics = ParkingAnalytics(
        total_revenue=1000.0,
        average_duration_hours=2.5,
        total_vehicles_today=100,
        current_occupancy=40,
        peak_hours=[{"hour": 10, "vehicles": 15}],
        revenue_by_day=[{"date": "2023-01-01", "revenue": 100.0}],
    )
    assert analytics.total_revenue == 1000.0
    assert analytics.average_duration_hours == 2.5
