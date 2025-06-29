from datetime import datetime, timedelta, date, timezone
from typing import List, Dict

from src.application.repositories import AbstractVehicleRepository, AbstractParkingSessionRepository, AbstractParkingSpotRepository
from src.domain.common import PaymentStatus


class AnalyticsService:
    def __init__(
        self,
        vehicle_repo: AbstractVehicleRepository,
        parking_session_repo: AbstractParkingSessionRepository,
        parking_spot_repo: AbstractParkingSpotRepository
    ):
        self.vehicle_repo = vehicle_repo
        self.parking_session_repo = parking_session_repo
        self.parking_spot_repo = parking_spot_repo

    async def get_revenue_last_hours(self, hours: int = 1) -> float:
        return await self.parking_session_repo.get_revenue_last_hours(hours)

    async def count_vehicles_by_color(self, color: str, active_only: bool = True) -> int:
        return await self.vehicle_repo.count_by_color(color, active_only)

    async def get_current_vehicle_count(self) -> int:
        return await self.parking_session_repo.get_current_vehicle_count()

    async def get_daily_average_vehicles(self, days: int = 30) -> float:
        return await self.parking_session_repo.get_daily_average_vehicles(days)

    async def get_average_daily_spending(self, days: int = 30) -> float:
        return await self.parking_session_repo.get_average_daily_spending(days)

    async def get_average_duration_by_color(self, color: str) -> float:
        return await self.parking_session_repo.get_average_duration_by_color(color)

    async def get_hourly_occupancy(self) -> List[Dict]:
        return await self.parking_session_repo.get_hourly_occupancy()

    async def get_revenue_by_day(self, days: int = 7) -> List[Dict]:
        return await self.parking_session_repo.get_revenue_by_day(days)

    async def get_brand_distribution(self, active_only: bool = True) -> Dict[str, int]:
        return await self.vehicle_repo.get_brand_distribution(active_only)

    async def get_floor_distribution(self, active_only: bool = True) -> Dict[int, int]:
        return await self.parking_spot_repo.get_floor_distribution(active_only)

    async def get_parking_analytics(self) -> Dict:
        return await self.parking_session_repo.get_parking_analytics()