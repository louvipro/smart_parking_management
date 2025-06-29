import pytest
from unittest.mock import patch, AsyncMock
import os

from src.infrastructure.ml_agents.parking_agent import ParkingAssistant


class TestParkingAgentTools:
    """Test the parking agent tools used by CrewAI agents."""

    @pytest.fixture
    def assistant(self):
        """Create a ParkingAssistant instance."""
        return ParkingAssistant()

    def get_tool_func(self, assistant, tool_name):
        """Helper to find a tool's function by its name."""
        for tool in assistant.tools:
            if tool.name == tool_name:
                return tool.func
        raise ValueError(f"Tool '{tool_name}' not found")

    @patch("src.infrastructure.ml_agents.parking_agent.AnalyticsService")
    def test_get_current_count_tool(self, MockAnalyticsService, assistant):
        """Test the get_current_count tool functionality."""
        # Mock the service method
        mock_analytics = MockAnalyticsService.return_value
        mock_analytics.get_current_vehicle_count = AsyncMock(return_value=5)

        # Get the tool function
        tool_func = self.get_tool_func(assistant, "get_current_count")

        # Test the tool function
        result = tool_func(None)  # Argument is ignored
        assert isinstance(result, str)
        assert "5" in result

    @patch("src.infrastructure.ml_agents.parking_agent.AnalyticsService")
    def test_count_by_color_tool(self, MockAnalyticsService, assistant):
        """Test the count_by_color tool functionality."""
        mock_analytics = MockAnalyticsService.return_value
        mock_analytics.count_vehicles_by_color = AsyncMock(return_value=2)

        tool_func = self.get_tool_func(assistant, "count_by_color")

        result = tool_func("red")
        assert isinstance(result, str)
        assert "2" in result
        assert "red" in result

    @patch("src.infrastructure.ml_agents.parking_agent.AnalyticsService")
    def test_get_revenue_tool(self, MockAnalyticsService, assistant):
        """Test the get_revenue tool functionality."""
        mock_analytics = MockAnalyticsService.return_value
        mock_analytics.get_revenue_last_hours = AsyncMock(return_value=25.50)

        tool_func = self.get_tool_func(assistant, "get_revenue")

        result = tool_func("24")
        assert isinstance(result, str)
        assert "$25.50" in result

    @patch("src.infrastructure.ml_agents.parking_agent.ParkingService")
    def test_get_parking_status_tool(self, MockParkingService, assistant):
        """Test the get_parking_status tool functionality."""
        mock_service = MockParkingService.return_value
        mock_service.get_parking_status = AsyncMock(return_value={
            'total_spots': 15,
            'occupied_spots': 1,
            'available_spots': 14,
            'occupancy_percentage': 6.67
        })

        tool_func = self.get_tool_func(assistant, "get_parking_status")

        result = tool_func(None)
        assert isinstance(result, str)
        assert "Total spots: 15" in result
        assert "Available spots: 14" in result
        assert "Occupancy rate: 6.7%" in result


class TestParkingAgentIntegration:
    """Test the full parking agent integration."""

    @pytest.fixture
    def assistant(self):
        """Create a ParkingAssistant instance."""
        return ParkingAssistant()

    def test_agent_tool_creation(self, assistant):
        """Test that agents are created with the correct tools."""
        tool_names = [tool.name for tool in assistant.tools]

        expected_tools = [
            "get_current_count",
            "count_by_color",
            "get_revenue",
            "get_parking_status",
            "get_daily_average",
            "get_average_spending",
            "get_duration_by_color",
            "get_today_analytics",
        ]

        for tool_name in expected_tools:
            assert tool_name in tool_names

    def test_agent_tool_descriptions(self, assistant):
        """Test that tool descriptions are helpful."""
        for tool in assistant.tools:
            assert tool.description is not None
            assert len(tool.description) > 10

    @patch('src.infrastructure.ml_agents.parking_agent.Crew')
    @patch.dict(os.environ, {'OPENAI_API_KEY': 'invalid_key'})
    def test_process_query_api_error(self, MockCrew, assistant):
        """Test process_query handles API key/connection errors."""
        mock_crew_instance = MockCrew.return_value
        mock_crew_instance.kickoff.side_effect = Exception("API key error or connection issue")

        response = assistant.process_query("How many cars are parked?")
        assert "I need an AI model to process your query." in response
        assert "API key error or connection issue" in response

    @patch('src.infrastructure.ml_agents.parking_agent.Crew')
    def test_process_query_generic_error(self, MockCrew, assistant):
        """Test process_query handles generic exceptions."""
        mock_crew_instance = MockCrew.return_value
        mock_crew_instance.kickoff.side_effect = Exception("Something unexpected happened")

        response = assistant.process_query("What is the revenue?")
        assert "Sorry, I encountered an error: Something unexpected happened" in response

    @patch('src.infrastructure.ml_agents.parking_agent.ChatOpenAI')
    @patch.dict(os.environ, {'OPENAI_MODEL_NAME': 'ollama/test-model', 'OPENAI_API_BASE': 'http://localhost:8000'})
    def test_ollama_model_initialization(self, MockChatOpenAI):
        """Test that ChatOpenAI is initialized correctly for Ollama models."""
        ParkingAssistant()
        MockChatOpenAI.assert_called_once_with(
            model='test-model',
            openai_api_key='dummy',
            openai_api_base='http://localhost:8000',
            temperature=0.1,
            max_tokens=2000
        )
