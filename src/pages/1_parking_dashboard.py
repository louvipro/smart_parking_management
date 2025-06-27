import streamlit as st
import asyncio
from datetime import datetime
import pandas as pd
import time

from database.database import AsyncSessionLocal
from services.parking_service import ParkingService
from services.analytics_service import AnalyticsService
from schemas.parking import VehicleEntry, VehicleExit, SpotType


st.set_page_config(
    page_title="Parking Dashboard",
    page_icon="🚗",
    layout="wide"
)

st.title("🚗 Parking Management Dashboard")


async def get_parking_status():
    async with AsyncSessionLocal() as db:
        service = ParkingService(db)
        return await service.get_parking_status()


async def get_active_sessions():
    async with AsyncSessionLocal() as db:
        service = ParkingService(db)
        return await service.get_active_sessions()


async def get_analytics():
    async with AsyncSessionLocal() as db:
        analytics = AnalyticsService(db)
        return await analytics.get_parking_analytics()


async def register_entry(vehicle_data):
    async with AsyncSessionLocal() as db:
        service = ParkingService(db)
        return await service.register_vehicle_entry(vehicle_data)


async def register_exit(exit_data):
    async with AsyncSessionLocal() as db:
        service = ParkingService(db)
        return await service.register_vehicle_exit(exit_data)


# Get current status
status = asyncio.run(get_parking_status())
analytics = asyncio.run(get_analytics())
active_sessions = asyncio.run(get_active_sessions())

# Calculate potential revenue
current_time = datetime.utcnow()
potential_revenue = sum([
    max(1.0, (current_time - s.entry_time).total_seconds() / 3600) * s.hourly_rate
    for s in active_sessions
]) if active_sessions else 0

# Main dashboard metrics
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Total Spots",
        status.total_spots,
        delta=None
    )

with col2:
    st.metric(
        "Occupied",
        status.occupied_spots,
        delta=f"{status.occupancy_rate}%"
    )

with col3:
    st.metric(
        "Available",
        status.available_spots,
        delta=None
    )

with col4:
    st.metric(
        "Today's Revenue",
        f"${analytics['today_revenue']:.2f}",
        delta=f"{analytics['today_vehicles']} vehicles"
    )

with col5:
    st.metric(
        "Potential Revenue",
        f"${potential_revenue:.2f}",
        delta=f"{len(active_sessions)} active",
        help="Revenue if all current vehicles exit now"
    )

# Tabs for different functions
tab1, tab2, tab3, tab4 = st.tabs(["Vehicle Entry/Exit", "Current Status", "Floor Overview", "Analytics"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚦 Vehicle Entry")
        with st.form("entry_form"):
            license_plate = st.text_input("License Plate", placeholder="ABC-123")
            color = st.text_input("Vehicle Color", placeholder="Blue")
            brand = st.text_input("Vehicle Brand", placeholder="Toyota")
            spot_type = st.selectbox("Spot Type", options=[e.value for e in SpotType])
            
            if st.form_submit_button("Register Entry", type="primary"):
                if license_plate and color and brand:
                    try:
                        vehicle_data = VehicleEntry(
                            license_plate=license_plate,
                            color=color,
                            brand=brand,
                            spot_type=spot_type
                        )
                        session = asyncio.run(register_entry(vehicle_data))
                        st.success(f"✅ Vehicle {license_plate} assigned to spot {session.parking_spot.spot_number}")
                        st.balloons()
                        # Force refresh to update metrics
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.error("Please fill all fields")
    
    with col2:
        st.subheader("🚪 Vehicle Exit")
        with st.form("exit_form"):
            exit_license = st.text_input("License Plate", placeholder="ABC-123", key="exit_plate")
            
            if st.form_submit_button("Register Exit", type="primary"):
                if exit_license:
                    try:
                        exit_data = VehicleExit(license_plate=exit_license)
                        payment = asyncio.run(register_exit(exit_data))
                        st.success(f"✅ Vehicle {payment.license_plate} exited")
                        st.info(f"Duration: {payment.duration_hours:.2f} hours")
                        st.info(f"💰 Amount Due: ${payment.amount_due:.2f}")
                        # Wait a moment to show the info, then refresh
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
                else:
                    st.error("Please enter license plate")

with tab2:
    st.subheader("🚗 Currently Parked Vehicles")
    
    sessions = asyncio.run(get_active_sessions())
    
    if sessions:
        # Calculate potential revenue for each session
        current_time = datetime.utcnow()
        df_sessions = pd.DataFrame([
            {
                "License Plate": s.vehicle.license_plate,
                "Color": s.vehicle.color,
                "Brand": s.vehicle.brand,
                "Spot": s.parking_spot.spot_number,
                "Floor": s.parking_spot.floor,
                "Entry Time": s.entry_time.strftime("%Y-%m-%d %H:%M"),
                "Duration (hours)": round((current_time - s.entry_time).total_seconds() / 3600, 2),
                "Potential Revenue": f"${max(1.0, (current_time - s.entry_time).total_seconds() / 3600) * s.hourly_rate:.2f}"
            }
            for s in sessions
        ])
        
        # Calculate total potential revenue
        total_potential = sum([
            max(1.0, (current_time - s.entry_time).total_seconds() / 3600) * s.hourly_rate
            for s in sessions
        ])
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.dataframe(df_sessions, use_container_width=True)
        with col2:
            st.metric("💰 Total Potential Revenue", f"${total_potential:.2f}")
    else:
        st.info("No vehicles currently parked")

with tab3:
    st.subheader("🏢 Floor Overview")
    
    # Create floor visualization
    floors_data = []
    for floor in status.floors:
        floors_data.extend([
            {"Floor": f"Floor {floor['floor']}", "Status": "Occupied", "Count": floor['occupied']},
            {"Floor": f"Floor {floor['floor']}", "Status": "Available", "Count": floor['available']}
        ])
    
    df_floors = pd.DataFrame(floors_data)
    
    # Use Streamlit's native bar chart
    st.bar_chart(
        df_floors.pivot(index="Floor", columns="Status", values="Count"),
        color=["#FF6B6B", "#4ECDC4"]
    )

with tab4:
    st.subheader("📊 Parking Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Occupancy visualization
        st.metric("Occupancy Rate", f"{status.occupancy_rate}%", delta=f"{status.occupied_spots} vehicles")
        
        # Progress bar for occupancy
        st.progress(status.occupancy_rate / 100)
        
        # Occupancy breakdown
        occupancy_data = pd.DataFrame({
            'Status': ['Occupied', 'Available'],
            'Count': [status.occupied_spots, status.available_spots]
        })
        st.bar_chart(occupancy_data.set_index('Status'))
    
    with col2:
        # Today's metrics
        st.metric("Average Duration Today", f"{analytics['average_duration_hours']:.2f} hours")
        st.metric("Vehicles Today", analytics['today_vehicles'])
        st.metric("Current Occupancy", analytics['current_occupancy'])
        
        # Show floor breakdown
        st.write("**Floor Breakdown:**")
        for floor in status.floors:
            st.write(f"Floor {floor['floor']}: {floor['occupied']}/{floor['total']} occupied")