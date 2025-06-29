import pytest
import sqlite3
import os
import tempfile
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.infrastructure.persistence.models.models import Base, Vehicle, ParkingSpot, ParkingSession
from subprocess import run, PIPE

@pytest.fixture(scope="function")
def setup_temp_db_for_check_all_tables():
    # Create a temporary file for the test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    # Set the DATABASE_URL environment variable to point to the temporary database
    # This is crucial for the script to connect to our test database
    original_db_url = os.getenv("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

    # Create a SQLAlchemy engine and session for populating the test database
    engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Populate with test data
    # Vehicle 1: Parked
    vehicle1 = Vehicle(license_plate="TEST001", color="Red", brand="Toyota")
    session.add(vehicle1)
    session.commit()
    session.refresh(vehicle1)

    spot1 = ParkingSpot(spot_number="A1", floor=1, spot_type="regular", is_occupied=True)
    session.add(spot1)
    session.commit()
    session.refresh(spot1)

    entry_time1 = datetime.now(timezone.utc) - timedelta(hours=2, minutes=30)
    session1 = ParkingSession(
        vehicle_id=vehicle1.id,
        parking_spot_id=spot1.id,
        entry_time=entry_time1,
        hourly_rate=5.0
    )
    session.add(session1)
    session.commit()
    session.refresh(session1)

    # Vehicle 2: Not parked (no active session)
    vehicle2 = Vehicle(license_plate="TEST002", color="Blue", brand="Honda")
    session.add(vehicle2)
    session.commit()
    session.refresh(vehicle2)

    # Vehicle 3: Parked and exited
    vehicle3 = Vehicle(license_plate="TEST003", color="Green", brand="BMW")
    session.add(vehicle3)
    session.commit()
    session.refresh(vehicle3)

    spot3 = ParkingSpot(spot_number="B1", floor=2, spot_type="regular", is_occupied=False)
    session.add(spot3)
    session.commit()
    session.refresh(spot3)

    entry_time3 = datetime.now(timezone.utc) - timedelta(hours=5)
    exit_time3 = datetime.now(timezone.utc) - timedelta(hours=3)
    session3 = ParkingSession(
        vehicle_id=vehicle3.id,
        parking_spot_id=spot3.id,
        entry_time=entry_time3,
        exit_time=exit_time3,
        hourly_rate=5.0,
        amount_paid=10.0,
        payment_status="paid"
    )
    session.add(session3)
    session.commit()
    session.refresh(session3)

    session.close()

    yield test_db_path, entry_time1 # Yield the path and entry time for assertions

    # Clean up: close connection and delete the temporary file
    engine.dispose()
    os.unlink(test_db_path)
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        del os.environ["DATABASE_URL"]

def test_check_all_tables_script_output(setup_temp_db_for_check_all_tables):
    db_path, entry_time1 = setup_temp_db_for_check_all_tables

    # Run the script as a subprocess and capture its output
    # We need to ensure the script uses the temporary database
    # by setting the DATABASE_URL env var for the subprocess
    script_path = os.path.abspath("src/check_all_tables.py")
    
    # Set the DATABASE_URL environment variable for the subprocess
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    
    result = run(["python", script_path], capture_output=True, text=True, env=env)

    # Assertions
    assert result.returncode == 0
    output = result.stdout

    # Verify VEHICLES TABLE output
    assert "=== VEHICLES TABLE ===" in output
    assert "TEST001" in output
    assert "TEST002" in output
    assert "TEST003" in output

    # Verify PARKING SPOTS TABLE output
    assert "=== PARKING SPOTS TABLE ===" in output
    assert "A1" in output
    assert "B1" in output

    # Verify PARKING DURATION ANALYSIS output
    assert "=== PARKING DURATION ANALYSIS ===" in output
    assert "Active sessions with parking duration:" in output
    assert "Session ID 1:" in output
    assert "- Vehicle: TEST001" in output
    assert "- Spot: A1 (Floor 1)" in output
    assert f"- Entry: {entry_time1.isoformat()}" in output # Check entry time format
    assert "- Duration: 2h 30m" in output # Approximate duration
    assert "- Estimated cost: $12.50" in output # 2.5 hours * 5.0 hourly rate

    # Ensure exited vehicle is not in active sessions
    assert "TEST003" not in output.split("Active sessions")[1]
