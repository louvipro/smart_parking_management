#!/usr/bin/env python3
"""Check database content"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from database.models import Base, ParkingSession

DATABASE_URL = "sqlite:///./parking.db"
if os.path.exists("parking.db"):
    db_path = os.path.abspath("parking.db")
    DATABASE_URL = f"sqlite:///{db_path}"

engine = create_engine(DATABASE_URL)

# Check parking sessions
with engine.connect() as conn:
    result = conn.execute(text("SELECT id, entry_time, exit_time, amount_paid, payment_status, hourly_rate FROM parking_sessions"))
    sessions = result.fetchall()
    
    print("=== Parking Sessions ===")
    for session in sessions:
        print(f"ID: {session[0]}, Entry: {session[1]}, Exit: {session[2]}, Amount: {session[3]}, Status: {session[4]}, Rate: {session[5]}")
    
    if not sessions:
        print("No parking sessions found")
    
    # Check for completed sessions with null amount
    result = conn.execute(text("SELECT COUNT(*) FROM parking_sessions WHERE exit_time IS NOT NULL AND (amount_paid IS NULL OR amount_paid = 0)"))
    count = result.scalar()
    print(f"\nCompleted sessions with null/zero amount: {count}")