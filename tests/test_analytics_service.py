import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from services.analytics_service import AnalyticsService
from services.parking_service import ParkingService
from schemas.parking import VehicleEntry, VehicleExit, SpotType
from database.models import ParkingSession


@pytest.fixture
async def analytics_service(db_session):
    """Create an AnalyticsService instance with test database session."""
    return AnalyticsService(db=db_session)


@pytest.fixture
async def parking_service(db_session):
    """Create a ParkingService instance for test data setup."""
    return ParkingService(db=db_session)


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
    base_time = datetime.utcnow()
    
    for i, (plate, color, brand) in enumerate(vehicles_data):
        # Register entry
        entry_data = VehicleEntry(
            license_plate=plate,
            color=color,
            brand=brand,
            spot_type=SpotType.REGULAR
        )
        
        # Mock entry time to spread across hours
        with patch('services.parking_service.datetime') as mock_dt:
            mock_dt.utcnow.return_value = base_time - timedelta(hours=i*2)
            session = await parking_service.register_vehicle_entry(entry_data)
            sessions.append(session)
    
    # Exit some vehicles with payments
    for i, session in enumerate(sessions[:3]):  # Exit first 3 vehicles
        with patch('services.parking_service.datetime') as mock_dt:
            # Each stayed for different durations
            mock_dt.utcnow.return_value = base_time - timedelta(hours=i)
            exit_data = VehicleExit(license_plate=session.vehicle.license_plate)
            await parking_service.register_vehicle_exit(exit_data)
    
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
    
    async def test_get_revenue_by_day(self, analytics_service, parking_service, init_parking_spots):
        """Test getting daily revenue breakdown."""
        # Create sessions across multiple days
        base_date = datetime.utcnow()
        
        for day in range(3):
            entry_time = base_date - timedelta(days=day, hours=2)
            exit_time = base_date - timedelta(days=day)
            
            # Register and exit vehicle
            with patch('services.parking_service.datetime') as mock_dt:
                mock_dt.utcnow.return_value = entry_time
                entry_data = VehicleEntry(
                    license_plate=f"DAY{day}",
                    color="Blue",
                    brand="Toyota",
                    spot_type=SpotType.REGULAR
                )
                session = await parking_service.register_vehicle_entry(entry_data)
                
                mock_dt.utcnow.return_value = exit_time
                exit_data = VehicleExit(license_plate=f"DAY{day}")
                await parking_service.register_vehicle_exit(exit_data)
        
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
        assert red_count == 2  # RED001 and RED002 are still parked
        
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
        base_date = datetime.utcnow()
        
        # Day 1: 3 vehicles
        for i in range(3):
            with patch('services.parking_service.datetime') as mock_dt:
                mock_dt.utcnow.return_value = base_date - timedelta(days=1)
                entry_data = VehicleEntry(
                    license_plate=f"DAY1_{i}",
                    color="Blue",
                    brand="Toyota",
                    spot_type=SpotType.REGULAR
                )
                await parking_service.register_vehicle_entry(entry_data)
        
        # Day 2: 2 vehicles
        for i in range(2):
            with patch('services.parking_service.datetime') as mock_dt:
                mock_dt.utcnow.return_value = base_date
                entry_data = VehicleEntry(
                    license_plate=f"DAY2_{i}",
                    color="Red",
                    brand="Honda",
                    spot_type=SpotType.REGULAR
                )
                await parking_service.register_vehicle_entry(entry_data)
        
        # Calculate average
        avg = await analytics_service.get_daily_average_vehicles(30)
        assert avg > 0


class TestAnalyticsServiceDurations:
    """Test parking duration analytics."""
    
    async def test_get_average_duration_by_color(self, analytics_service, parking_service, init_parking_spots):
        """Test calculating average parking duration by vehicle color."""
        base_time = datetime.utcnow()
        
        # Create and exit red vehicles with known durations
        for i, hours in enumerate([2, 3, 4]):  # Average should be 3 hours
            with patch('services.parking_service.datetime') as mock_dt:
                # Entry
                mock_dt.utcnow.return_value = base_time - timedelta(hours=hours)
                entry_data = VehicleEntry(
                    license_plate=f"REDTEST{i}",
                    color="Red",
                    brand="Toyota",
                    spot_type=SpotType.REGULAR
                )
                session = await parking_service.register_vehicle_entry(entry_data)
                
                # Exit
                mock_dt.utcnow.return_value = base_time
                exit_data = VehicleExit(license_plate=f"REDTEST{i}")
                await parking_service.register_vehicle_exit(exit_data)
        
        avg_duration = await analytics_service.get_average_duration_by_color("Red")
        assert avg_duration == pytest.approx(3.0, 0.1)
    
    async def test_get_average_daily_spending(self, analytics_service, parking_service, init_parking_spots):
        """Test calculating average spending per vehicle per day."""
        base_time = datetime.utcnow()
        
        # Create sessions with known amounts
        with patch('services.parking_service.datetime') as mock_dt:
            # Vehicle 1: 2 hours = $10
            mock_dt.utcnow.return_value = base_time - timedelta(hours=2)
            entry1 = VehicleEntry(license_plate="SPEND1", color="Blue", brand="Ford", spot_type=SpotType.REGULAR)
            await parking_service.register_vehicle_entry(entry1)
            
            mock_dt.utcnow.return_value = base_time
            await parking_service.register_vehicle_exit(VehicleExit(license_plate="SPEND1"))
            
            # Vehicle 2: 4 hours = $20
            mock_dt.utcnow.return_value = base_time - timedelta(hours=4)
            entry2 = VehicleEntry(license_plate="SPEND2", color="Red", brand="Honda", spot_type=SpotType.REGULAR)
            await parking_service.register_vehicle_entry(entry2)
            
            mock_dt.utcnow.return_value = base_time
            await parking_service.register_vehicle_exit(VehicleExit(license_plate="SPEND2"))
        
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
        assert 1 in floor_dist
        assert floor_dist[1] > 0
        
        # Total active vehicles should match
        total_vehicles = sum(floor_dist.values())
        assert total_vehicles == 2  # BLACK001 and WHITE001 are still parked
    
    async def test_get_parking_analytics(self, analytics_service, parking_service, init_parking_spots):
        """Test comprehensive parking analytics."""
        # Create some test data for today
        with patch('services.parking_service.datetime') as mock_dt:
            now = datetime.utcnow()
            mock_dt.utcnow.return_value = now
            
            # Register and exit a vehicle today
            entry_data = VehicleEntry(
                license_plate="TODAY1",
                color="Green",
                brand="Tesla",
                spot_type=SpotType.REGULAR
            )
            await parking_service.register_vehicle_entry(entry_data)
            
            # Exit after 3 hours
            mock_dt.utcnow.return_value = now + timedelta(hours=3)
            await parking_service.register_vehicle_exit(VehicleExit(license_plate="TODAY1"))
            
            # Register another vehicle (still parked)
            mock_dt.utcnow.return_value = now
            entry_data2 = VehicleEntry(
                license_plate="TODAY2",
                color="Yellow",
                brand="Nissan",
                spot_type=SpotType.REGULAR
            )
            await parking_service.register_vehicle_entry(entry_data2)
        
        analytics = await analytics_service.get_parking_analytics()
        
        assert analytics["current_occupancy"] == 1  # TODAY2 is still parked
        assert analytics["today_revenue"] == 15.0  # 3 hours * $5
        assert analytics["today_vehicles"] == 2  # Both vehicles entered today
        assert analytics["average_duration_hours"] == pytest.approx(3.0, 0.1)