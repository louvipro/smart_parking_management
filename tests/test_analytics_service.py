import pytest
from datetime import datetime, timedelta, timezone
from freezegun import freeze_time
from unittest.mock import patch
from unittest.mock import patch
from unittest.mock import patch

from src.application.services.analytics_service import AnalyticsService
from src.application.services.parking_service import ParkingService
from src.domain.common import SpotType, PaymentStatus
from src.domain.entities import ParkingSession
from src.infrastructure.persistence.models.models import ParkingSession as ORMParkingSession
from sqlalchemy import delete





@pytest.fixture
async def setup_test_data(db_session, parking_service, init_parking_spots):
    """Set up test data with various parking sessions."""
    # Create vehicles with different colors and brands
    vehicles_data = [
        ("RED001", "Red", "Toyota"),
        ("RED002", "Red", "Honda"),
        ("BLUE001", "Blue", "Ford"),
        ("WHITE001", "White", "BMW"),
        ("BLACK001", "Black", "Mercedes"),
    ]
    
    sessions = []
    base_time = datetime.now(timezone.utc)
    
    for i, (plate, color, brand) in enumerate(vehicles_data):
        # Register entry
        session = await parking_service.register_vehicle_entry(
            license_plate=plate,
            color=color,
            brand=brand,
            spot_type=SpotType.REGULAR
        )
        sessions.append(session)
    
    # Exit some vehicles with payments
    for i, session in enumerate(sessions[:3]):  # Exit first 3 vehicles
        vehicle = await parking_service.vehicle_repo.get_by_id(session.vehicle_id)
        await parking_service.register_vehicle_exit(vehicle.license_plate)
    
    return sessions


class TestAnalyticsServiceRevenue:
    """Test revenue-related analytics."""
    
    async def test_get_revenue_last_hours(self, analytics_service, setup_test_data):
        """Test getting revenue from the last N hours."""
        # Get revenue from last 24 hours (should include all 3 exits)
        revenue_24h = await analytics_service.get_revenue_last_hours(24)
        assert revenue_24h > 0
        
        # Get revenue from last 1 hour (might be 0 or include recent exits)
        revenue_1h = await analytics_service.get_revenue_last_hours(1)
        assert revenue_1h >= 0
        assert revenue_1h <= revenue_24h
    
    async def test_get_revenue_no_payments(self, analytics_service, init_parking_spots):
        """Test revenue when no payments have been made."""
        revenue = await analytics_service.get_revenue_last_hours(24)
        assert revenue == 0.0

    async def test_get_revenue_for_period_with_no_payments(self, analytics_service: AnalyticsService, empty_db_for_analytics, db_session):
        """Test revenue for a period with no payments."""
        # Ensure no existing parking sessions interfere
        await db_session.execute(delete(ORMParkingSession))
        await db_session.commit()

        revenue = await empty_db_for_analytics.get_revenue_last_hours(0)
        assert revenue == 0.0
    
    async def test_get_revenue_by_day(self, analytics_service, parking_service, init_parking_spots):
        """Test getting daily revenue breakdown."""
        # Create sessions across multiple days
        base_date = datetime.now(timezone.utc)
        
        for i in range(3):
            # Ensure each session is on a distinct day
            entry_time = base_date - timedelta(days=i + 1, hours=2)
            exit_time = base_date - timedelta(days=i + 1, hours=1)
            
            # Manually set exit time and amount paid for accurate revenue calculation
            session = await parking_service.register_vehicle_entry(
                license_plate=f"DAY{i}",
                color="Blue",
                brand="Toyota",
                spot_type=SpotType.REGULAR
            )
            session_obj = await parking_service.parking_session_repo.get_by_id(session.id)
            session_obj.exit_time = exit_time
            session_obj.amount_paid = 5.0 * ((exit_time - entry_time).total_seconds() / 3600) # Assuming 5.0 hourly rate
            session_obj.payment_status = PaymentStatus.PAID
            await parking_service.parking_session_repo.update(session_obj)
        
        # Get revenue by day
        revenue_data = await analytics_service.get_revenue_by_day(7)
        
        assert len(revenue_data) >= 3
        assert all(item["revenue"] >= 0 for item in revenue_data)
        assert all("date" in item for item in revenue_data)


class TestAnalyticsServiceVehicleCounts:
    """Test vehicle counting analytics."""
    
    async def test_count_vehicles_by_color(self, analytics_service, setup_test_data):
        """Test counting vehicles by color."""
        # Count red vehicles (2 active)
        red_count = await analytics_service.count_vehicles_by_color("Red", active_only=True)
        assert red_count == 0  # RED001 and RED002 have exited
        
        # Count all red vehicles including exited
        red_count_all = await analytics_service.count_vehicles_by_color("Red", active_only=False)
        assert red_count_all == 2
        
        # Count blue vehicles
        blue_count = await analytics_service.count_vehicles_by_color("Blue", active_only=True)
        assert blue_count == 0  # BLUE001 has exited
        
        # Test case insensitive
        red_count_lower = await analytics_service.count_vehicles_by_color("red", active_only=True)
        assert red_count_lower == red_count
    
    async def test_get_current_vehicle_count(self, analytics_service, setup_test_data):
        """Test getting current total vehicle count."""
        count = await analytics_service.get_current_vehicle_count()
        assert count == 2  # Only BLACK001 and WHITE001 are still parked
    
    async def test_get_daily_average_vehicles(self, analytics_service, parking_service, init_parking_spots):
        """Test calculating daily average vehicle count."""
        # Create sessions across multiple days
        base_date = datetime.now(timezone.utc)
        
        # Day 1: 3 vehicles
        for i in range(3):
            await parking_service.register_vehicle_entry(
                license_plate=f"DAY1_{i}",
                color="Blue",
                brand="Toyota",
                spot_type=SpotType.REGULAR
            )
        
        # Day 2: 2 vehicles
        for i in range(2):
            await parking_service.register_vehicle_entry(
                license_plate=f"DAY2_{i}",
                color="Red",
                brand="Honda",
                spot_type=SpotType.REGULAR
            )
        
        # Calculate average
        avg = await analytics_service.get_daily_average_vehicles(30)
        assert avg > 0


class TestAnalyticsServiceDurations:
    """Test parking duration analytics."""
    
    async def test_get_average_duration_by_color(self, analytics_service, parking_service, init_parking_spots):
        """Test calculating average parking duration by vehicle color."""
        base_time = datetime.now(timezone.utc)
        
        # Create and exit red vehicles with known durations
        for i, hours in enumerate([2, 3, 4]):  # Average should be 3 hours
            # Entry
            session = await parking_service.register_vehicle_entry(
                license_plate=f"REDTEST{i}",
                color="Red",
                brand="Toyota",
                spot_type=SpotType.REGULAR
            )
            
            # Manually set exit time for accurate duration calculation
            session_obj = await parking_service.parking_session_repo.get_by_id(session.id)
            session_obj.exit_time = session_obj.entry_time + timedelta(hours=hours)
            await parking_service.parking_session_repo.update(session_obj)
            print(f"Entry Time: {session_obj.entry_time}, Exit Time: {session_obj.exit_time}, Hours: {hours}")
            
            
            # No need to call register_vehicle_exit as we manually set exit_time and committed
            # await parking_service.register_vehicle_exit(exit_data)
        
        avg_duration = await analytics_service.get_average_duration_by_color("Red")
        assert avg_duration == pytest.approx(3.0, 0.1)
    
    async def test_get_average_daily_spending(self, analytics_service, parking_service, init_parking_spots):
        """Test calculating average spending per vehicle per day."""
        base_time = datetime.now(timezone.utc)
        
        # Create sessions with known amounts
        # Vehicle 1: 2 hours = $10
        session1 = await parking_service.register_vehicle_entry(license_plate="SPEND1", color="Blue", brand="Ford", spot_type=SpotType.REGULAR)
        session_obj1 = await parking_service.parking_session_repo.get_by_id(session1.id)
        session_obj1.exit_time = session_obj1.entry_time + timedelta(hours=2)
        session_obj1.amount_paid = 10.0
        session_obj1.payment_status = PaymentStatus.PAID
        await parking_service.parking_session_repo.update(session_obj1)

        # Vehicle 2: 4 hours = $20
        session2 = await parking_service.register_vehicle_entry(license_plate="SPEND2", color="Red", brand="Honda", spot_type=SpotType.REGULAR)
        session_obj2 = await parking_service.parking_session_repo.get_by_id(session2.id)
        session_obj2.exit_time = session_obj2.entry_time + timedelta(hours=4)
        session_obj2.amount_paid = 20.0
        session_obj2.payment_status = PaymentStatus.PAID
        await parking_service.parking_session_repo.update(session_obj2)
        
        avg_spending = await analytics_service.get_average_daily_spending(30)
        assert avg_spending == pytest.approx(15.0, 0.1)  # (10 + 20) / 2


class TestAnalyticsServiceDistributions:
    """Test distribution analytics."""
    
    async def test_get_brand_distribution(self, analytics_service, setup_test_data):
        """Test getting vehicle distribution by brand."""
        # Active vehicles only
        brand_dist = await analytics_service.get_brand_distribution(active_only=True)
        assert "Mercedes" in brand_dist
        assert "BMW" in brand_dist
        assert brand_dist["Mercedes"] == 1
        assert brand_dist["BMW"] == 1
        
        # All vehicles
        brand_dist_all = await analytics_service.get_brand_distribution(active_only=False)
        assert len(brand_dist_all) >= len(brand_dist)
    
    async def test_get_floor_distribution(self, analytics_service, setup_test_data):
        """Test getting vehicle distribution by floor."""
        floor_dist = await analytics_service.get_floor_distribution(active_only=True)
        
        # Should have vehicles on floor 1 (since spots are filled sequentially)
        assert 2 in floor_dist
        assert floor_dist[2] == 2
        
        # Total active vehicles should match
        total_vehicles = sum(floor_dist.values())
        assert total_vehicles == 2  # BLACK001 and WHITE001 are still parked
    
    async def test_get_parking_analytics(self, analytics_service, parking_service, init_parking_spots):
        """Test comprehensive parking analytics."""
        from unittest.mock import patch # Import patch here
        with freeze_time(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)):
            # Create some test data for today
            today_start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            # Register and exit a vehicle today
            with patch('src.application.services.parking_service.datetime') as mock_dt:
                mock_dt.now.return_value = today_start_time + timedelta(hours=1)
                mock_dt.timezone = timezone
                session1 = await parking_service.register_vehicle_entry(
                    license_plate="TODAY1",
                    color="Green",
                    brand="Tesla",
                    spot_type=SpotType.REGULAR
                )
            # Exit session1
            with patch('src.application.services.parking_service.datetime') as mock_dt:
                mock_dt.now.return_value = today_start_time + timedelta(hours=4) # Exit 3 hours after entry
                mock_dt.timezone = timezone
                vehicle1 = await parking_service.vehicle_repo.get_by_id(session1.vehicle_id)
                await parking_service.register_vehicle_exit(vehicle1.license_plate)
            session1 = await parking_service.parking_session_repo.get_by_id(session1.id) # Refresh session1 after exit

            # Register another vehicle (still parked)
            with patch('src.application.services.parking_service.datetime') as mock_dt:
                mock_dt.now.return_value = today_start_time + timedelta(hours=2)
                mock_dt.timezone = timezone
                session2 = await parking_service.register_vehicle_entry(
                    license_plate="TODAY2",
                    color="Yellow",
                    brand="Nissan",
                    spot_type=SpotType.REGULAR
                )
        
        analytics = await analytics_service.get_parking_analytics()
        
        assert analytics["current_occupancy"] == 1  # TODAY2 is still parked
        assert analytics["today_revenue"] == 15.0  # 3 hours * $5
        assert analytics["today_vehicles"] == 2  # Both vehicles entered today
        assert analytics["average_duration_hours"] == pytest.approx(3.0, 0.1)