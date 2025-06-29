import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
import tempfile
import os
from freezegun import freeze_time
from datetime import datetime, timedelta, timezone

from src.infrastructure.persistence.models.models import Base
from src.infrastructure.persistence.sqlalchemy_repositories.sqlalchemy_repositories import SQLAlchemyVehicleRepository, SQLAlchemyParkingSpotRepository, SQLAlchemyParkingSessionRepository
from src.application.services.parking_service import ParkingService
from src.application.services.analytics_service import AnalyticsService
from src.config.settings_env import Settings


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
    from src.infrastructure.persistence.models.models import ParkingSpot
    
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
    from src.infrastructure.persistence.models.models import Vehicle
    
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
    from src.infrastructure.persistence.models.models import ParkingSession, ParkingSpot
    from datetime import datetime, timezone
    
    # Get the first available spot
    spot = await db_session.get(ParkingSpot, 1)
    spot.is_occupied = True
    
    session = ParkingSession(
        vehicle_id=sample_vehicle.id,
        parking_spot_id=spot.id,
        entry_time=datetime.now(timezone.utc),
        hourly_rate=5.0
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session

@pytest.fixture
async def parked_vehicle(parking_service, init_parking_spots):
    """Create a vehicle that's already parked."""
    with freeze_time(datetime.now(timezone.utc) - timedelta(hours=2)):
        session_response = await parking_service.register_vehicle_entry(
            license_plate="PARKED123",
            color="Silver",
            brand="Mercedes",
            spot_type=SpotType.REGULAR
        )
    return session_response

@pytest.fixture
async def parking_service(db_session):
    """Create a ParkingService instance with test database session."""
    vehicle_repo = SQLAlchemyVehicleRepository(db_session)
    parking_spot_repo = SQLAlchemyParkingSpotRepository(db_session)
    parking_session_repo = SQLAlchemyParkingSessionRepository(db_session)
    return ParkingService(
        vehicle_repo=vehicle_repo,
        parking_spot_repo=parking_spot_repo,
        parking_session_repo=parking_session_repo
    )

@pytest.fixture
async def analytics_service(db_session):
    """Create an AnalyticsService instance with test database session."""
    vehicle_repo = SQLAlchemyVehicleRepository(db_session)
    parking_spot_repo = SQLAlchemyParkingSpotRepository(db_session)
    parking_session_repo = SQLAlchemyParkingSessionRepository(db_session)
    return AnalyticsService(
        vehicle_repo=vehicle_repo,
        parking_spot_repo=parking_spot_repo,
        parking_session_repo=parking_session_repo
    )

@pytest.fixture
async def empty_db_for_analytics(db_session):
    """Provides an analytics service with an empty database."""
    vehicle_repo = SQLAlchemyVehicleRepository(db_session)
    parking_spot_repo = SQLAlchemyParkingSpotRepository(db_session)
    parking_session_repo = SQLAlchemyParkingSessionRepository(db_session)
    return AnalyticsService(
        vehicle_repo=vehicle_repo,
        parking_spot_repo=parking_spot_repo,
        parking_session_repo=parking_session_repo
    )