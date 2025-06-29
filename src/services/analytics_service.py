from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, extract, distinct
from datetime import datetime, timedelta, date, timezone
from typing import List, Dict
import pandas as pd

from database.models import Vehicle, ParkingSession, ParkingSpot
from schemas.parking import PaymentStatus


class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_revenue_last_hours(self, hours: int = 1) -> float:
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await self.db.execute(
            select(func.sum(ParkingSession.amount_paid)).where(
                and_(
                    ParkingSession.exit_time >= cutoff_time,
                    ParkingSession.payment_status == PaymentStatus.PAID
                )
            )
        )
        return result.scalar() or 0.0

    async def count_vehicles_by_color(self, color: str, active_only: bool = True) -> int:
        query = select(func.count(func.distinct(Vehicle.id))).select_from(Vehicle).join(ParkingSession)
        
        conditions = [Vehicle.color.ilike(f"%{color}%")]
        if active_only:
            conditions.append(ParkingSession.exit_time.is_(None))
        
        query = query.where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def get_current_vehicle_count(self) -> int:
        result = await self.db.execute(
            select(func.count(ParkingSession.id)).where(
                ParkingSession.exit_time.is_(None)
            )
        )
        return result.scalar() or 0

    async def get_daily_average_vehicles(self, days: int = 30) -> float:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Count vehicles per day
        daily_counts = await self.db.execute(
            select(
                func.date(ParkingSession.entry_time).label('date'),
                func.count(ParkingSession.id).label('count')
            ).where(
                ParkingSession.entry_time >= cutoff_date
            ).group_by(
                func.date(ParkingSession.entry_time)
            )
        )
        
        counts = [row.count for row in daily_counts]
        return sum(counts) / len(counts) if counts else 0.0

    async def get_average_daily_spending(self, days: int = 30) -> float:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get daily revenue and unique vehicles
        daily_stats = await self.db.execute(
            select(
                func.date(ParkingSession.exit_time).label('date'),
                func.sum(ParkingSession.amount_paid).label('revenue'),
                func.count(func.distinct(ParkingSession.vehicle_id)).label('vehicles')
            ).where(
                and_(
                    ParkingSession.exit_time >= cutoff_date,
                    ParkingSession.payment_status == PaymentStatus.PAID
                )
            ).group_by(
                func.date(ParkingSession.exit_time)
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
        result = await self.db.execute(
            select(ParkingSession.entry_time, ParkingSession.exit_time).select_from(ParkingSession).join(Vehicle).where(
                and_(
                    Vehicle.color.ilike(f"%{color}%"),
                    ParkingSession.exit_time.is_not(None)
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
        # Get occupancy for each hour of the day
        hourly_stats = []
        
        for hour in range(24):
            result = await self.db.execute(
                select(func.count(ParkingSession.id)).where(
                    and_(
                        extract('hour', ParkingSession.entry_time) <= hour,
                        or_(
                            ParkingSession.exit_time.is_(None),
                            extract('hour', ParkingSession.exit_time) >= hour
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
        
        result = await self.db.execute(
            select(
                func.strftime('%Y-%m-%d', ParkingSession.exit_time).label('date'),
                func.sum(ParkingSession.amount_paid).label('revenue')
            ).where(
                and_(
                    ParkingSession.exit_time >= cutoff_date,
                    ParkingSession.payment_status == PaymentStatus.PAID
                )
            ).group_by(
                func.strftime('%Y-%m-%d', ParkingSession.exit_time)
            ).order_by(
                func.strftime('%Y-%m-%d', ParkingSession.exit_time)
            )
        )
        
        revenue_data = []
        for row in result:
            
            revenue_data.append({
                "date": datetime.strptime(row.date, '%Y-%m-%d').date().isoformat() if row.date else None,
                "revenue": float(row.revenue) if row.revenue else 0.0
            })
        return revenue_data

    async def get_brand_distribution(self, active_only: bool = True) -> Dict[str, int]:
        """Get distribution of vehicles by brand."""
        query = select(
            Vehicle.brand,
            func.count(func.distinct(Vehicle.id)).label('count')
        ).select_from(Vehicle).join(ParkingSession)
        
        if active_only:
            query = query.where(ParkingSession.exit_time.is_(None))
        
        query = query.group_by(Vehicle.brand).order_by(func.count(func.distinct(Vehicle.id)).desc())
        
        result = await self.db.execute(query)
        return {row.brand: row.count for row in result if row.brand}

    async def get_floor_distribution(self, active_only: bool = True) -> Dict[int, int]:
        """Get distribution of vehicles by floor."""
        query = select(
            ParkingSpot.floor,
            func.count(ParkingSession.id).label('count')
        ).select_from(ParkingSession).join(ParkingSpot)
        
        if active_only:
            query = query.where(ParkingSession.exit_time.is_(None))
        
        query = query.group_by(ParkingSpot.floor).order_by(ParkingSpot.floor)
        
        result = await self.db.execute(query)
        return {row.floor: row.count for row in result}

    async def get_parking_analytics(self) -> Dict:
        # Current occupancy
        current_vehicles = await self.get_current_vehicle_count()
        
        # Today's revenue
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue_result = await self.db.execute(
            select(func.sum(ParkingSession.amount_paid)).where(
                and_(
                    ParkingSession.exit_time >= today_start,
                    ParkingSession.payment_status == PaymentStatus.PAID
                )
            )
        )
        today_revenue = today_revenue_result.scalar() or 0.0
        
        # Today's vehicle count
        today_vehicles_result = await self.db.execute(
            select(func.count(ParkingSession.id)).where(
                ParkingSession.entry_time >= today_start
            )
        )
        today_vehicles = today_vehicles_result.scalar() or 0
        
        # Average duration today
        avg_duration_result = await self.db.execute(
            select(ParkingSession.entry_time, ParkingSession.exit_time).where(
                and_(
                    ParkingSession.exit_time >= today_start,
                    ParkingSession.exit_time.is_not(None)
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