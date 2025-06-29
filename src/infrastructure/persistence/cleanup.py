"""Database cleanup script to remove duplicates."""
from sqlalchemy import create_engine, select, func, update
from sqlalchemy.orm import Session
from src.infrastructure.persistence.models.models import Vehicle, ParkingSession

DATABASE_URL = "sqlite:///./parking.db"
engine = create_engine(DATABASE_URL)

def cleanup_duplicates():
    with Session(engine) as session:
        # Find duplicate vehicles
        duplicates = session.execute(
            select(Vehicle.license_plate)
            .group_by(Vehicle.license_plate)
            .having(func.count(Vehicle.id) > 1)
        ).scalars().all()
        
        for license_plate in duplicates:
            # Keep only the first vehicle
            vehicles = session.execute(
                select(Vehicle)
                .where(Vehicle.license_plate == license_plate)
                .order_by(Vehicle.id)
            ).scalars().all()
            
            # Delete all but the first
            for vehicle in vehicles[1:]:
                # Update sessions to point to the first vehicle
                session.execute(
                    update(ParkingSession)
                    .where(ParkingSession.vehicle_id == vehicle.id)
                    .values(vehicle_id=vehicles[0].id)
                )
                # Delete the duplicate vehicle
                session.delete(vehicle)
        
        session.commit()
        print(f"Cleaned up {len(duplicates)} duplicate vehicles")

if __name__ == "__main__":
    cleanup_duplicates()