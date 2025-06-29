import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re

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

# --- Tool-specific functions ---
def get_total_parked_vehicles() -> str:
    async def _get():
        async with AsyncSessionLocal() as db:
            s_repo = SQLAlchemyParkingSessionRepository(db)
            analytics = AnalyticsService(None, s_repo, None)
            count = await analytics.get_current_vehicle_count()
            return f"There are currently {count} vehicles parked."
    return run_async_in_sync(_get())

def get_available_parking_spots() -> str:
    async def _get():
        async with AsyncSessionLocal() as db:
            p_repo = SQLAlchemyParkingSpotRepository(db)
            service = ParkingService(None, p_repo, None)
            status = await service.get_parking_status()
            return f"There are {status['available_spots']} spots available out of {status['total_spots']} total."
    return run_async_in_sync(_get())

def count_vehicles_by_color(color: str) -> str:
    async def _get():
        async with AsyncSessionLocal() as db:
            v_repo = SQLAlchemyVehicleRepository(db)
            analytics = AnalyticsService(v_repo, None, None)
            count = await analytics.count_vehicles_by_color(color, active_only=True)
            return f"There are {count} {color} cars parked."
    return run_async_in_sync(_get())

def get_brand_distribution() -> str:
    async def _get():
        async with AsyncSessionLocal() as db:
            v_repo = SQLAlchemyVehicleRepository(db)
            analytics = AnalyticsService(v_repo, None, None)
            dist = await analytics.get_brand_distribution(active_only=True)
            if not dist:
                return "No brand data available for currently parked vehicles."
            return "Brand Distribution:\n" + "\n".join([f"- {brand}: {count}" for brand, count in dist.items()])
    return run_async_in_sync(_get())

# --- Tool definitions ---
tool_total_parked = Tool(name="get_total_parked_vehicles", func=lambda _: get_total_parked_vehicles(), description="Use to get the total number of vehicles currently parked.")
tool_available_spots = Tool(name="get_available_parking_spots", func=lambda _: get_available_parking_spots(), description="Use to find out how many parking spots are currently available.")
tool_count_by_color = Tool(name="count_vehicles_by_color", func=lambda color: count_vehicles_by_color(color), description="Use to count parked vehicles of a specific color.")
tool_brand_distribution = Tool(name="get_brand_distribution", func=lambda _: get_brand_distribution(), description="Use to see the breakdown of car brands currently parked.")

class ParkingAssistant:
    def __init__(self):
        model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        api_key = os.getenv("OPENAI_API_KEY", "dummy")
        base_url = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")

        if "ollama" in model_name.lower():
            self.llm = ChatOpenAI(model=model_name.replace("ollama/", ""), openai_api_key="dummy", openai_api_base=base_url, temperature=0.1)
        elif api_key and api_key != "dummy":
            self.llm = ChatOpenAI(model=model_name, openai_api_key=api_key, temperature=0.1)
        else:
            raise ValueError("No valid LLM configuration found.")

    def _select_tool_and_input(self, query: str) -> (Tool, str):
        """Selects the right tool and determines the input based on the user's query."""
        query = query.lower()
        
        color_match = re.search(r'\b(red|blue|green|black|white|yellow|silver)\b', query)
        if color_match and "how many" in query:
            return tool_count_by_color, color_match.group(1)

        if "brand" in query or "repartition" in query:
            return tool_brand_distribution, query

        if "available" in query or "spots" in query or "places" in query:
            return tool_available_spots, query

        if "how many" in query and "car" in query:
            return tool_total_parked, query
            
        return None, None

    def process_query(self, query: str) -> str:
        """Process a user query using a dynamically created specialist agent."""
        
        selected_tool, tool_input = self._select_tool_and_input(query)

        if not selected_tool:
            return "I'm sorry, I can only answer questions about the number of cars, available spots, colors, or brands."

        specialist_agent = Agent(
            role='Parking Data Specialist',
            goal=f'Execute the assigned tool to answer the query: "{query}"',
            backstory='You are a specialist agent with a single tool. Your job is to execute it and return the result.',
            verbose=True,
            tools=[selected_tool],
            llm=self.llm,
            max_iter=2,
            allow_delegation=False
        )

        task = Task(
            description=f'Use your tool to answer the query: "{query}". The specific input for your tool is: "{tool_input}"',
            expected_output='The direct result from executing the tool.',
            agent=specialist_agent
        )

        crew = Crew(agents=[specialist_agent], tasks=[task], process="sequential")
        result = crew.kickoff()
        return str(result)
