import pytest
from sqlalchemy import select, inspect
from datetime import datetime, timedelta
import os
import tempfile

from src.infrastructure.persistence.models.models import Vehicle, ParkingSpot, ParkingSession
from src.infrastructure.persistence.database import init_db # Import init_db directly


class TestVehicleModel:
    """Test Vehicle model CRUD operations."""
    
    async def test_create_vehicle(self, db_session):
        """Test creating a new vehicle."""
        vehicle = Vehicle(
            license_plate="XYZ789",
            color="Blue",
            brand="Honda"
        )
        db_session.add(vehicle)
        await db_session.commit()
        
        # Verify vehicle was created
        result = await db_session.execute(
            select(Vehicle).where(Vehicle.license_plate == "XYZ789")
        )
        saved_vehicle = result.scalar_one()
        
        assert saved_vehicle.license_plate == "XYZ789"
        assert saved_vehicle.color == "Blue"
        assert saved_vehicle.brand == "Honda"
        assert saved_vehicle.created_at is not None
    
    async def test_read_vehicle(self, sample_vehicle, db_session):
        """Test reading an existing vehicle."""
        result = await db_session.execute(
            select(Vehicle).where(Vehicle.id == sample_vehicle.id)
        )
        vehicle = result.scalar_one()
        
        assert vehicle.license_plate == sample_vehicle.license_plate
        assert vehicle.color == sample_vehicle.color
        assert vehicle.brand == sample_vehicle.brand
    
    async def test_update_vehicle(self, sample_vehicle, db_session):
        """Test updating a vehicle."""
        sample_vehicle.color = "Green"
        await db_session.commit()
        
        # Verify update
        result = await db_session.execute(
            select(Vehicle).where(Vehicle.id == sample_vehicle.id)
        )
        updated_vehicle = result.scalar_one()
        
        assert updated_vehicle.color == "Green"
    
    async def test_delete_vehicle(self, db_session):
        """Test deleting a vehicle."""
        # Create a vehicle
        vehicle = Vehicle(
            license_plate="DEL123",
            color="Black",
            brand="BMW"
        )
        db_session.add(vehicle)
        await db_session.commit()
        
        vehicle_id = vehicle.id
        
        # Delete the vehicle
        await db_session.delete(vehicle)
        await db_session.commit()
        
        # Verify deletion
        result = await db_session.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id)
        )
        assert result.scalar_one_or_none() is None
    
    async def test_unique_license_plate_constraint(self, sample_vehicle, db_session):
        """Test that license plates must be unique."""
        duplicate_vehicle = Vehicle(
            license_plate=sample_vehicle.license_plate,
            color="Yellow",
            brand="Ford"
        )
        db_session.add(duplicate_vehicle)
        
        with pytest.raises(Exception):  # IntegrityError
            await db_session.commit()


class TestParkingSpotModel:
    """Test ParkingSpot model CRUD operations."""
    
    async def test_create_parking_spot(self, db_session):
        """Test creating a new parking spot."""
        spot = ParkingSpot(
            spot_number="4-01",
            floor=4,
            spot_type="regular",
            is_occupied=False
        )
        db_session.add(spot)
        await db_session.commit()
        
        # Verify spot was created
        result = await db_session.execute(
            select(ParkingSpot).where(ParkingSpot.spot_number == "4-01")
        )
        saved_spot = result.scalar_one()
        
        assert saved_spot.spot_number == "4-01"
        assert saved_spot.floor == 4
        assert saved_spot.spot_type == "regular"
        assert saved_spot.is_occupied is False
    
    async def test_read_parking_spots(self, init_parking_spots, db_session):
        """Test reading parking spots."""
        result = await db_session.execute(select(ParkingSpot))
        spots = result.scalars().all()
        
        assert len(spots) == 15  # 3 floors * 5 spots
        
        # Check spot types distribution
        spot_types = [spot.spot_type for spot in spots]
        assert spot_types.count("disabled") == 3
        assert spot_types.count("vip") == 3
        assert spot_types.count("regular") == 9
    
    async def test_update_parking_spot_occupancy(self, init_parking_spots, db_session):
        """Test updating parking spot occupancy."""
        # Get first spot
        result = await db_session.execute(
            select(ParkingSpot).where(ParkingSpot.spot_number == "1-01")
        )
        spot = result.scalar_one()
        
        # Update occupancy
        spot.is_occupied = True
        await db_session.commit()
        
        # Verify update
        result = await db_session.execute(
            select(ParkingSpot).where(ParkingSpot.spot_number == "1-01")
        )
        updated_spot = result.scalar_one()
        
        assert updated_spot.is_occupied is True
    
    async def test_query_available_spots_by_type(self, init_parking_spots, db_session):
        """Test querying available spots by type."""
        # Query available regular spots
        result = await db_session.execute(
            select(ParkingSpot).where(
                (ParkingSpot.spot_type == "regular") & 
                (ParkingSpot.is_occupied == False)
            )
        )
        available_regular = result.scalars().all()
        
        assert len(available_regular) == 9
        assert all(spot.spot_type == "regular" for spot in available_regular)
        assert all(not spot.is_occupied for spot in available_regular)


class TestParkingSessionModel:
    """Test ParkingSession model CRUD operations."""
    
    async def test_create_parking_session(self, db_session, sample_vehicle, init_parking_spots):
        """Test creating a new parking session."""
        # Get an available spot
        result = await db_session.execute(
            select(ParkingSpot).where(ParkingSpot.is_occupied == False).limit(1)
        )
        spot = result.scalar_one()
        
        session = ParkingSession(
            vehicle_id=sample_vehicle.id,
            parking_spot_id=spot.id,
            entry_time=datetime.utcnow(),
            hourly_rate=5.0
        )
        db_session.add(session)
        await db_session.commit()
        
        assert session.id is not None
        assert session.exit_time is None
        assert session.amount_paid is None
        assert session.payment_status == "pending"
    
    async def test_read_parking_session_with_relationships(self, sample_parking_session, db_session):
        """Test reading a parking session with its relationships."""
        result = await db_session.execute(
            select(ParkingSession).where(ParkingSession.id == sample_parking_session.id)
        )
        session = result.scalar_one()
        
        # Load relationships
        await db_session.refresh(session, ["vehicle", "parking_spot"])
        
        assert session.vehicle.license_plate == "ABC123"
        assert session.parking_spot.spot_number == "1-01"
    
    async def test_update_parking_session_on_exit(self, sample_parking_session, db_session):
        """Test updating a parking session when vehicle exits."""
        exit_time = sample_parking_session.entry_time + timedelta(hours=2.5)
        
        sample_parking_session.exit_time = exit_time
        sample_parking_session.amount_paid = 12.50  # 2.5 hours * 5.0
        sample_parking_session.payment_status = "paid"
        
        await db_session.commit()
        
        # Verify updates
        result = await db_session.execute(
            select(ParkingSession).where(ParkingSession.id == sample_parking_session.id)
        )
        updated_session = result.scalar_one()
        
        assert updated_session.exit_time is not None
        assert updated_session.amount_paid == 12.50
        assert updated_session.payment_status == "paid"
    
    async def test_duration_hours_property(self, sample_parking_session, db_session):
        """Test the duration_hours property calculation."""
        # Set exit time 3 hours after entry
        sample_parking_session.exit_time = sample_parking_session.entry_time + timedelta(hours=3)
        await db_session.commit()
        
        assert sample_parking_session.duration_hours == pytest.approx(3.0, 0.01)
    
    async def test_calculate_amount_property(self, sample_parking_session, db_session):
        """Test the calculate_amount property."""
        # Set exit time 2.5 hours after entry
        sample_parking_session.exit_time = sample_parking_session.entry_time + timedelta(hours=2.5)
        await db_session.commit()
        
        expected_amount = 2.5 * sample_parking_session.hourly_rate
        assert sample_parking_session.calculate_amount == expected_amount
    
    async def test_query_active_sessions(self, db_session, sample_vehicle, init_parking_spots):
        """Test querying active parking sessions."""
        # Create multiple sessions
        spots = await db_session.execute(
            select(ParkingSpot).where(ParkingSpot.is_occupied == False).limit(3)
        )
        spots = spots.scalars().all()
        
        # Create 2 active and 1 completed session
        for i, spot in enumerate(spots):
            session = ParkingSession(
                vehicle_id=sample_vehicle.id,
                parking_spot_id=spot.id,
                entry_time=datetime.utcnow() - timedelta(hours=i)
            )
            if i == 2:  # Complete the third session
                session.exit_time = datetime.utcnow()
                session.payment_status = "paid"
            
            db_session.add(session)
        
        await db_session.commit()
        
        # Query active sessions
        result = await db_session.execute(
            select(ParkingSession).where(ParkingSession.exit_time.is_(None))
        )
        active_sessions = result.scalars().all()
        
        # Should have 2 active sessions (2 created, fixture creates one but occupies the spot)
        assert len(active_sessions) == 2
        assert all(session.exit_time is None for session in active_sessions)


@pytest.fixture(scope="function")
def init_db_fixture():
    """Fixture to set up and tear down a clean in-memory database for init_db tests."""
    # Temporarily override DATABASE_URL to ensure in-memory db for init_db
    original_db_url = os.getenv("DATABASE_URL")
    original_async_db_url = os.getenv("ASYNC_DATABASE_URL")
    
    # Use a temporary file for the test database to trigger the absolute path logic
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
    os.environ["ASYNC_DATABASE_URL"] = f"sqlite+aiosqlite:///{test_db_path}"

    # Import database.database here to ensure it picks up the patched environment variables
    # and re-initializes its global engine variables.
    import src.infrastructure.persistence.database as database
    import importlib
    importlib.reload(database)

    # Ensure tables are dropped before each test run
    database.Base.metadata.drop_all(database.engine)

    yield database.engine # Yield the engine for inspection

    # Clean up after test
    database.Base.metadata.drop_all(database.engine)
    
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        del os.environ["DATABASE_URL"]
    
    if original_async_db_url:
        os.environ["ASYNC_DATABASE_URL"] = original_async_db_url
    else:
        del os.environ["ASYNC_DATABASE_URL"]
    
    # Reload database.database again to restore original settings
    importlib.reload(database)


class TestDatabaseFunctions:
    """Tests for functions in src/database/database.py."""

    def test_init_db_creates_tables_and_spots(self, init_db_fixture):
        """Test that init_db creates all tables and initial parking spots."""
        engine = init_db_fixture
        
        # Call init_db
        init_db()
        
        # Verify tables exist
        inspector = inspect(engine)
        assert inspector.has_table("vehicles")
        assert inspector.has_table("parking_spots")
        assert inspector.has_table("parking_sessions")
        
        # Verify initial parking spots are created
        from sqlalchemy.orm import Session
        with Session(engine) as session:
            spot_count = session.query(ParkingSpot).count()
            assert spot_count == 60 # 3 floors * 20 spots
