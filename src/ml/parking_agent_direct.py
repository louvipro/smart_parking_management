import os
import re
from typing import Dict, Any
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from database.database import AsyncSessionLocal
from services.analytics_service import AnalyticsService
from services.parking_service import ParkingService


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


class DirectParkingAssistant:
    """Direct parking assistant that processes queries without LLM hallucination."""
    
    def __init__(self):
        pass
    
    async def get_current_count(self) -> int:
        """Get the current number of vehicles."""
        async with AsyncSessionLocal() as db:
            analytics = AnalyticsService(db)
            return await analytics.get_current_vehicle_count()
    
    async def count_by_color(self, color: str) -> int:
        """Count vehicles by color."""
        async with AsyncSessionLocal() as db:
            analytics = AnalyticsService(db)
            return await analytics.count_vehicles_by_color(color.lower(), active_only=True)
    
    async def get_revenue(self, hours: int) -> float:
        """Get revenue for the last N hours."""
        async with AsyncSessionLocal() as db:
            analytics = AnalyticsService(db)
            return await analytics.get_revenue_last_hours(hours)
    
    async def get_parking_status(self) -> dict:
        """Get parking status."""
        async with AsyncSessionLocal() as db:
            parking = ParkingService(db)
            return await parking.get_parking_status()
    
    async def get_all_colors(self) -> dict:
        """Get count of all colors."""
        colors = ['red', 'blue', 'black', 'white', 'green', 'yellow', 'silver', 'gray', 'grey']
        result = {}
        
        async with AsyncSessionLocal() as db:
            analytics = AnalyticsService(db)
            for color in colors:
                count = await analytics.count_vehicles_by_color(color, active_only=True)
                if count > 0:
                    result[color] = count
        
        return result
    
    async def get_brand_distribution(self) -> dict:
        """Get distribution of vehicles by brand."""
        async with AsyncSessionLocal() as db:
            analytics = AnalyticsService(db)
            return await analytics.get_brand_distribution(active_only=True)
    
    async def get_floor_distribution(self) -> dict:
        """Get distribution of vehicles by floor."""
        async with AsyncSessionLocal() as db:
            analytics = AnalyticsService(db)
            return await analytics.get_floor_distribution(active_only=True)
    
    async def process_query(self, query: str) -> str:
        """Process a user query directly."""
        query_lower = query.lower()
        
        try:
            # Handle Toyota/brand queries
            if 'toyota' in query_lower or any(brand in query_lower for brand in ['honda', 'ford', 'bmw', 'mercedes']):
                if 'color' in query_lower or 'repartition' in query_lower:
                    # Get all colors
                    colors = await self.get_all_colors()
                    total = await self.get_current_count()
                    
                    if not colors:
                        return "There are no vehicles currently in the parking."
                    
                    response = f"Current color distribution in the parking (total {total} vehicles):\n"
                    for color, count in colors.items():
                        percentage = (count / total * 100) if total > 0 else 0
                        response += f"- {color.capitalize()}: {count} vehicles ({percentage:.1f}%)\n"
                    
                    response += "\nNote: I track vehicles by color, not by brand. The actual brand distribution would require different data tracking."
                    return response
            
            # Handle color-specific queries
            colors = ['red', 'blue', 'black', 'white', 'green', 'yellow', 'silver', 'gray', 'grey']
            for color in colors:
                if color in query_lower and any(word in query_lower for word in ['how many', 'count', 'number']):
                    count = await self.count_by_color(color)
                    return f"There are currently {count} {color} cars in the parking."
            
            # Handle total count
            if any(phrase in query_lower for phrase in ['how many cars', 'how many vehicles', 'total cars', 'total vehicles']):
                count = await self.get_current_count()
                return f"There are currently {count} vehicles in the parking."
            
            # Handle revenue
            if 'revenue' in query_lower:
                # Try to extract hours
                hours = 24  # default
                numbers = re.findall(r'\d+', query)
                if numbers:
                    hours = int(numbers[0])
                
                revenue = await self.get_revenue(hours)
                return f"Revenue generated in the last {hours} hour(s): ${revenue:.2f}"
            
            # Handle parking status
            if any(phrase in query_lower for phrase in ['parking status', 'available spots', 'occupancy']):
                status = await self.get_parking_status()
                return f"""Current Parking Status:
- Total spots: {status['total_spots']}
- Available spots: {status['available_spots']}
- Occupied spots: {status['occupied_spots']}
- Occupancy rate: {status['occupancy_percentage']:.1f}%"""
            
            # Handle brand distribution/repartition
            if 'brand' in query_lower and ('distribution' in query_lower or 'repartition' in query_lower):
                brands = await self.get_brand_distribution()
                total = await self.get_current_count()
                
                if not brands:
                    return "There are no vehicles currently in the parking."
                
                response = f"Current brand distribution (total {total} vehicles):\n"
                for brand, count in brands.items():
                    percentage = (count / total * 100) if total > 0 else 0
                    response += f"- {brand}: {count} vehicles ({percentage:.1f}%)\n"
                
                return response
            
            # Handle floor distribution/repartition
            if 'floor' in query_lower and ('distribution' in query_lower or 'repartition' in query_lower):
                floors = await self.get_floor_distribution()
                total = await self.get_current_count()
                
                if not floors:
                    return "There are no vehicles currently in the parking."
                
                response = f"Current floor distribution (total {total} vehicles):\n"
                for floor, count in sorted(floors.items()):
                    percentage = (count / total * 100) if total > 0 else 0
                    response += f"- Floor {floor}: {count} vehicles ({percentage:.1f}%)\n"
                
                return response
            
            # Handle color distribution/repartition
            if 'color' in query_lower and ('distribution' in query_lower or 'repartition' in query_lower):
                colors = await self.get_all_colors()
                total = await self.get_current_count()
                
                if not colors:
                    return "There are no vehicles currently in the parking."
                
                response = f"Current color distribution (total {total} vehicles):\n"
                for color, count in colors.items():
                    percentage = (count / total * 100) if total > 0 else 0
                    response += f"- {color.capitalize()}: {count} vehicles ({percentage:.1f}%)\n"
                
                return response
            
            # Default response
            return """I can help you with:
- How many cars are currently parked?
- How many [color] cars are in the parking?
- What's the color distribution?
- What's the brand distribution?
- What's the floor distribution?
- What's the revenue from the last [N] hours?
- What's the parking status?

Please ask a specific question about the parking system."""
            
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"