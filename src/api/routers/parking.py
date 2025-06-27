from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database.database import get_async_db
from services.parking_service import ParkingService
from services.analytics_service import AnalyticsService
from schemas.parking import (
    VehicleEntry, VehicleExit, PaymentInfo, ParkingStatus,
    ParkingSessionResponse, ParkingAnalytics
)

router = APIRouter(prefix="/api/parking", tags=["parking"])


@router.post("/entry", response_model=ParkingSessionResponse)
async def vehicle_entry(
    vehicle_data: VehicleEntry,
    db: AsyncSession = Depends(get_async_db)
):
    service = ParkingService(db)
    try:
        session = await service.register_vehicle_entry(vehicle_data)
        return session
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/exit", response_model=PaymentInfo)
async def vehicle_exit(
    exit_data: VehicleExit,
    db: AsyncSession = Depends(get_async_db)
):
    service = ParkingService(db)
    try:
        payment_info = await service.register_vehicle_exit(exit_data)
        return payment_info
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/status", response_model=ParkingStatus)
async def get_parking_status(db: AsyncSession = Depends(get_async_db)):
    service = ParkingService(db)
    try:
        status = await service.get_parking_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/sessions/active", response_model=List[ParkingSessionResponse])
async def get_active_sessions(db: AsyncSession = Depends(get_async_db)):
    service = ParkingService(db)
    try:
        sessions = await service.get_active_sessions()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/analytics/revenue/{hours}")
async def get_revenue_last_hours(
    hours: int,
    db: AsyncSession = Depends(get_async_db)
):
    analytics = AnalyticsService(db)
    try:
        revenue = await analytics.get_revenue_last_hours(hours)
        return {"hours": hours, "revenue": revenue}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/analytics/vehicles/color/{color}")
async def count_vehicles_by_color(
    color: str,
    active_only: bool = True,
    db: AsyncSession = Depends(get_async_db)
):
    analytics = AnalyticsService(db)
    try:
        count = await analytics.count_vehicles_by_color(color, active_only)
        return {"color": color, "count": count, "active_only": active_only}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/analytics/current-count")
async def get_current_vehicle_count(db: AsyncSession = Depends(get_async_db)):
    analytics = AnalyticsService(db)
    try:
        count = await analytics.get_current_vehicle_count()
        return {"current_vehicles": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/analytics/daily-average/{days}")
async def get_daily_average_vehicles(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db)
):
    analytics = AnalyticsService(db)
    try:
        average = await analytics.get_daily_average_vehicles(days)
        return {"days": days, "average_daily_vehicles": round(average, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/analytics/average-spending/{days}")
async def get_average_daily_spending(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db)
):
    analytics = AnalyticsService(db)
    try:
        average = await analytics.get_average_daily_spending(days)
        return {"days": days, "average_daily_spending": round(average, 2)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/analytics/duration/color/{color}")
async def get_average_duration_by_color(
    color: str,
    db: AsyncSession = Depends(get_async_db)
):
    analytics = AnalyticsService(db)
    try:
        duration = await analytics.get_average_duration_by_color(color)
        return {"color": color, "average_duration_hours": duration}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/analytics/overview")
async def get_parking_analytics(db: AsyncSession = Depends(get_async_db)):
    analytics = AnalyticsService(db)
    try:
        data = await analytics.get_parking_analytics()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")