import os
import re
from typing import Dict, Any
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from crewai import Agent, Task, Crew
from langchain.tools import Tool
from langchain_openai import ChatOpenAI
import litellm

from database.database import AsyncSessionLocal
from services.analytics_service import AnalyticsService
from services.parking_service import ParkingService
from ml.parking_agent_direct import DirectParkingAssistant


class HybridParkingAssistant:
    """Hybrid parking assistant that uses CrewAI with fallback to direct processing."""
    
    def __init__(self):
        # Initialize direct assistant for fallback
        self.direct_assistant = DirectParkingAssistant()
        
        # Configure the LLM
        model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo")
        api_key = os.getenv("OPENAI_API_KEY", "dummy")
        
        self.use_crewai = True
        
        if "ollama" in model_name:
            # For smaller Ollama models, use direct processing
            if "0.5b" in model_name or "1b" in model_name:
                self.use_crewai = False
                return
            
            # For larger models, try CrewAI
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
        
        if self.use_crewai:
            # Create tools for the agent
            self.tools = self._create_tools()
            
            # Create the parking data analyst agent
            self.analyst = Agent(
                role='Parking Data Analyst',
                goal='Analyze parking data and provide accurate information to users',
                backstory="""You are an expert parking system analyst. You MUST use the provided tools to get real data. 
                NEVER make up numbers. Always call the appropriate tool and use its exact output.""",
                verbose=True,
                allow_delegation=False,
                tools=self.tools,
                llm=self.llm,
                max_iter=3
            )
    
    def _create_tools(self) -> list:
        """Create simplified tools that directly use the direct assistant."""
        
        def process_parking_query(query: str) -> str:
            """Process any parking-related query and return accurate data."""
            print(f"[TOOL CALLED] process_parking_query with: {query}")
            
            # Run the direct assistant synchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.direct_assistant.process_query(query))
                print(f"[TOOL RESULT] {result}")
                return result
            finally:
                loop.close()
        
        # Create a single tool that handles all queries
        return [
            Tool(
                name="process_parking_query",
                func=process_parking_query,
                description="Process any parking-related query. Pass the user's exact question to get accurate parking data."
            )
        ]
    
    async def process_query(self, query: str) -> str:
        """Process a user query using CrewAI or direct processing."""
        
        # If CrewAI is disabled or for simple queries, use direct processing
        if not self.use_crewai:
            return await self.direct_assistant.process_query(query)
        
        try:
            # Create a task for the query
            task = Task(
                description=f"""Answer this parking system query using the process_parking_query tool:
                
                User Query: {query}
                
                IMPORTANT: You MUST use the 'process_parking_query' tool with the user's exact query to get real data.
                Do NOT make up any numbers or information. Use only the data returned by the tool.""",
                expected_output="An accurate response based on the tool's output",
                agent=self.analyst
            )
            
            # Create and run the crew
            crew = Crew(
                agents=[self.analyst],
                tasks=[task],
                verbose=True
            )
            
            # Execute and return result
            result = crew.kickoff()
            
            # If the result looks like hallucination (contains made-up numbers), fall back
            result_str = str(result)
            if any(fake_num in result_str for fake_num in ['10000', '1000 toyota', '4800', 'toyota vehicles']):
                print("[FALLBACK] Detected hallucination, using direct processing")
                return await self.direct_assistant.process_query(query)
            
            return result_str
            
        except Exception as e:
            print(f"[ERROR] CrewAI failed: {e}, falling back to direct processing")
            return await self.direct_assistant.process_query(query)