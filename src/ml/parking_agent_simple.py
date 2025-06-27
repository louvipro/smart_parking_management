import os
import asyncio
from typing import Dict, Any
from datetime import datetime

from database.database import AsyncSessionLocal
from services.analytics_service import AnalyticsService
from services.parking_service import ParkingService


class SimpleParkingAssistant:
    """Simple parking assistant without CrewAI."""
    
    def __init__(self):
        pass
    
    async def process_query(self, query: str) -> str:
        """Process a user query with simple pattern matching."""
        query_lower = query.lower()
        
        try:
            # Check for color-related queries
            colors = ['red', 'blue', 'black', 'white', 'green', 'yellow', 'silver', 'gray', 'grey']
            for color in colors:
                if color in query_lower and any(word in query_lower for word in ['how many', 'count', 'number']):
                    async with AsyncSessionLocal() as db:
                        analytics = AnalyticsService(db)
                        count = await analytics.count_vehicles_by_color(color, active_only=True)
                        return f"There are currently {count} {color} cars in the parking."
            
            # Check for total count queries
            if any(phrase in query_lower for phrase in ['how many cars', 'how many vehicles', 'total cars', 'total vehicles', 'current count']):
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    count = await analytics.get_current_vehicle_count()
                    return f"There are currently {count} vehicles parked."
            
            # Check for revenue queries
            if 'revenue' in query_lower:
                hours = 24  # Default to 24 hours
                # Try to extract hours from query
                for word in query.split():
                    if word.isdigit():
                        hours = int(word)
                        break
                
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    revenue = await analytics.get_revenue_last_hours(hours)
                    return f"Revenue generated in the last {hours} hour(s): ${revenue:.2f}"
            
            # Check for parking status
            if any(phrase in query_lower for phrase in ['parking status', 'available spots', 'occupancy']):
                async with AsyncSessionLocal() as db:
                    parking = ParkingService(db)
                    status = await parking.get_parking_status()
                    return f"""Current Parking Status:
- Total spots: {status['total_spots']}
- Available spots: {status['available_spots']}
- Occupied spots: {status['occupied_spots']}
- Occupancy rate: {status['occupancy_percentage']:.1f}%"""
            
            # Check for daily average
            if 'daily average' in query_lower or 'average per day' in query_lower:
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    avg = await analytics.get_daily_average_vehicles()
                    return f"Average number of vehicles per day (last 30 days): {avg:.1f}"
            
            # Check for average spending
            if 'average spending' in query_lower or 'spend' in query_lower:
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    avg = await analytics.get_average_spending_per_day()
                    return f"Average spending per day: ${avg:.2f}"
            
            # Check for duration by color
            if 'duration' in query_lower:
                for color in colors:
                    if color in query_lower:
                        async with AsyncSessionLocal() as db:
                            analytics = AnalyticsService(db)
                            duration = await analytics.get_average_duration_by_color(color)
                            return f"Average parking duration for {color} cars: {duration:.2f} hours"
            
            # Check for today's analytics
            if 'today' in query_lower and any(word in query_lower for word in ['analytics', 'summary', 'report']):
                async with AsyncSessionLocal() as db:
                    analytics = AnalyticsService(db)
                    data = await analytics.get_parking_analytics()
                    return f"""Today's Analytics:
- Revenue: ${data['today_revenue']:.2f}
- Vehicles: {data['today_vehicles']}
- Current occupancy: {data['current_occupancy']}
- Average duration: {data['average_duration_hours']:.2f} hours"""
            
            # Default response
            return """I can help you with:
- How many cars are currently parked?
- How many [color] cars are in the parking?
- What's the revenue from the last [N] hours?
- What's the parking status?
- What's the daily average number of vehicles?
- What's today's analytics summary?

Please ask a specific question about the parking system."""
            
        except Exception as e:
            return f"Sorry, I encountered an error while processing your query: {str(e)}"