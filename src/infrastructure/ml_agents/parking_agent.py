import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from crewai import Agent, Task, Crew
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

from src.infrastructure.persistence.database import AsyncSessionLocal
from src.application.services.analytics_service import AnalyticsService
from src.application.services.parking_service import ParkingService
from src.infrastructure.persistence.sqlalchemy_repositories.sqlalchemy_repositories import (
    SQLAlchemyVehicleRepository,
    SQLAlchemyParkingSpotRepository,
    SQLAlchemyParkingSessionRepository,
)

def run_async_in_sync(coro):
    """Run async coroutine in a sync context safely."""
    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_thread)
        return future.result()


class ParkingAssistant:
    """CrewAI-based parking assistant with proper async handling."""
    
    def __init__(self):
        # Configure the LLM
        model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        api_key = os.getenv("OPENAI_API_KEY", "dummy")
        base_url = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")

        # Prioritize Ollama if the model name contains "ollama"
        print(f"DEBUG: Attempting to load model: {model_name}")
        if "ollama" in model_name.lower():
            self.llm = ChatOpenAI(
                model=model_name.replace("ollama/", ""),
                openai_api_key="dummy",  # Ollama doesn't need a key
                openai_api_base=base_url,
                temperature=0.1,
                max_tokens=2000
            )
        # Fallback to OpenAI only if a valid API key is provided
        elif api_key and api_key != "dummy":
            self.llm = ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                temperature=0.1
            )
        # If no valid configuration is found, raise an error
        else:
            raise ValueError("No valid LLM configuration found. Please set either Ollama or a valid OpenAI API key.")
        
        # Create tools for the agent
        self.tools = self._create_tools()
        
        # Create the parking data analyst agent
        self.analyst = Agent(
            role='Parking Data Analyst',
            goal='Analyze parking data and provide accurate information to users',
            backstory="""You are an expert parking system analyst who can quickly 
            access and interpret parking data. You provide clear, accurate answers 
            about parking occupancy, revenue, and vehicle statistics. You must use the tools provided to answer questions.""",
            verbose=True,
            allow_delegation=False,
            tools=self.tools,
            llm=self.llm,
            max_iter=15,
            force_tool_use=True
        )
    
    def _create_tools(self) -> list:
        """Create tools for the CrewAI agent."""

        def get_current_count(_) -> str:
            """Get the current number of vehicles in the parking."""
            async def _get_count():
                async with AsyncSessionLocal() as db:
                    vehicle_repo = SQLAlchemyVehicleRepository(db)
                    session_repo = SQLAlchemyParkingSessionRepository(db)
                    spot_repo = SQLAlchemyParkingSpotRepository(db)
                    analytics = AnalyticsService(vehicle_repo, session_repo, spot_repo)
                    return await analytics.get_current_vehicle_count()
            return f"There are currently {run_async_in_sync(_get_count())} vehicles parked."

        def count_by_color(color: str) -> str:
            """Count vehicles by color."""
            if color.lower() in ['toyota', 'honda', 'ford', 'bmw', 'mercedes']:
                return f"'{color}' is a car brand, not a color."
            async def _count_color():
                async with AsyncSessionLocal() as db:
                    vehicle_repo = SQLAlchemyVehicleRepository(db)
                    session_repo = SQLAlchemyParkingSessionRepository(db)
                    spot_repo = SQLAlchemyParkingSpotRepository(db)
                    analytics = AnalyticsService(vehicle_repo, session_repo, spot_repo)
                    return await analytics.count_vehicles_by_color(color.lower(), active_only=True)
            return f"There are {run_async_in_sync(_count_color())} {color} cars currently in the parking."

        def get_recent_revenue(hours: str) -> str:
            """Get revenue generated in the last N hours."""
            try:
                hours_int = int(hours)
            except:
                hours_int = 1
            async def _get_revenue():
                async with AsyncSessionLocal() as db:
                    vehicle_repo = SQLAlchemyVehicleRepository(db)
                    session_repo = SQLAlchemyParkingSessionRepository(db)
                    spot_repo = SQLAlchemyParkingSpotRepository(db)
                    analytics = AnalyticsService(vehicle_repo, session_repo, spot_repo)
                    return await analytics.get_revenue_last_hours(hours_int)
            return f"Revenue generated in the last {hours_int} hour(s): ${run_async_in_sync(_get_revenue()):.2f}"

        def get_parking_status(_) -> str:
            """Get current parking status."""
            async def _get_status():
                async with AsyncSessionLocal() as db:
                    vehicle_repo = SQLAlchemyVehicleRepository(db)
                    spot_repo = SQLAlchemyParkingSpotRepository(db)
                    session_repo = SQLAlchemyParkingSessionRepository(db)
                    parking = ParkingService(vehicle_repo, spot_repo, session_repo)
                    return await parking.get_parking_status()
            status = run_async_in_sync(_get_status())
            return f"""Current Parking Status:
- Total spots: {status['total_spots']}
- Available spots: {status['available_spots']}
- Occupied spots: {status['occupied_spots']}
- Occupancy rate: {status['occupancy_rate']:.1f}%"""

        def get_brand_distribution(_) -> str:
            """Get the distribution of car brands currently parked."""
            async def _get_distribution():
                async with AsyncSessionLocal() as db:
                    vehicle_repo = SQLAlchemyVehicleRepository(db)
                    session_repo = SQLAlchemyParkingSessionRepository(db)
                    spot_repo = SQLAlchemyParkingSpotRepository(db)
                    analytics = AnalyticsService(vehicle_repo, session_repo, spot_repo)
                    return await analytics.get_brand_distribution(active_only=True)
            dist = run_async_in_sync(_get_distribution())
            if not dist:
                return "No brand data available for currently parked vehicles."
            return "Brand Distribution:\n" + "\n".join([f"- {brand}: {count}" for brand, count in dist.items()])

        return [
            Tool(name="get_current_count", func=get_current_count, description="Use to get the current total number of vehicles in the parking."),
            Tool(name="count_by_color", func=count_by_color, description="Use to count vehicles of a specific color. The input must be a color name."),
            Tool(name="get_revenue", func=get_recent_revenue, description="Use to get revenue generated in the last N hours. The input must be a number of hours."),
            Tool(name="get_parking_status", func=get_parking_status, description="Use to get the current parking status, including total, occupied, and available spots, and occupancy rate. This tool provides a direct answer to queries about current parking status."),
            Tool(name="get_brand_distribution", func=get_brand_distribution, description="Use to get the distribution of car brands currently parked."),
        ]


    def process_query(self, query: str) -> str:
        """Process a user query using CrewAI."""
        try:
            task = Task(
                description=f"""Analyze the user's query and use the available tools to provide a direct and accurate answer.
                The user wants to know: '{query}'
                
                Your final answer MUST be the result from a tool. Do not add any extra conversational text.
                - For questions about counts (total, by color): Use the appropriate counting tool.
                - For questions about status or revenue: Use the corresponding status or revenue tool.
                - For questions about distributions (brand, floor): Use the distribution tools.
                """,
                expected_output="A clear, accurate response to the user's parking query based on actual tool results.",
                agent=self.analyst
            )
            crew = Crew(agents=[self.analyst], tasks=[task], verbose=True, process="sequential")
            result = crew.kickoff()
            return str(result)
        except Exception as e:
            error_str = str(e)
            if "api" in error_str.lower() or "key" in error_str.lower() or "connection" in error_str.lower():
                return f"I need an AI model to process your query. Error details: {error_str}"
            else:
                return f"Sorry, I encountered an error: {error_str}"
