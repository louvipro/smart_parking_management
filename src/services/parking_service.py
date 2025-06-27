from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, Integer
from datetime import datetime, timedelta
from typing import Optional, List
from loguru import logger

from database.models import Vehicle, ParkingSpot, ParkingSession
from schemas.parking import (
    VehicleEntry, VehicleExit, PaymentInfo, ParkingStatus,
    ParkingSessionResponse, SpotType, PaymentStatus
)


class ParkingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_vehicle_entry(self, vehicle_data: VehicleEntry) -> ParkingSessionResponse:
        async with self.db.begin():
            # Check if vehicle already in parking
            active_session = await self.db.execute(
                select(ParkingSession).join(Vehicle).where(
                    and_(
                        Vehicle.license_plate == vehicle_data.license_plate,
                        ParkingSession.exit_time.is_(None)
                    )
                )
            )
            existing_session = active_session.first()
            if existing_session:
                raise ValueError(f"Vehicle {vehicle_data.license_plate} is already in the parking")

            # Find or create vehicle
            vehicle_result = await self.db.execute(
                select(Vehicle).where(Vehicle.license_plate == vehicle_data.license_plate)
            )
            vehicles = vehicle_result.scalars().all()
            vehicle = vehicles[0] if vehicles else None
            
            if not vehicle:
                vehicle = Vehicle(
                    license_plate=vehicle_data.license_plate,
                    color=vehicle_data.color,
                    brand=vehicle_data.brand
                )
                self.db.add(vehicle)
                await self.db.flush()

            # Find available parking spot
            spot_query = select(ParkingSpot).where(
                and_(
                    ParkingSpot.is_occupied == False,
                    ParkingSpot.spot_type == vehicle_data.spot_type
                )
            ).order_by(ParkingSpot.floor, ParkingSpot.spot_number)
            
            result = await self.db.execute(spot_query)
            spots = result.scalars().all()
            available_spot = spots[0] if spots else None
            
            if not available_spot:
                raise ValueError(f"No available {vehicle_data.spot_type} spots")

            # Create parking session
            session = ParkingSession(
                vehicle_id=vehicle.id,
                parking_spot_id=available_spot.id,
                entry_time=datetime.utcnow()
            )
            self.db.add(session)
            
            # Mark spot as occupied
            available_spot.is_occupied = True
            
            await self.db.flush()
            await self.db.refresh(session)
            
            # Load relationships
            await self.db.refresh(session, ["vehicle", "parking_spot"])
            
            logger.info(f"Vehicle {vehicle_data.license_plate} entered at spot {available_spot.spot_number}")
            return ParkingSessionResponse.model_validate(session)

    async def register_vehicle_exit(self, exit_data: VehicleExit) -> PaymentInfo:
        async with self.db.begin():
            # Find active session
            result = await self.db.execute(
                select(ParkingSession).join(Vehicle).where(
                    and_(
                        Vehicle.license_plate == exit_data.license_plate,
                        ParkingSession.exit_time.is_(None)
                    )
                ).order_by(ParkingSession.entry_time.desc())
            )
            sessions = result.scalars().all()
            session = sessions[0] if sessions else None
            
            if not session:
                raise ValueError(f"No active session for vehicle {exit_data.license_plate}")

            # Calculate payment
            session.exit_time = datetime.utcnow()
            duration_hours = (session.exit_time - session.entry_time).total_seconds() / 3600
            
            # Minimum charge for 1 hour
            duration_hours = max(1.0, duration_hours)
            session.amount_paid = round(duration_hours * session.hourly_rate, 2)
            session.payment_status = PaymentStatus.PAID

            # Free up parking spot
            spot = await self.db.get(ParkingSpot, session.parking_spot_id)
            spot.is_occupied = False
            
            await self.db.flush()
            
            # Load vehicle for response
            vehicle = await self.db.get(Vehicle, session.vehicle_id)
            
            logger.info(f"Vehicle {exit_data.license_plate} exited. Amount: ${session.amount_paid}")
            
            return PaymentInfo(
                session_id=session.id,
                license_plate=vehicle.license_plate,
                entry_time=session.entry_time,
                exit_time=session.exit_time,
                duration_hours=round(duration_hours, 2),
                amount_due=session.amount_paid,
                spot_number=spot.spot_number
            )

    async def get_parking_status(self) -> ParkingStatus:
        # Total spots
        total_result = await self.db.execute(select(func.count(ParkingSpot.id)))
        total_spots = total_result.scalar()
        
        # Occupied spots
        occupied_result = await self.db.execute(
            select(func.count(ParkingSpot.id)).where(ParkingSpot.is_occupied == True)
        )
        occupied_spots = occupied_result.scalar()
        
        # Floor breakdown
        floor_stats = await self.db.execute(
            select(
                ParkingSpot.floor,
                func.count(ParkingSpot.id).label('total'),
                func.sum(func.cast(ParkingSpot.is_occupied, Integer)).label('occupied')
            ).group_by(ParkingSpot.floor).order_by(ParkingSpot.floor)
        )
        
        floors = []
        for row in floor_stats:
            floors.append({
                "floor": row.floor,
                "total": row.total,
                "occupied": row.occupied or 0,
                "available": row.total - (row.occupied or 0)
            })
        
        available_spots = total_spots - occupied_spots
        occupancy_rate = (occupied_spots / total_spots * 100) if total_spots > 0 else 0
        
        return ParkingStatus(
            total_spots=total_spots,
            occupied_spots=occupied_spots,
            available_spots=available_spots,
            occupancy_rate=round(occupancy_rate, 2),
            floors=floors
        )

    async def get_active_sessions(self) -> List[ParkingSessionResponse]:
        result = await self.db.execute(
            select(ParkingSession)
            .where(ParkingSession.exit_time.is_(None))
            .order_by(ParkingSession.entry_time.desc())
        )
        sessions = result.scalars().all()
        
        # Load relationships
        for session in sessions:
            await self.db.refresh(session, ["vehicle", "parking_spot"])
        
        return [ParkingSessionResponse.model_validate(s) for s in sessions]

    async def get_vehicle_by_plate(self, license_plate: str) -> Optional[Vehicle]:
        result = await self.db.execute(
            select(Vehicle).where(Vehicle.license_plate == license_plate.upper())
        )
        vehicles = result.scalars().all()
        return vehicles[0] if vehicles else None