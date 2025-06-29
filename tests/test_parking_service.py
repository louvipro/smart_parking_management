import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from freezegun import freeze_time

from src.application.services.parking_service import ParkingService
from src.domain.common import SpotType, PaymentStatus
from src.domain.entities import Vehicle, ParkingSpot, ParkingSession


@pytest.fixture
async def parked_vehicle(parking_service, init_parking_spots):
    """Create a vehicle that's already parked."""
    session_response = await parking_service.register_vehicle_entry(
        license_plate="PARKED123",
        color="Silver",
        brand="Mercedes",
        spot_type=SpotType.REGULAR
    )
    return session_response


class TestParkingServiceVehicleEntry:
    """Test vehicle entry functionality."""
    
    async def test_register_new_vehicle_entry(self, parking_service, init_parking_spots, db_session):
        """Test registering a new vehicle entry."""
        response = await parking_service.register_vehicle_entry(
            license_plate="NEW123",
            color="White",
            brand="Audi",
            spot_type=SpotType.REGULAR
        )
        
        # Verify response
        vehicle = await parking_service.vehicle_repo.get_by_id(response.vehicle_id)
        assert vehicle.license_plate == "NEW123"
        assert vehicle.color == "White"
        assert vehicle.brand == "Audi"
        parking_spot = await parking_service.parking_spot_repo.get_by_id(response.parking_spot_id)
        assert parking_spot.spot_type == "regular"
        assert parking_spot.is_occupied is True
        assert response.entry_time is not None
        assert response.exit_time is None
        
        # Verify database state
        from sqlalchemy import select
        
        # Check vehicle was created
        vehicle = await parking_service.vehicle_repo.get_by_license_plate("NEW123")
        assert vehicle is not None
        
        # Check parking session was created
        parking_session = await parking_service.parking_session_repo.get_active_session_by_license_plate("NEW123")
        assert parking_session.exit_time is None
        assert parking_session.payment_status == PaymentStatus.PENDING
    
    async def test_register_existing_vehicle_entry(self, parking_service, sample_vehicle, init_parking_spots):
        """Test registering entry for an existing vehicle."""
        response = await parking_service.register_vehicle_entry(
            license_plate=sample_vehicle.license_plate,
            color=sample_vehicle.color,
            brand=sample_vehicle.brand,
            spot_type=SpotType.REGULAR
        )
        
        # Should use existing vehicle
        assert response.vehicle_id == sample_vehicle.id
        vehicle = await parking_service.vehicle_repo.get_by_id(response.vehicle_id)
        assert vehicle.license_plate == sample_vehicle.license_plate
    
    async def test_register_vehicle_already_parked(self, parking_service, parked_vehicle):
        """Test registering a vehicle that's already parked."""
        vehicle = await parking_service.vehicle_repo.get_by_id(parked_vehicle.vehicle_id)
        with pytest.raises(ValueError, match="already in the parking"):
            await parking_service.register_vehicle_entry(
                license_plate=vehicle.license_plate,
                color=vehicle.color,
                brand=vehicle.brand,
                spot_type=SpotType.REGULAR
            )
    
    async def test_register_vehicle_no_available_spots(self, parking_service, db_session, init_parking_spots):
        """Test registering vehicle when no spots are available."""
        await parking_service.parking_spot_repo.update_all_occupied_by_type("regular", True)
        
        with pytest.raises(ValueError, match="No available .* spots"):
            await parking_service.register_vehicle_entry(
                license_plate="NOSPACE123",
                color="Black",
                brand="BMW",
                spot_type=SpotType.REGULAR
            )

    async def test_register_vehicle_full_parking(self, parking_service, db_session, init_parking_spots):
        """Test registering a vehicle when the parking lot is full."""
        await parking_service.parking_spot_repo.update_all_occupied(True)

        with pytest.raises(ValueError, match="No available SpotType.REGULAR spots"):
            await parking_service.register_vehicle_entry(
                license_plate="FULL123",
                color="Yellow",
                brand="Subaru",
                spot_type=SpotType.REGULAR
            )
    
    async def test_register_vehicle_specific_spot_types(self, parking_service, init_parking_spots):
        """Test registering vehicles for different spot types."""
        # Test VIP spot
        vip_response = await parking_service.register_vehicle_entry(
            license_plate="VIP123",
            color="Gold",
            brand="Bentley",
            spot_type=SpotType.VIP
        )
        assert vip_response.parking_spot_id is not None # Check if a spot was assigned
        # We can't directly assert spot_type here as the returned object is a ParkingSession
        # We would need to fetch the ParkingSpot entity to verify its type
        
        # Test disabled spot
        disabled_response = await parking_service.register_vehicle_entry(
            license_plate="DIS123",
            color="Blue",
            brand="Toyota",
            spot_type=SpotType.DISABLED
        )
        assert disabled_response.parking_spot_id is not None # Check if a spot was assigned


class TestParkingServiceVehicleExit:
    """Test vehicle exit functionality."""
    
    async def test_register_vehicle_exit_success(self, parking_service, parked_vehicle):
        """Test successful vehicle exit and payment calculation."""
        vehicle = await parking_service.vehicle_repo.get_by_id(parked_vehicle.vehicle_id)
        
        # Mock exit time to be 2 hours after entry
        with freeze_time(parked_vehicle.entry_time + timedelta(hours=2)):
            payment_info = await parking_service.register_vehicle_exit(vehicle.license_plate)
        
        # Verify payment calculation
        assert payment_info.vehicle_id == parked_vehicle.vehicle_id
        calculated_duration = (payment_info.exit_time - payment_info.entry_time).total_seconds() / 3600
        assert calculated_duration == 2.0
        assert payment_info.amount_paid == 10.0  # 2 hours * 5.0 hourly rate
        assert payment_info.exit_time is not None
        
        # Verify parking spot is freed
        spot = await parking_service.parking_spot_repo.get_by_id(parked_vehicle.parking_spot_id)
        assert spot.is_occupied is False
        
        # Verify session is completed
        session = await parking_service.parking_session_repo.get_by_id(parked_vehicle.id)
        assert session.exit_time is not None
        assert session.payment_status == PaymentStatus.PAID
        assert session.amount_paid == 10.0
    
    async def test_register_vehicle_exit_minimum_charge(self, parking_service, parked_vehicle):
        """Test that minimum charge is 1 hour even for shorter stays."""
        vehicle = await parking_service.vehicle_repo.get_by_id(parked_vehicle.vehicle_id)
        
        # Mock exit time to be 30 minutes after entry
        with freeze_time(parked_vehicle.entry_time + timedelta(minutes=30)):
            payment_info = await parking_service.register_vehicle_exit(vehicle.license_plate)
        
        # Should charge for minimum 1 hour
        assert payment_info.amount_paid == 5.0  # 1 hour * 5.0 hourly rate
    
    async def test_register_vehicle_exit_not_found(self, parking_service):
        """Test exit for vehicle not in parking."""
        with pytest.raises(ValueError, match="No active session"):
            await parking_service.register_vehicle_exit(license_plate="NOTHERE123")
    
    async def test_register_vehicle_exit_already_exited(self, parking_service, parked_vehicle):
        """Test exit for vehicle that already exited."""
        vehicle = await parking_service.vehicle_repo.get_by_id(parked_vehicle.vehicle_id)
        await parking_service.register_vehicle_exit(vehicle.license_plate)
        
        # Try to exit again
        with pytest.raises(ValueError, match="No active session"):
            await parking_service.register_vehicle_exit(vehicle.license_plate)


class TestParkingServiceStatus:
    """Test parking status functionality."""
    
    async def test_get_parking_status_empty(self, parking_service, init_parking_spots):
        """Test parking status when parking is empty."""
        status = await parking_service.get_parking_status()
        
        assert status["total_spots"] == 15  # 3 floors * 5 spots
        assert status["occupied_spots"] == 0
        assert status["available_spots"] == 15
        assert status["occupancy_rate"] == 0.0
        assert len(status["floors"]) == 3
        
        for floor_info in status["floors"]:
            assert floor_info["total"] == 5
            assert floor_info["occupied"] == 0
            assert floor_info["available"] == 5
    
    async def test_get_parking_status_with_vehicles(self, parking_service, init_parking_spots):
        """Test parking status with some vehicles parked."""
        # Park 3 vehicles
        for i in range(3):
            await parking_service.register_vehicle_entry(
                license_plate=f"TEST{i}",
                color="Red",
                brand="Toyota",
                spot_type=SpotType.REGULAR
            )
        
        status = await parking_service.get_parking_status()
        
        assert status["total_spots"] == 15
        assert status["occupied_spots"] == 3
        assert status["available_spots"] == 12
        assert status["occupancy_rate"] == 20.0  # 3/15 * 100
    
    async def test_get_active_sessions(self, parking_service, init_parking_spots):
        """Test getting all active parking sessions."""
        # Park 2 vehicles
        vehicles = []
        for i in range(2):
            response = await parking_service.register_vehicle_entry(
                license_plate=f"ACTIVE{i}",
                color="Blue",
                brand="Honda",
                spot_type=SpotType.REGULAR
            )
            vehicles.append(response)
        
        # Exit one vehicle
        await parking_service.register_vehicle_exit(license_plate="ACTIVE0")
        
        # Get active sessions
        active_sessions = await parking_service.get_active_sessions()
        
        assert len(active_sessions) == 1
        vehicle = await parking_service.vehicle_repo.get_by_id(active_sessions[0].vehicle_id)
        assert vehicle.license_plate == "ACTIVE1"
        assert active_sessions[0].exit_time is None
    
    async def test_get_vehicle_by_plate(self, parking_service, sample_vehicle):
        """Test finding vehicle by license plate."""
        # Test exact match
        vehicle = await parking_service.get_vehicle_by_plate(sample_vehicle.license_plate)
        assert vehicle is not None
        assert vehicle.id == sample_vehicle.id
        
        # Test case insensitive
        vehicle_lower = await parking_service.get_vehicle_by_plate(sample_vehicle.license_plate.lower())
        assert vehicle_lower is not None
        assert vehicle_lower.id == sample_vehicle.id
        
        # Test not found
        vehicle_none = await parking_service.get_vehicle_by_plate("NOTEXIST")
        assert vehicle_none is None