from typing import List, Optional, Dict
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract, update
from sqlalchemy.orm import selectinload

from src.domain.entities import Vehicle, ParkingSpot, ParkingSession
from src.domain.common import PaymentStatus
from src.infrastructure.persistence.models.models import Vehicle as ORMVehicle, ParkingSpot as ORMParkingSpot, ParkingSession as ORMParkingSession
from src.application.repositories import AbstractVehicleRepository, AbstractParkingSpotRepository, AbstractParkingSessionRepository


class SQLAlchemyVehicleRepository(AbstractVehicleRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_license_plate(self, license_plate: str) -> Optional[Vehicle]:
        result = await self.session.execute(
            select(ORMVehicle).where(ORMVehicle.license_plate == license_plate.upper())
        )
        orm_vehicle = result.scalars().first()
        if orm_vehicle:
            return Vehicle(
                id=orm_vehicle.id,
                license_plate=orm_vehicle.license_plate,
                color=orm_vehicle.color,
                brand=orm_vehicle.brand,
                created_at=orm_vehicle.created_at
            )
        return None

    async def add(self, vehicle: Vehicle) -> Vehicle:
        orm_vehicle = ORMVehicle(
            license_plate=vehicle.license_plate,
            color=vehicle.color,
            brand=vehicle.brand
        )
        self.session.add(orm_vehicle)
        await self.session.flush()
        await self.session.refresh(orm_vehicle)
        return Vehicle(
            id=orm_vehicle.id,
            license_plate=orm_vehicle.license_plate,
            color=orm_vehicle.color,
            brand=orm_vehicle.brand,
            created_at=orm_vehicle.created_at
        )

    async def count_by_color(self, color: str, active_only: bool = True) -> int:
        query = select(func.count(func.distinct(ORMVehicle.id))).select_from(ORMVehicle).join(ORMParkingSession)
        
        conditions = [ORMVehicle.color.ilike(f"%{color}%")]
        if active_only:
            conditions.append(ORMParkingSession.exit_time.is_(None))
        
        query = query.where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_brand_distribution(self, active_only: bool = True) -> Dict[str, int]:
        query = select(
            ORMVehicle.brand,
            func.count(func.distinct(ORMVehicle.id)).label('count')
        ).select_from(ORMVehicle).join(ORMParkingSession)
        
        if active_only:
            query = query.where(ORMParkingSession.exit_time.is_(None))
        
        query = query.group_by(ORMVehicle.brand).order_by(func.count(func.distinct(ORMVehicle.id)).desc())
        
        result = await self.session.execute(query)
        return {row.brand: row.count for row in result if row.brand}

    async def get_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        result = await self.session.execute(
            select(ORMVehicle).where(ORMVehicle.id == vehicle_id)
        )
        orm_vehicle = result.scalars().first()
        if orm_vehicle:
            return Vehicle(
                id=orm_vehicle.id,
                license_plate=orm_vehicle.license_plate,
                color=orm_vehicle.color,
                brand=orm_vehicle.brand,
                created_at=orm_vehicle.created_at
            )
        return None


class SQLAlchemyParkingSpotRepository(AbstractParkingSpotRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_available_spot(self, spot_type: str) -> Optional[ParkingSpot]:
        spot_query = select(ORMParkingSpot).where(
            and_(
                ORMParkingSpot.is_occupied == False,
                ORMParkingSpot.spot_type == spot_type
            )
        ).order_by(ORMParkingSpot.floor, ORMParkingSpot.spot_number)
        
        result = await self.session.execute(spot_query)
        orm_spot = result.scalars().first()
        if orm_spot:
            return ParkingSpot(
                id=orm_spot.id,
                spot_number=orm_spot.spot_number,
                floor=orm_spot.floor,
                spot_type=orm_spot.spot_type,
                is_occupied=orm_spot.is_occupied
            )
        return None

    async def update(self, spot: ParkingSpot) -> ParkingSpot:
        orm_spot = await self.session.get(ORMParkingSpot, spot.id)
        if orm_spot:
            orm_spot.is_occupied = spot.is_occupied
            # Update other fields if necessary
            await self.session.flush()
            await self.session.refresh(orm_spot)
            await self.session.commit()
            return ParkingSpot(
                id=orm_spot.id,
                spot_number=orm_spot.spot_number,
                floor=orm_spot.floor,
                spot_type=orm_spot.spot_type,
                is_occupied=orm_spot.is_occupied
            )
        raise ValueError(f"Parking spot with ID {spot.id} not found.")

    async def get_all(self) -> List[ParkingSpot]:
        result = await self.session.execute(select(ORMParkingSpot))
        return [
            ParkingSpot(
                id=s.id, spot_number=s.spot_number, floor=s.floor, spot_type=s.spot_type, is_occupied=s.is_occupied
            ) for s in result.scalars().all()
        ]

    async def get_by_id(self, spot_id: int) -> Optional[ParkingSpot]:
        result = await self.session.execute(
            select(ORMParkingSpot).where(ORMParkingSpot.id == spot_id)
        )
        orm_spot = result.scalars().first()
        if orm_spot:
            return ParkingSpot(
                id=orm_spot.id,
                spot_number=orm_spot.spot_number,
                floor=orm_spot.floor,
                spot_type=orm_spot.spot_type,
                is_occupied=orm_spot.is_occupied
            )
        return None

    async def get_total_spots_count(self) -> int:
        result = await self.session.execute(select(func.count(ORMParkingSpot.id)))
        return result.scalar() or 0

    async def get_occupied_spots_count(self) -> int:
        result = await self.session.execute(
            select(func.count(ORMParkingSpot.id)).where(ORMParkingSpot.is_occupied == True)
        )
        return result.scalar() or 0

    async def get_floor_distribution(self, active_only: bool = True) -> Dict[int, int]:
        query = select(
            ORMParkingSpot.floor,
            func.count(ORMParkingSession.id).label('count')
        ).select_from(ORMParkingSession).join(ORMParkingSpot)
        
        if active_only:
            query = query.where(ORMParkingSession.exit_time.is_(None))
        
        query = query.group_by(ORMParkingSpot.floor).order_by(ORMParkingSpot.floor)
        
        result = await self.session.execute(query)
        return {row.floor: row.count for row in result}

    async def update_all_occupied_by_type(self, spot_type: str, is_occupied: bool):
        await self.session.execute(
            update(ORMParkingSpot)
            .where(ORMParkingSpot.spot_type == spot_type)
            .values(is_occupied=is_occupied)
        )
        await self.session.commit()

    async def update_all_occupied(self, is_occupied: bool):
        await self.session.execute(
            update(ORMParkingSpot).values(is_occupied=is_occupied)
        )
        await self.session.commit()


class SQLAlchemyParkingSessionRepository(AbstractParkingSessionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_session_by_license_plate(self, license_plate: str) -> Optional[ParkingSession]:
        result = await self.session.execute(
            select(ORMParkingSession).join(ORMVehicle).where(
                and_(
                    ORMVehicle.license_plate == license_plate,
                    ORMParkingSession.exit_time.is_(None)
                )
            ).order_by(ORMParkingSession.entry_time.desc())
        )
        orm_session = result.scalars().first()
        if orm_session:
            # Eagerly load related vehicle and parking_spot
            await self.session.refresh(orm_session, ["vehicle", "parking_spot"])
            return ParkingSession(
                id=orm_session.id,
                vehicle_id=orm_session.vehicle_id,
                parking_spot_id=orm_session.parking_spot_id,
                entry_time=orm_session.entry_time,
                exit_time=orm_session.exit_time,
                amount_paid=orm_session.amount_paid,
                payment_status=orm_session.payment_status,
                hourly_rate=orm_session.hourly_rate,
            )
        return None

    async def add(self, session: ParkingSession) -> ParkingSession:
        orm_session = ORMParkingSession(
            vehicle_id=session.vehicle_id,
            parking_spot_id=session.parking_spot_id,
            entry_time=session.entry_time,
            hourly_rate=session.hourly_rate
        )
        self.session.add(orm_session)
        await self.session.flush()
        await self.session.refresh(orm_session)
        await self.session.commit()
        return ParkingSession(
            id=orm_session.id,
            vehicle_id=orm_session.vehicle_id,
            parking_spot_id=orm_session.parking_spot_id,
            entry_time=orm_session.entry_time,
            exit_time=orm_session.exit_time,
            amount_paid=orm_session.amount_paid,
            payment_status=orm_session.payment_status,
            hourly_rate=session.hourly_rate,
        )

    async def get_by_id(self, session_id: int) -> Optional[ParkingSession]:
        result = await self.session.execute(
            select(ORMParkingSession).where(ORMParkingSession.id == session_id)
        )
        orm_session = result.scalars().first()
        if orm_session:
            return ParkingSession(
                id=orm_session.id,
                vehicle_id=orm_session.vehicle_id,
                parking_spot_id=orm_session.parking_spot_id,
                entry_time=orm_session.entry_time,
                exit_time=orm_session.exit_time,
                amount_paid=orm_session.amount_paid,
                payment_status=orm_session.payment_status,
                hourly_rate=orm_session.hourly_rate,
            )
        return None

    async def update(self, session: ParkingSession) -> ParkingSession:
        orm_session = await self.session.get(ORMParkingSession, session.id)
        if orm_session:
            orm_session.exit_time = session.exit_time
            orm_session.amount_paid = session.amount_paid
            orm_session.payment_status = session.payment_status
            await self.session.flush()
            await self.session.refresh(orm_session)
            return ParkingSession(
                id=orm_session.id,
                vehicle_id=orm_session.vehicle_id,
                parking_spot_id=orm_session.parking_spot_id,
                entry_time=orm_session.entry_time,
                exit_time=orm_session.exit_time,
                amount_paid=orm_session.amount_paid,
                payment_status=orm_session.payment_status,
                hourly_rate=orm_session.hourly_rate,
            )
        raise ValueError(f"Parking session with ID {session.id} not found.")

    async def get_active_sessions(self) -> List[Dict]:
        result = await self.session.execute(
            select(ORMParkingSession).where(ORMParkingSession.exit_time.is_(None))
            .options(selectinload(ORMParkingSession.vehicle), selectinload(ORMParkingSession.parking_spot))
            .order_by(ORMParkingSession.entry_time.desc())
        )
        sessions = result.scalars().unique().all()
        
        return [
            {
                "id": s.id,
                "vehicle_id": s.vehicle_id,
                "parking_spot_id": s.parking_spot_id,
                "entry_time": s.entry_time,
                "exit_time": s.exit_time,
                "amount_paid": s.amount_paid,
                "payment_status": s.payment_status,
                "hourly_rate": s.hourly_rate,
                "vehicle": {
                    "license_plate": s.vehicle.license_plate,
                    "color": s.vehicle.color,
                    "brand": s.vehicle.brand,
                } if s.vehicle else None,
                "parking_spot": {
                    "spot_number": s.parking_spot.spot_number,
                    "floor": s.parking_spot.floor,
                } if s.parking_spot else None,
            } for s in sessions
        ]

    async def get_all_sessions(self) -> List[ParkingSession]:
        result = await self.session.execute(select(ORMParkingSession))
        return [
            ParkingSession(
                id=s.id, vehicle_id=s.vehicle_id, parking_spot_id=s.parking_spot_id,
                entry_time=s.entry_time, exit_time=s.exit_time, amount_paid=s.amount_paid,
                payment_status=s.payment_status, hourly_rate=s.hourly_rate
            ) for s in result.scalars().all()
        ]

    async def get_revenue_last_hours(self, hours: int = 1) -> float:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.session.execute(
            select(func.sum(ORMParkingSession.amount_paid)).where(
                and_(
                    ORMParkingSession.exit_time >= cutoff_time,
                    ORMParkingSession.payment_status == PaymentStatus.PAID
                )
            )
        )
        return result.scalar() or 0.0

    async def get_current_vehicle_count(self) -> int:
        result = await self.session.execute(
            select(func.count(ORMParkingSession.id)).where(
                ORMParkingSession.exit_time.is_(None)
            )
        )
        return result.scalar() or 0

    async def get_daily_average_vehicles(self, days: int = 30) -> float:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        daily_counts = await self.session.execute(
            select(
                func.date(ORMParkingSession.entry_time).label('date'),
                func.count(ORMParkingSession.id).label('count')
            ).where(
                ORMParkingSession.entry_time >= cutoff_date
            ).group_by(
                func.date(ORMParkingSession.entry_time)
            )
        )
        
        counts = [row.count for row in daily_counts]
        return sum(counts) / len(counts) if counts else 0.0

    async def get_average_daily_spending(self, days: int = 30) -> float:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        daily_stats = await self.session.execute(
            select(
                func.date(ORMParkingSession.exit_time).label('date'),
                func.sum(ORMParkingSession.amount_paid).label('revenue'),
                func.count(func.distinct(ORMParkingSession.vehicle_id)).label('vehicles')
            ).where(
                and_(
                    ORMParkingSession.exit_time >= cutoff_date,
                    ORMParkingSession.payment_status == PaymentStatus.PAID
                )
            ).group_by(
                func.date(ORMParkingSession.exit_time)
            )
        )
        
        total_revenue = 0
        total_vehicles = 0
        for row in daily_stats:
            if row.revenue and row.vehicles:
                total_revenue += row.revenue
                total_vehicles += row.vehicles
        
        return total_revenue / total_vehicles if total_vehicles > 0 else 0.0

    async def get_average_duration_by_color(self, color: str) -> float:
        result = await self.session.execute(
            select(ORMParkingSession.entry_time, ORMParkingSession.exit_time).select_from(ORMParkingSession).join(ORMVehicle).where(
                and_(
                    ORMVehicle.color.ilike(f"%{color}%"),
                    ORMParkingSession.exit_time.is_not(None)
                )
            )
        )
        durations = []
        for entry_time, exit_time in result:
            if entry_time and exit_time:
                duration = (exit_time - entry_time).total_seconds() / 3600
                durations.append(duration)
        
        avg_hours = sum(durations) / len(durations) if durations else 0.0
        return round(avg_hours, 2) if avg_hours else 0.0

    async def get_hourly_occupancy(self) -> List[Dict]:
        hourly_stats = []
        
        for hour in range(24):
            result = await self.session.execute(
                select(func.count(ORMParkingSession.id)).where(
                    and_(
                        extract('hour', ORMParkingSession.entry_time) <= hour,
                        or_(
                            ORMParkingSession.exit_time.is_(None),
                            extract('hour', ORMParkingSession.exit_time) >= hour
                        )
                    )
                )
            )
            count = result.scalar() or 0
            hourly_stats.append({
                "hour": hour,
                "occupancy": count
            })
        
        return hourly_stats

    async def get_revenue_by_day(self, days: int = 7) -> List[Dict]:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = await self.session.execute(
            select(
                func.strftime('%Y-%m-%d', ORMParkingSession.exit_time).label('date'),
                func.sum(ORMParkingSession.amount_paid).label('revenue')
            ).where(
                and_(
                    ORMParkingSession.exit_time >= cutoff_date,
                    ORMParkingSession.payment_status == PaymentStatus.PAID
                )
            ).group_by(
                func.strftime('%Y-%m-%d', ORMParkingSession.exit_time)
            ).order_by(
                func.strftime('%Y-%m-%d', ORMParkingSession.exit_time)
            )
        )
        
        revenue_data = []
        for row in result:
            
            revenue_data.append({
                "date": datetime.strptime(row.date, '%Y-%m-%d').date().isoformat() if row.date else None,
                "revenue": float(row.revenue) if row.revenue else 0.0
            })
        return revenue_data

    async def get_parking_analytics(self) -> Dict:
        # Current occupancy
        current_vehicles = await self.get_current_vehicle_count()
        
        # Today's revenue
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue_result = await self.session.execute(
            select(func.sum(ORMParkingSession.amount_paid)).where(
                and_(
                    ORMParkingSession.exit_time >= today_start,
                    ORMParkingSession.payment_status == PaymentStatus.PAID
                )
            )
        )
        today_revenue = today_revenue_result.scalar() or 0.0
        
        # Today's vehicle count
        today_vehicles_result = await self.session.execute(
            select(func.count(ORMParkingSession.id)).where(
                ORMParkingSession.entry_time >= today_start
            )
        )
        today_vehicles = today_vehicles_result.scalar() or 0
        
        # Average duration today
        avg_duration_result = await self.session.execute(
            select(ORMParkingSession.entry_time, ORMParkingSession.exit_time).where(
                and_(
                    ORMParkingSession.exit_time >= today_start,
                    ORMParkingSession.exit_time.is_not(None)
                )
            )
        )
        durations = []
        for entry_time, exit_time in avg_duration_result:
            if entry_time and exit_time:
                duration = (exit_time - entry_time).total_seconds() / 3600
                durations.append(duration)
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        
        return {
            "current_occupancy": current_vehicles,
            "today_revenue": round(today_revenue, 2),
            "today_vehicles": today_vehicles,
            "average_duration_hours": round(avg_duration, 2)
        }