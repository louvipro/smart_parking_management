#!/usr/bin/env python3
"""Check for duplicate vehicles in the database"""
import os
import sys
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.models import Vehicle

DATABASE_URL = "sqlite:///parking.db"
engine = create_engine(DATABASE_URL)

def check_duplicates():
    with Session(engine) as session:
        # Count all vehicles
        total = session.query(Vehicle).count()
        print(f"Total vehicles: {total}")
        
        # Find duplicates
        duplicates = session.execute(
            select(Vehicle.license_plate, func.count(Vehicle.id).label('count'))
            .group_by(Vehicle.license_plate)
            .having(func.count(Vehicle.id) > 1)
        ).all()
        
        if duplicates:
            print("\nDuplicate license plates found:")
            for plate, count in duplicates:
                print(f"  {plate}: {count} entries")
                
                # Show the duplicate entries
                vehicles = session.query(Vehicle).filter(Vehicle.license_plate == plate).all()
                for v in vehicles:
                    print(f"    ID: {v.id}, Color: {v.color}, Brand: {v.brand}")
        else:
            print("No duplicate vehicles found")

if __name__ == "__main__":
    check_duplicates()