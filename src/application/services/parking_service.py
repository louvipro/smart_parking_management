from datetime import datetime, timezone
from typing import Optional, List, Dict
from loguru import logger

from src.application.repositories import AbstractVehicleRepository, AbstractParkingSpotRepository, AbstractParkingSessionRepository
from src.domain.common import SpotType, PaymentStatus
from src.domain.entities import Vehicle, ParkingSession


class ParkingService:
    def __init__(
        self,
        vehicle_repo: AbstractVehicleRepository,
        parking_spot_repo: AbstractParkingSpotRepository,
        parking_session_repo: AbstractParkingSessionRepository
    ):
        self.vehicle_repo = vehicle_repo
        self.parking_spot_repo = parking_spot_repo
        self.parking_session_repo = parking_session_repo

    async def register_vehicle_entry(self, license_plate: str, color: str, brand: str, spot_type: SpotType) -> ParkingSession:
        # Check if vehicle already in parking
        existing_session = await self.parking_session_repo.get_active_session_by_license_plate(license_plate)
        if existing_session:
            raise ValueError(f"Vehicle {license_plate} is already in the parking")

        # Find or create vehicle
        vehicle = await self.vehicle_repo.get_by_license_plate(license_plate)
        
        if not vehicle:
            vehicle = Vehicle(
                license_plate=license_plate,
                color=color,
                brand=brand
            )
            vehicle = await self.vehicle_repo.add(vehicle)

        # Find available parking spot
        available_spot = await self.parking_spot_repo.get_available_spot(spot_type)
        
        if not available_spot:
            raise ValueError(f"No available {spot_type} spots")

        # Create parking session
        session = ParkingSession(
            vehicle_id=vehicle.id,
            parking_spot_id=available_spot.id,
            entry_time=datetime.now(timezone.utc),
            hourly_rate=5.0 # Assuming a default hourly rate for now, this should come from somewhere else
        )
        
        # The add method now returns a complete session with vehicle and spot
        new_session = await self.parking_session_repo.add(session)
        
        # Mark spot as occupied
        available_spot.is_occupied = True
        await self.parking_spot_repo.update(available_spot)
        
        logger.info(f"Vehicle {license_plate} entered at spot {new_session.parking_spot.spot_number}")
        return new_session

    async def register_vehicle_exit(self, license_plate: str) -> ParkingSession:
        # Find active session
        session = await self.parking_session_repo.get_active_session_by_license_plate(license_plate)
        
        if not session:
            raise ValueError(f"No active session for vehicle {license_plate}")

        # Calculate payment
        session.exit_time = datetime.now(timezone.utc)
        # Ensure both datetimes are timezone-aware before subtraction
        entry_time_aware = session.entry_time.replace(tzinfo=timezone.utc) if session.entry_time.tzinfo is None else session.entry_time
        exit_time_aware = session.exit_time.replace(tzinfo=timezone.utc) if session.exit_time.tzinfo is None else session.exit_time
        duration_hours = (exit_time_aware - entry_time_aware).total_seconds() / 3600
        
        # Minimum charge for 1 hour
        duration_hours = max(1.0, duration_hours)
        duration_hours = max(1.0, duration_hours)
        session.amount_paid = round(duration_hours * session.hourly_rate, 2)
        session.payment_status = PaymentStatus.PAID

        # Free up parking spot
        spot = await self.parking_spot_repo.get_by_id(session.parking_spot_id)
        if spot: # Ensure spot exists before updating
            spot.is_occupied = False
            await self.parking_spot_repo.update(spot)
        
        session = await self.parking_session_repo.update(session)
        
        logger.info(f"Vehicle {license_plate} exited. Amount: ${session.amount_paid}")
        return session

    async def get_parking_status(self) -> Dict:
        all_spots = await self.parking_spot_repo.get_all()
        total_spots = len(all_spots)
        
        occupied_spots_list = [spot for spot in all_spots if spot.is_occupied]
        occupied_spots = len(occupied_spots_list)
        
        # Floor breakdown
        floor_stats = {}
        for spot in all_spots:
            if spot.floor not in floor_stats:
                floor_stats[spot.floor] = {"total": 0, "occupied": 0}
            floor_stats[spot.floor]["total"] += 1
            if spot.is_occupied:
                floor_stats[spot.floor]["occupied"] += 1
        
        floors = []
        for floor_num in sorted(floor_stats.keys()):
            stats = floor_stats[floor_num]
            floors.append({
                "floor": floor_num,
                "total": stats["total"],
                "occupied": stats["occupied"],
                "available": stats["total"] - stats["occupied"]
            })
        
        available_spots = total_spots - occupied_spots
        occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0
        
        return {
            "total_spots": total_spots,
            "occupied_spots": occupied_spots,
            "available_spots": available_spots,
            "occupancy_rate": round(occupancy_rate, 2),
            "floors": floors
        }

    async def get_active_sessions(self) -> List[ParkingSession]:
        sessions = await self.parking_session_repo.get_active_sessions()
        
        return sessions

    async def get_vehicle_by_plate(self, license_plate: str) -> Optional[Vehicle]:
        return await self.vehicle_repo.get_by_license_plate(license_plate.upper())