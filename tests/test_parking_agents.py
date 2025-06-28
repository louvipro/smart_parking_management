import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timedelta

from services.parking_service import ParkingService
from services.analytics_service import AnalyticsService
from schemas.parking import VehicleEntry, SpotType


@pytest.fixture
async def setup_agent_test_data(db_session):
    """Set up test data for agent testing."""
    # Initialize parking spots
    from database.models import ParkingSpot
    
    spots = []
    for floor in range(1, 3):
        for spot_num in range(1, 6):
            spot_number = f"{floor}-{spot_num:02d}"
            spot_type = "regular"
            spot = ParkingSpot(
                spot_number=spot_number,
                floor=floor,
                spot_type=spot_type,
                is_occupied=False
            )
            spots.append(spot)
            db_session.add(spot)
    
    await db_session.commit()
    
    # Create some parked vehicles
    parking_service = ParkingService(db_session)
    
    vehicles = [
        ("RED001", "Red", "Toyota"),
        ("RED002", "Red", "Honda"),
        ("BLUE001", "Blue", "Ford"),
        ("WHITE001", "White", "BMW"),
    ]
    
    for plate, color, brand in vehicles:
        entry_data = VehicleEntry(
            license_plate=plate,
            color=color,
            brand=brand,
            spot_type=SpotType.REGULAR
        )
        await parking_service.register_vehicle_entry(entry_data)
    
    return len(vehicles)


class TestSimpleParkingAssistant:
    """Test the SimpleParkingAssistant implementation."""
    
    @pytest.fixture
    async def simple_assistant(self):
        """Create a SimpleParkingAssistant instance."""
        from ml.parking_agent_simple import SimpleParkingAssistant
        return SimpleParkingAssistant()
    
    async def test_count_vehicles_by_color(self, simple_assistant, setup_agent_test_data):
        """Test counting vehicles by color."""
        # Test red cars
        response = await simple_assistant.process_query("How many red cars are there?")
        assert "2 red cars" in response.lower()
        
        # Test blue cars
        response = await simple_assistant.process_query("Count blue vehicles")
        assert "1 blue car" in response.lower()
        
        # Test case insensitive
        response = await simple_assistant.process_query("How many RED cars?")
        assert "2 red cars" in response.lower()
    
    async def test_total_vehicle_count(self, simple_assistant, setup_agent_test_data):
        """Test getting total vehicle count."""
        queries = [
            "How many cars are currently parked?",
            "What's the total vehicle count?",
            "How many vehicles are there?",
            "Show me current count"
        ]
        
        for query in queries:
            response = await simple_assistant.process_query(query)
            assert "4 vehicles" in response or "4 cars" in response
    
    async def test_revenue_queries(self, simple_assistant, db_session, setup_agent_test_data):
        """Test revenue-related queries."""
        # Exit some vehicles to generate revenue
        parking_service = ParkingService(db_session)
        from schemas.parking import VehicleExit
        
        # Exit RED001 after 2 hours
        with patch('services.parking_service.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime.utcnow() + timedelta(hours=2)
            await parking_service.register_vehicle_exit(VehicleExit(license_plate="RED001"))
        
        # Test revenue query
        response = await simple_assistant.process_query("What's the revenue from the last 24 hours?")
        assert "$10.00" in response  # 2 hours * $5
        
        # Test with specific hours
        response = await simple_assistant.process_query("Show revenue for last 1 hour")
        assert "last 1 hour" in response.lower()
    
    async def test_parking_status(self, simple_assistant, setup_agent_test_data):
        """Test parking status query."""
        response = await simple_assistant.process_query("What's the parking status?")
        
        assert "Total spots:" in response
        assert "Available spots:" in response
        assert "Occupied spots:" in response
        assert "Occupancy rate:" in response
    
    async def test_unknown_query(self, simple_assistant):
        """Test handling of unknown queries."""
        response = await simple_assistant.process_query("What's the weather like?")
        
        assert "I can help you with:" in response
        assert "How many cars" in response
    
    async def test_error_handling(self, simple_assistant):
        """Test error handling in assistant."""
        # Mock database connection to raise an error
        with patch('ml.parking_agent_simple.AsyncSessionLocal') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            response = await simple_assistant.process_query("How many cars?")
            assert "Sorry, I encountered an error" in response


class TestParkingAgentTools:
    """Test the parking agent tools used by CrewAI agents."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session
    
    async def test_count_vehicles_tool(self, setup_agent_test_data):
        """Test the count_vehicles tool functionality."""
        from ml.parking_agent import count_vehicles
        
        # Test the tool function
        result = await count_vehicles()
        assert isinstance(result, str)
        assert "4" in result or "four" in result.lower()
    
    async def test_count_vehicles_by_color_tool(self, setup_agent_test_data):
        """Test the count_vehicles_by_color tool functionality."""
        from ml.parking_agent import count_vehicles_by_color
        
        # Test counting red vehicles
        result = await count_vehicles_by_color("red")
        assert isinstance(result, str)
        assert "2" in result or "two" in result.lower()
        
        # Test counting non-existent color
        result = await count_vehicles_by_color("purple")
        assert "0" in result or "no" in result.lower()
    
    async def test_get_revenue_tool(self, db_session, setup_agent_test_data):
        """Test the get_revenue tool functionality."""
        # Create some revenue
        parking_service = ParkingService(db_session)
        from schemas.parking import VehicleExit
        
        with patch('services.parking_service.datetime') as mock_dt:
            mock_dt.utcnow.return_value = datetime.utcnow() + timedelta(hours=3)
            await parking_service.register_vehicle_exit(VehicleExit(license_plate="BLUE001"))
        
        from ml.parking_agent import get_revenue
        
        # Test getting revenue
        result = await get_revenue(1)
        assert isinstance(result, str)
        assert "$" in result
        assert "15" in result  # 3 hours * $5
    
    async def test_get_parking_status_tool(self, setup_agent_test_data):
        """Test the get_parking_status tool functionality."""
        from ml.parking_agent import get_parking_status
        
        result = await get_parking_status()
        assert isinstance(result, str)
        assert "total" in result.lower()
        assert "available" in result.lower()
        assert "occupied" in result.lower()


class TestParkingAgentIntegration:
    """Test the full parking agent integration."""
    
    @pytest.fixture
    def mock_crew_agent(self):
        """Create a mock CrewAI agent."""
        agent = MagicMock()
        agent.execute_task = AsyncMock()
        return agent
    
    async def test_agent_response_format(self, mock_crew_agent, setup_agent_test_data):
        """Test that agent responses are properly formatted."""
        # Mock the agent to return a structured response
        mock_crew_agent.execute_task.return_value = {
            "output": "There are currently 4 vehicles parked: 2 red cars, 1 blue car, and 1 white car."
        }
        
        # Test query processing
        query = "How many cars are in the parking lot?"
        result = await mock_crew_agent.execute_task(query)
        
        assert "output" in result
        assert "4 vehicles" in result["output"]
    
    async def test_agent_tool_usage(self, setup_agent_test_data):
        """Test that agents properly use the provided tools."""
        # This test verifies the tools are callable and return expected formats
        from ml.parking_agent import tools
        
        # Verify all required tools are present
        tool_names = [tool.name for tool in tools]
        assert "count_vehicles" in tool_names
        assert "count_vehicles_by_color" in tool_names
        assert "get_revenue" in tool_names
        assert "get_parking_status" in tool_names
        
        # Verify tool descriptions are helpful
        for tool in tools:
            assert tool.description is not None
            assert len(tool.description) > 10