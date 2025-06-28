import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from services.parking_service import ParkingService
from schemas.parking import VehicleEntry, VehicleExit, SpotType, PaymentStatus
from database.models import Vehicle, ParkingSpot, ParkingSession


@pytest.fixture
async def parking_service(db_session):
    """Create a ParkingService instance with test database session."""
    return ParkingService(db=db_session)


@pytest.fixture
async def parked_vehicle(db_session, parking_service, init_parking_spots):
    """Create a vehicle that's already parked."""
    entry_data = VehicleEntry(
        license_plate="PARKED123",
        color="Silver",
        brand="Mercedes",
        spot_type=SpotType.REGULAR
    )
    
    session_response = await parking_service.register_vehicle_entry(entry_data)
    return session_response


class TestParkingServiceVehicleEntry:
    """Test vehicle entry functionality."""
    
    async def test_register_new_vehicle_entry(self, parking_service, init_parking_spots, db_session):
        """Test registering a new vehicle entry."""
        entry_data = VehicleEntry(
            license_plate="NEW123",
            color="White",
            brand="Audi",
            spot_type=SpotType.REGULAR
        )
        
        # Register vehicle
        response = await parking_service.register_vehicle_entry(entry_data)
        
        # Verify response
        assert response.vehicle.license_plate == "NEW123"
        assert response.vehicle.color == "White"
        assert response.vehicle.brand == "Audi"
        assert response.parking_spot.spot_type == "regular"
        assert response.parking_spot.is_occupied is True
        assert response.entry_time is not None
        assert response.exit_time is None
        
        # Verify database state
        from sqlalchemy import select
        
        # Check vehicle was created
        vehicle_result = await db_session.execute(
            select(Vehicle).where(Vehicle.license_plate == "NEW123")
        )
        vehicle = vehicle_result.scalar_one()
        assert vehicle is not None
        
        # Check parking session was created
        session_result = await db_session.execute(
            select(ParkingSession).where(ParkingSession.vehicle_id == vehicle.id)
        )
        parking_session = session_result.scalar_one()
        assert parking_session.exit_time is None
        assert parking_session.payment_status == "pending"
    
    async def test_register_existing_vehicle_entry(self, parking_service, sample_vehicle, init_parking_spots):
        """Test registering entry for an existing vehicle."""
        entry_data = VehicleEntry(
            license_plate=sample_vehicle.license_plate,
            color=sample_vehicle.color,
            brand=sample_vehicle.brand,
            spot_type=SpotType.REGULAR
        )
        
        response = await parking_service.register_vehicle_entry(entry_data)
        
        # Should use existing vehicle
        assert response.vehicle.id == sample_vehicle.id
        assert response.vehicle.license_plate == sample_vehicle.license_plate
    
    async def test_register_vehicle_already_parked(self, parking_service, parked_vehicle):
        """Test registering a vehicle that's already parked."""
        entry_data = VehicleEntry(
            license_plate=parked_vehicle.vehicle.license_plate,
            color=parked_vehicle.vehicle.color,
            brand=parked_vehicle.vehicle.brand,
            spot_type=SpotType.REGULAR
        )
        
        with pytest.raises(ValueError, match="already in the parking"):
            await parking_service.register_vehicle_entry(entry_data)
    
    async def test_register_vehicle_no_available_spots(self, parking_service, db_session, init_parking_spots):
        """Test registering vehicle when no spots are available."""
        from sqlalchemy import select, update
        
        # Mark all regular spots as occupied
        await db_session.execute(
            update(ParkingSpot)
            .where(ParkingSpot.spot_type == "regular")
            .values(is_occupied=True)
        )
        await db_session.commit()
        
        entry_data = VehicleEntry(
            license_plate="NOSPACE123",
            color="Black",
            brand="BMW",
            spot_type=SpotType.REGULAR
        )
        
        with pytest.raises(ValueError, match="No available .* spots"):
            await parking_service.register_vehicle_entry(entry_data)
    
    async def test_register_vehicle_specific_spot_types(self, parking_service, init_parking_spots):
        """Test registering vehicles for different spot types."""
        # Test VIP spot
        vip_entry = VehicleEntry(
            license_plate="VIP123",
            color="Gold",
            brand="Bentley",
            spot_type=SpotType.VIP
        )
        vip_response = await parking_service.register_vehicle_entry(vip_entry)
        assert vip_response.parking_spot.spot_type == "vip"
        
        # Test disabled spot
        disabled_entry = VehicleEntry(
            license_plate="DIS123",
            color="Blue",
            brand="Toyota",
            spot_type=SpotType.DISABLED
        )
        disabled_response = await parking_service.register_vehicle_entry(disabled_entry)
        assert disabled_response.parking_spot.spot_type == "disabled"


class TestParkingServiceVehicleExit:
    """Test vehicle exit functionality."""
    
    async def test_register_vehicle_exit_success(self, parking_service, parked_vehicle, db_session):
        """Test successful vehicle exit and payment calculation."""
        from sqlalchemy import select
        
        # Mock exit time to be 2 hours after entry
        with patch('services.parking_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = parked_vehicle.entry_time + timedelta(hours=2)
            
            exit_data = VehicleExit(license_plate=parked_vehicle.vehicle.license_plate)
            payment_info = await parking_service.register_vehicle_exit(exit_data)
        
        # Verify payment calculation
        assert payment_info.license_plate == parked_vehicle.vehicle.license_plate
        assert payment_info.duration_hours == 2.0
        assert payment_info.amount_due == 10.0  # 2 hours * 5.0 hourly rate
        assert payment_info.exit_time is not None
        
        # Verify parking spot is freed
        spot_result = await db_session.execute(
            select(ParkingSpot).where(ParkingSpot.id == parked_vehicle.parking_spot.id)
        )
        spot = spot_result.scalar_one()
        assert spot.is_occupied is False
        
        # Verify session is completed
        session_result = await db_session.execute(
            select(ParkingSession).where(ParkingSession.id == parked_vehicle.id)
        )
        session = session_result.scalar_one()
        assert session.exit_time is not None
        assert session.payment_status == "paid"
        assert session.amount_paid == 10.0
    
    async def test_register_vehicle_exit_minimum_charge(self, parking_service, parked_vehicle):
        """Test that minimum charge is 1 hour even for shorter stays."""
        # Mock exit time to be 30 minutes after entry
        with patch('services.parking_service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = parked_vehicle.entry_time + timedelta(minutes=30)
            
            exit_data = VehicleExit(license_plate=parked_vehicle.vehicle.license_plate)
            payment_info = await parking_service.register_vehicle_exit(exit_data)
        
        # Should charge for minimum 1 hour
        assert payment_info.duration_hours == 1.0
        assert payment_info.amount_due == 5.0  # 1 hour * 5.0 hourly rate
    
    async def test_register_vehicle_exit_not_found(self, parking_service):
        """Test exit for vehicle not in parking."""
        exit_data = VehicleExit(license_plate="NOTHERE123")
        
        with pytest.raises(ValueError, match="No active session"):
            await parking_service.register_vehicle_exit(exit_data)
    
    async def test_register_vehicle_exit_already_exited(self, parking_service, parked_vehicle):
        """Test exit for vehicle that already exited."""
        # First exit
        exit_data = VehicleExit(license_plate=parked_vehicle.vehicle.license_plate)
        await parking_service.register_vehicle_exit(exit_data)
        
        # Try to exit again
        with pytest.raises(ValueError, match="No active session"):
            await parking_service.register_vehicle_exit(exit_data)


class TestParkingServiceStatus:
    """Test parking status functionality."""
    
    async def test_get_parking_status_empty(self, parking_service, init_parking_spots):
        """Test parking status when parking is empty."""
        status = await parking_service.get_parking_status()
        
        assert status.total_spots == 15  # 3 floors * 5 spots
        assert status.occupied_spots == 0
        assert status.available_spots == 15
        assert status.occupancy_rate == 0.0
        assert len(status.floors) == 3
        
        for floor_info in status.floors:
            assert floor_info["total"] == 5
            assert floor_info["occupied"] == 0
            assert floor_info["available"] == 5
    
    async def test_get_parking_status_with_vehicles(self, parking_service, init_parking_spots):
        """Test parking status with some vehicles parked."""
        # Park 3 vehicles
        for i in range(3):
            entry_data = VehicleEntry(
                license_plate=f"TEST{i}",
                color="Red",
                brand="Toyota",
                spot_type=SpotType.REGULAR
            )
            await parking_service.register_vehicle_entry(entry_data)
        
        status = await parking_service.get_parking_status()
        
        assert status.total_spots == 15
        assert status.occupied_spots == 3
        assert status.available_spots == 12
        assert status.occupancy_rate == 20.0  # 3/15 * 100
    
    async def test_get_active_sessions(self, parking_service, init_parking_spots):
        """Test getting all active parking sessions."""
        # Park 2 vehicles
        vehicles = []
        for i in range(2):
            entry_data = VehicleEntry(
                license_plate=f"ACTIVE{i}",
                color="Blue",
                brand="Honda",
                spot_type=SpotType.REGULAR
            )
            response = await parking_service.register_vehicle_entry(entry_data)
            vehicles.append(response)
        
        # Exit one vehicle
        exit_data = VehicleExit(license_plate="ACTIVE0")
        await parking_service.register_vehicle_exit(exit_data)
        
        # Get active sessions
        active_sessions = await parking_service.get_active_sessions()
        
        assert len(active_sessions) == 1
        assert active_sessions[0].vehicle.license_plate == "ACTIVE1"
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