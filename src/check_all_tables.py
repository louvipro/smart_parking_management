#!/usr/bin/env python3
"""Check all tables in the parking database"""
import sqlite3
from datetime import datetime

# Connect to the database
conn = sqlite3.connect('parking.db')
cursor = conn.cursor()

print("=== VEHICLES TABLE ===")
cursor.execute("SELECT * FROM vehicles")
vehicles = cursor.fetchall()
cursor.execute("PRAGMA table_info(vehicles)")
vehicle_cols = [col[1] for col in cursor.fetchall()]
print(f"Columns: {', '.join(vehicle_cols)}")
for vehicle in vehicles:
    print(vehicle)

print("\n=== PARKING SPOTS TABLE ===")
cursor.execute("SELECT * FROM parking_spots")
spots = cursor.fetchall()
cursor.execute("PRAGMA table_info(parking_spots)")
spot_cols = [col[1] for col in cursor.fetchall()]
print(f"Columns: {', '.join(spot_cols)}")
for spot in spots:
    print(spot)

# Calculate parking duration for active sessions
print("\n=== PARKING DURATION ANALYSIS ===")
cursor.execute("""
    SELECT 
        ps.id,
        v.license_plate,
        ps.entry_time,
        ps.hourly_rate,
        sp.spot_number,
        sp.floor
    FROM parking_sessions ps
    LEFT JOIN vehicles v ON ps.vehicle_id = v.id
    LEFT JOIN parking_spots sp ON ps.parking_spot_id = sp.id
    WHERE ps.exit_time IS NULL
""")
active_sessions = cursor.fetchall()

now = datetime.now()
print("Active sessions with parking duration:")
for session in active_sessions:
    session_id, license_plate, entry_time_str, hourly_rate, spot_number, floor = session
    entry_time = datetime.fromisoformat(entry_time_str)
    duration = now - entry_time
    hours = duration.total_seconds() / 3600
    estimated_cost = hours * hourly_rate
    
    print(f"\nSession ID {session_id}:")
    print(f"  - Vehicle: {license_plate}")
    print(f"  - Spot: {spot_number} (Floor {floor})")
    print(f"  - Entry: {entry_time_str}")
    print(f"  - Duration: {int(duration.total_seconds() // 3600)}h {int((duration.total_seconds() % 3600) // 60)}m")
    print(f"  - Estimated cost: ${estimated_cost:.2f} (at ${hourly_rate}/hour)")

conn.close()