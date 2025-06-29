from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
import os

from src.infrastructure.persistence.models.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./parking.db")
ASYNC_DATABASE_URL = os.getenv(
    "ASYNC_DATABASE_URL", "sqlite+aiosqlite:///./parking.db")

# Ensure we're using absolute paths for SQLite
if "sqlite" in DATABASE_URL:
    db_path = os.path.abspath("parking.db")
    DATABASE_URL = f"sqlite:///{db_path}"
    ASYNC_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

# Sync engine for initialization
engine = create_engine(DATABASE_URL, connect_args={
                       "check_same_thread": False} if "sqlite" in DATABASE_URL else {})

# Async engine for application
async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def init_db():
    print(f"Initializing database at: {DATABASE_URL}")
    Base.metadata.create_all(bind=engine, checkfirst=True)
    print("Tables created")

    # Create initial parking spots
    from sqlalchemy.orm import Session
    from src.infrastructure.persistence.models.models import ParkingSpot

    with Session(engine) as session:
        # Check if spots already exist
        existing_spots = session.query(ParkingSpot).count()
        if existing_spots == 0:
            # Create 3 floors with 20 spots each
            for floor in range(1, 4):
                for spot_num in range(1, 21):
                    spot_number = f"{floor}-{spot_num:02d}"
                    spot_type = "disabled" if spot_num <= 2 else "vip" if spot_num <= 5 else "regular"
                    spot = ParkingSpot(
                        spot_number=spot_number,
                        floor=floor,
                        spot_type=spot_type,
                        is_occupied=False
                    )
                    session.add(spot)
            session.commit()
            print(f"Created {3 * 20} parking spots")
