from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities import Vehicle, ParkingSpot, ParkingSession


class AbstractVehicleRepository(ABC):
    @abstractmethod
    async def get_by_license_plate(self, license_plate: str) -> Optional[Vehicle]:
        pass

    @abstractmethod
    async def add(self, vehicle: Vehicle) -> Vehicle:
        pass

    @abstractmethod
    async def count_by_color(self, color: str, active_only: bool = True) -> int:
        pass

    @abstractmethod
    async def get_brand_distribution(self, active_only: bool = True) -> dict:
        pass

    @abstractmethod
    async def get_by_id(self, vehicle_id: int) -> Optional[Vehicle]:
        pass


class AbstractParkingSpotRepository(ABC):
    @abstractmethod
    async def get_available_spot(self, spot_type: str) -> Optional[ParkingSpot]:
        pass

    @abstractmethod
    async def update(self, spot: ParkingSpot) -> ParkingSpot:
        pass

    @abstractmethod
    async def get_all(self) -> List[ParkingSpot]:
        pass

    @abstractmethod
    async def get_by_id(self, spot_id: int) -> Optional[ParkingSpot]:
        pass

    @abstractmethod
    async def get_total_spots_count(self) -> int:
        pass

    @abstractmethod
    async def get_occupied_spots_count(self) -> int:
        pass

    @abstractmethod
    async def get_floor_distribution(self, active_only: bool = True) -> dict:
        pass

    @abstractmethod
    async def update_all_occupied_by_type(self, spot_type: str, is_occupied: bool):
        pass

    @abstractmethod
    async def update_all_occupied(self, is_occupied: bool):
        pass


class AbstractParkingSessionRepository(ABC):
    @abstractmethod
    async def get_active_session_by_license_plate(self, license_plate: str) -> Optional[ParkingSession]:
        pass

    @abstractmethod
    async def add(self, session: ParkingSession) -> ParkingSession:
        pass

    @abstractmethod
    async def update(self, session: ParkingSession) -> ParkingSession:
        pass

    @abstractmethod
    async def get_active_sessions(self) -> List[ParkingSession]:
        pass

    @abstractmethod
    async def get_all_sessions(self) -> List[ParkingSession]:
        pass

    @abstractmethod
    async def get_revenue_last_hours(self, hours: int = 1) -> float:
        pass

    @abstractmethod
    async def get_current_vehicle_count(self) -> int:
        pass

    @abstractmethod
    async def get_daily_average_vehicles(self, days: int = 30) -> float:
        pass

    @abstractmethod
    async def get_average_daily_spending(self, days: int = 30) -> float:
        pass

    @abstractmethod
    async def get_average_duration_by_color(self, color: str) -> float:
        pass

    @abstractmethod
    async def get_hourly_occupancy(self) -> List[dict]:
        pass

    @abstractmethod
    async def get_revenue_by_day(self, days: int = 7) -> List[dict]:
        pass

    @abstractmethod
    async def get_parking_analytics(self) -> dict:
        pass

    @abstractmethod
    async def get_by_id(self, session_id: int) -> Optional[ParkingSession]:
        pass
