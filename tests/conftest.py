import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import tempfile
import os

from database.models import Base
from settings_env import Settings


# Event loop fixture removed - pytest-asyncio provides it automatically


@pytest.fixture(scope="function")
async def test_db():
    """Create a test database for each test function."""
    # Create a temporary file for the test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    # Create async engine with NullPool to avoid connection issues
    test_db_url = f"sqlite+aiosqlite:///{test_db_path}"
    engine = create_async_engine(
        test_db_url,
        poolclass=NullPool,
        echo=False
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Yield the session factory
    yield async_session_maker
    
    # Cleanup
    await engine.dispose()
    os.unlink(test_db_path)


@pytest.fixture
async def db_session(test_db):
    """Create a database session for a test."""
    async with test_db() as session:
        yield session
        await session.rollback()


@pytest.fixture
def test_settings():
    """Provide test settings."""
    return Settings(
        DATABASE_URL=f"sqlite:///:memory:",
        ASYNC_DATABASE_URL=f"sqlite+aiosqlite:///:memory:",
        HOURLY_RATE=5.0,
        PARKING_FLOORS=3,
        SPOTS_PER_FLOOR=20
    )


@pytest.fixture
async def init_parking_spots(db_session: AsyncSession):
    """Initialize parking spots for testing."""
    from database.models import ParkingSpot
    
    # Create test parking spots
    spots = []
    for floor in range(1, 4):
        for spot_num in range(1, 6):  # Only 5 spots per floor for testing
            spot_number = f"{floor}-{spot_num:02d}"
            spot_type = "disabled" if spot_num == 1 else "vip" if spot_num == 2 else "regular"
            spot = ParkingSpot(
                spot_number=spot_number,
                floor=floor,
                spot_type=spot_type,
                is_occupied=False
            )
            spots.append(spot)
            db_session.add(spot)
    
    await db_session.commit()
    return spots


@pytest.fixture
async def sample_vehicle(db_session: AsyncSession):
    """Create a sample vehicle for testing."""
    from database.models import Vehicle
    
    vehicle = Vehicle(
        license_plate="ABC123",
        color="Red",
        brand="Toyota"
    )
    db_session.add(vehicle)
    await db_session.commit()
    await db_session.refresh(vehicle)
    return vehicle


@pytest.fixture
async def sample_parking_session(db_session: AsyncSession, sample_vehicle, init_parking_spots):
    """Create a sample parking session for testing."""
    from database.models import ParkingSession, ParkingSpot
    from datetime import datetime
    
    # Get the first available spot
    spot = await db_session.get(ParkingSpot, 1)
    spot.is_occupied = True
    
    session = ParkingSession(
        vehicle_id=sample_vehicle.id,
        parking_spot_id=spot.id,
        entry_time=datetime.utcnow(),
        hourly_rate=5.0
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session