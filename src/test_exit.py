#!/usr/bin/env python3
"""Test vehicle exit to generate revenue"""
import os
import sys
import asyncio

# Set working directory to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, 'src')

from database.database import AsyncSessionLocal
from services.parking_service import ParkingService
from schemas.parking import VehicleExit

async def test_exit():
    """Exit the first vehicle to generate revenue"""
    # Get active sessions first
    async with AsyncSessionLocal() as db:
        service = ParkingService(db)
        sessions = await service.get_active_sessions()
        if not sessions:
            print("No active sessions found")
            return
        
        # Exit the first vehicle
        first_session = sessions[0]
        print(f"Exiting vehicle: {first_session.vehicle.license_plate}")
    
    # Register exit in a new session
    async with AsyncSessionLocal() as db:
        service = ParkingService(db)
        exit_data = VehicleExit(license_plate=first_session.vehicle.license_plate)
        payment = await service.register_vehicle_exit(exit_data)
        
        print(f"Exit successful!")
        print(f"Duration: {payment.duration_hours} hours")
        print(f"Amount paid: ${payment.amount_due}")
    
    # Check analytics in another session
    async with AsyncSessionLocal() as db:
        from services.analytics_service import AnalyticsService
        analytics_service = AnalyticsService(db)
        analytics = await analytics_service.get_parking_analytics()
        
        print(f"\nToday's revenue: ${analytics['today_revenue']}")

if __name__ == "__main__":
    asyncio.run(test_exit())