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
def setup_temp_db_for_check_db():
    # Create a temporary file for the test database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        test_db_path = tmp_file.name
    
    # Set the DATABASE_URL environment variable to point to the temporary database
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
    session.expunge(session1) # Detach from session

    # Vehicle 2: Parked and exited
    vehicle2 = Vehicle(license_plate="TEST002", color="Blue", brand="Honda")
    session.add(vehicle2)
    session.commit()
    session.refresh(vehicle2)

    spot2 = ParkingSpot(spot_number="B1", floor=2, spot_type="regular", is_occupied=False)
    session.add(spot2)
    session.commit()
    session.refresh(spot2)

    entry_time2 = datetime.now(timezone.utc) - timedelta(hours=5)
    exit_time2 = datetime.now(timezone.utc) - timedelta(hours=3)
    session2 = ParkingSession(
        vehicle_id=vehicle2.id,
        parking_spot_id=spot2.id,
        entry_time=entry_time2,
        exit_time=exit_time2,
        hourly_rate=5.0,
        amount_paid=10.0,
        payment_status="paid"
    )
    session.add(session2)
    session.commit()
    session.refresh(session2)
    session.expunge(session2) # Detach from session

    # Vehicle 3: Completed session with null amount
    vehicle3 = Vehicle(license_plate="TEST003", color="Green", brand="BMW")
    session.add(vehicle3)
    session.commit()
    session.refresh(vehicle3)

    spot3 = ParkingSpot(spot_number="C1", floor=3, spot_type="regular", is_occupied=False)
    session.add(spot3)
    session.commit()
    session.refresh(spot3)

    entry_time3 = datetime.now(timezone.utc) - timedelta(hours=1)
    exit_time3 = datetime.now(timezone.utc) - timedelta(minutes=30)
    session3 = ParkingSession(
        vehicle_id=vehicle3.id,
        parking_spot_id=spot3.id,
        entry_time=entry_time3,
        exit_time=exit_time3,
        hourly_rate=5.0,
        amount_paid=None,
        payment_status="pending"
    )
    session.add(session3)
    session.commit()
    session.refresh(session3)
    session.expunge(session3) # Detach from session

    session.close()

    yield test_db_path, session1.to_dict(), session2.to_dict(), session3.to_dict() # Yield the path and sessions for assertions

    # Clean up: close connection and delete the temporary file
    engine.dispose()
    os.unlink(test_db_path)
    if original_db_url:
        os.environ["DATABASE_URL"] = original_db_url
    else:
        del os.environ["DATABASE_URL"]

def test_check_db_script_output(setup_temp_db_for_check_db):
    db_path, session1, session2, session3 = setup_temp_db_for_check_db

    # Run the script as a subprocess and capture its output
    script_path = os.path.abspath("src/check_db.py")
    
    # Set the DATABASE_URL environment variable for the subprocess
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["PYTHONPATH"] = os.path.abspath(".")
    
    result = run(["python", script_path], capture_output=True, text=True, env=env)

    # Assertions
    assert result.returncode == 0
    output = result.stdout

    # Verify Parking Sessions section
    assert "=== Parking Sessions ===" in output
    assert f"ID: {session1['id']}, Entry: {session1['entry_time'].isoformat()}, Exit: None, Amount: None, Status: pending, Rate: 5.0\}}" in output
    assert f"ID: {session2['id']}, Entry: {session2['entry_time'].isoformat()}, Exit: {session2['exit_time'].isoformat()}, Amount: 10.0, Status: paid, Rate: 5.0\}}" in output
    assert f"ID: {session3['id']}, Entry: {session3['entry_time'].isoformat()}, Exit: {session3['exit_time'].isoformat()}, Amount: None, Status: pending, Rate: 5.0\}}" in output

    # Verify completed sessions with null/zero amount
    assert "Completed sessions with null/zero amount: 1" in output

def test_check_db_no_sessions_output(setup_temp_db_for_check_db):
    db_path, _, _, _ = setup_temp_db_for_check_db

    # Clear all sessions from the database
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    session = Session()
    session.query(ParkingSession).delete()
    session.commit()
    session.close()
    engine.dispose()

    # Run the script as a subprocess and capture its output
    script_path = os.path.abspath("src/check_db.py")
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["PYTHONPATH"] = os.path.abspath(".")
    result = run(["python", script_path], capture_output=True, text=True, env=env)

    # Assertions
    assert result.returncode == 0
    output = result.stdout
    assert "No parking sessions found" in output
    assert "Completed sessions with null/zero amount: 0" in output
