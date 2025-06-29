import sys
import os

# Add the project root to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from src.infrastructure.persistence.database import init_db

# Initialize database on startup
init_db()

st.set_page_config(
    page_title="Parking Management System",
    page_icon="🚗",
    layout="wide"
)

st.write("# 🚗 Parking Management System")

st.write(
    """Welcome to the Parking Management System! This application helps manage parking operations with real-time tracking and AI-powered analytics.

## Features:

### 🚦 Parking Operations
- **Vehicle Entry/Exit**: Register vehicles entering and exiting the parking
- **Real-time Status**: View current parking occupancy and available spots
- **Payment Processing**: Automatic calculation of parking fees

### 🤖 AI Assistant
- Ask questions about parking status in natural language
- Get insights about revenue, occupancy, and vehicle patterns
- Analyze parking data with intelligent queries

### 📊 Analytics Dashboard
- Real-time occupancy visualization
- Revenue tracking and reporting
- Vehicle statistics by color, brand, and duration

## Getting Started:
1. Navigate to **Parking Dashboard** to manage vehicle entries and exits
2. Visit **AI Assistant** to ask questions about the parking system
3. Check the **Analytics** section for detailed insights

The system tracks vehicles by license plate, color, and brand, automatically assigns parking spots, and calculates fees based on duration.
"""
)
