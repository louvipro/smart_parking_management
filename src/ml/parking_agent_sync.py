import os
import asyncio
from typing import Dict, Any
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from crewai import Agent, Task, Crew
from langchain.tools import Tool
from langchain_openai import ChatOpenAI

from database.database import AsyncSessionLocal
from services.analytics_service import AnalyticsService
from services.parking_service import ParkingService


def run_async_in_sync(coro):
    """Run async coroutine in a sync context safely."""
    # Create a new event loop in a thread
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
        
        if "ollama" in model_name:
            # For Ollama models, set the base URL
            base_url = os.getenv("OPENAI_API_BASE", "http://localhost:11434/v1")
            self.llm = ChatOpenAI(
                model=model_name.replace("ollama/", ""),
                openai_api_key="dummy",
                openai_api_base=base_url,
                temperature=0.1,
                max_tokens=2000
            )
        else:
            # For OpenAI models
            self.llm = ChatOpenAI(
                model=model_name,
                openai_api_key=api_key,
                temperature=0.1
            )
        
        # Create tools for the agent
        self.tools = self._create_tools()
        
        # Create the parking data analyst agent
        self.analyst = Agent(
            role='Parking Data Analyst',
            goal='Analyze parking data and provide accurate information to users',
            backstory="""You are an expert parking system analyst who can quickly 
            access and interpret parking data. You provide clear, accurate answers 
            about parking occupancy, revenue, and vehicle statistics.""",
            verbose=True,
            allow_delegation=False,
            tools=self.tools,
            llm=self.llm,
            max_iter=5,
            execution_mode="sequential",
            force_tool_use=True
        )
    
    def _create_tools(self) -> list:
        """Create tools for the CrewAI agent."""
        
        def get_current_count(_) -> str:
            """Get the current number of vehicles in the parking."""
            print("[TOOL CALLED] get_current_count")
            async def _get_count():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    count = await analytics.get_current_vehicle_count()
                    return count
            
            count = run_async_in_sync(_get_count())
            result = f"There are currently {count} vehicles parked."
            print(f"[TOOL RESULT] {result}")
            return result
        
        def count_by_color(color: str) -> str:
            """Count vehicles by color."""
            print(f"[TOOL CALLED] count_by_color with color: {color}")
            # Toyota is not a color, so return 0 if it's passed
            if color.lower() in ['toyota', 'honda', 'ford', 'bmw', 'mercedes']:
                return f"'{color}' is a car brand, not a color. Please ask about colors like red, blue, black, etc."
            
            async def _count_color():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    count = await analytics.count_vehicles_by_color(color.lower(), active_only=True)
                    return count
            
            count = run_async_in_sync(_count_color())
            result = f"There are {count} {color} cars currently in the parking."
            print(f"[TOOL RESULT] {result}")
            return result
        
        def get_recent_revenue(hours: str) -> str:
            """Get revenue generated in the last N hours."""
            try:
                hours_int = int(hours)
            except:
                hours_int = 1
                
            async def _get_revenue():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    revenue = await analytics.get_revenue_last_hours(hours_int)
                    return revenue
            
            revenue = run_async_in_sync(_get_revenue())
            return f"Revenue generated in the last {hours_int} hour(s): ${revenue:.2f}"
        
        def get_parking_status(_) -> str:
            """Get current parking status."""
            async def _get_status():
                async with AsyncSessionLocal() as db:
                    parking = ParkingService(db)
                    status = await parking.get_parking_status()
                    return status
            
            status = run_async_in_sync(_get_status())
            return f"""Current Parking Status:
- Total spots: {status['total_spots']}
- Available spots: {status['available_spots']}
- Occupied spots: {status['occupied_spots']}
- Occupancy rate: {status['occupancy_percentage']:.1f}%"""
        
        def get_daily_average(_) -> str:
            """Get average number of vehicles per day."""
            async def _get_average():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    avg = await analytics.get_daily_average_vehicles(30)
                    return avg
            
            average = run_async_in_sync(_get_average())
            return f"Average daily vehicles (last 30 days): {average:.1f}"
        
        def get_average_spending(_) -> str:
            """Get average spending per user per day."""
            async def _get_spending():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    avg = await analytics.get_average_daily_spending(30)
                    return avg
            
            spending = run_async_in_sync(_get_spending())
            return f"Average daily spending per user: ${spending:.2f}"
        
        def get_duration_by_color(color: str) -> str:
            """Get average parking duration for vehicles of a specific color."""
            async def _get_duration():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    duration = await analytics.get_average_duration_by_color(color)
                    return duration
            
            duration = run_async_in_sync(_get_duration())
            return f"Average parking duration for {color} cars: {duration:.2f} hours"
        
        def get_today_analytics(_) -> str:
            """Get today's parking analytics."""
            async def _get_analytics():
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    data = await analytics.get_parking_analytics()
                    return data
            
            data = run_async_in_sync(_get_analytics())
            return f"""Today's Analytics:
- Revenue: ${data['today_revenue']:.2f}
- Vehicles: {data['today_vehicles']}
- Current occupancy: {data['current_occupancy']}
- Average duration: {data['average_duration_hours']:.2f} hours"""
        
        # Create Tool objects for CrewAI
        return [
            Tool(
                name="get_current_count",
                func=get_current_count,
                description="Get the current number of vehicles in the parking"
            ),
            Tool(
                name="count_by_color",
                func=count_by_color,
                description="Count vehicles by color. Input should be a color name like 'blue', 'red', 'black', etc."
            ),
            Tool(
                name="get_revenue",
                func=get_recent_revenue,
                description="Get revenue generated in the last N hours. Input should be number of hours."
            ),
            Tool(
                name="get_parking_status",
                func=get_parking_status,
                description="Get current parking status including available spots and occupancy"
            ),
            Tool(
                name="get_daily_average",
                func=get_daily_average,
                description="Get average number of vehicles per day over the last 30 days"
            ),
            Tool(
                name="get_average_spending",
                func=get_average_spending,
                description="Get average spending per user per day"
            ),
            Tool(
                name="get_duration_by_color",
                func=get_duration_by_color,
                description="Get average parking duration for vehicles of a specific color"
            ),
            Tool(
                name="get_today_analytics",
                func=get_today_analytics,
                description="Get today's parking analytics including revenue and vehicle count"
            )
        ]
    
    async def process_query(self, query: str) -> str:
        """Process a user query using CrewAI."""
        try:
            # Create a task for the query
            task = Task(
                description=f"""You must analyze this parking system query and use the appropriate tools to answer it:
                
                User Query: {query}
                
                IMPORTANT: You MUST use the tools available to get real data. Do not make up information.
                
                Instructions for tool usage:
                - For questions about specific car colors (red, blue, black, etc): Use the 'count_by_color' tool with the color as input
                - For questions about total cars: Use the 'get_current_count' tool with any input
                - For questions about revenue: Use the 'get_revenue' tool with number of hours as input
                - For questions about parking status: Use the 'get_parking_status' tool with any input
                - For questions about averages: Use the 'get_daily_average' or 'get_average_spending' tools with any input
                
                Always use tools before providing an answer. The tools will give you real-time data.
                Provide a direct answer based on the tool results.""",
                expected_output="A clear, accurate response to the user's parking query based on actual tool results",
                agent=self.analyst
            )
            
            # Create and run the crew
            crew = Crew(
                agents=[self.analyst],
                tasks=[task],
                verbose=True,
                process="sequential"
            )
            
            # Execute and return result
            result = crew.kickoff()
            return str(result)
            
        except Exception as e:
            error_str = str(e)
            print(f"CrewAI Error: {error_str}")  # Debug log
            
            # Provide helpful error message
            if "api" in error_str.lower() or "key" in error_str.lower() or "connection" in error_str.lower():
                return f"""I need an AI model to process your query. 

**Current configuration:**
- Model: {os.getenv('OPENAI_MODEL_NAME', 'Not set')}
- API Base: {os.getenv('OPENAI_API_BASE', 'Not set')}

**To fix this, please ensure either:**

1. **For OpenAI**: Set OPENAI_API_KEY in your .env file
2. **For Ollama**: 
   - Run `make run-ollama` to start Ollama
   - Run `make download-ollama-model` to download a model
   - Set `OPENAI_MODEL_NAME=ollama/qwen2.5:0.5b` in .env

**Error details**: {error_str}

You can still view parking data in the Dashboard tab!"""
            else:
                return f"Sorry, I encountered an error: {error_str}"