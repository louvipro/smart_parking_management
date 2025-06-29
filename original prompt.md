# Technical Test: Parking Management System with AI Agent

## Project Overview
Create a web application in Python 3.12 that manages a parking system lifecycle and includes an AI conversational agent for querying parking data.

## Core Functionalities

### Parking Management System
Track vehicle entries with timestamps
Track vehicle exits with timestamps and payment calculation
Vehicle definition: color and brand
Real-time parking status management

### AI Conversational Agent (Chatbot)
The chatbot should answer queries like:

"How many blue cars are currently in the parking?"
"How much money have we generated in the last hour?"
"How many cars are currently parked?"
"What's the average daily number of cars using the parking?"
"What's the average daily spending per user?"
"What's the average parking duration for black cars?"

## Technical Requirements

### Mandatory Technologies
Python 3.12
Streamlit for web framework
CrewAI (https://www.crewai.com/) for AI agent system
LiteLLM (https://www.litellm.ai) for LLM calls
FastAPI (optional backend)
Pydantic for data validation
Docker with Dockerfile for containerization

### Code Quality Standards
Code must be in English exclusively
Minimal comments (self-explanatory code preferred)
Clean, production-ready code structure
Proper async/await implementation using Python's asynchronous features
Public GitHub repository

### Deliverables
Complete application with all functionalities
README.md with setup and launch instructions
Dockerfile ready for Kubernetes deployment
GitHub repository (public)

## Timeline & Expectations
Deadline: June 30th, midnight
Expected: Project may not be fully complete - this is normal
Required: If incomplete, provide:
List of remaining tasks
Prioritization strategy for remaining work
Follow-up: 1-hour debrief meeting after deadline

## Focus Areas for Assessment
Code quality and production readiness
Architecture design for parking system
AI agent integration and query handling
Asynchronous programming implementation
Docker containerization approach
Documentation clarity

## Suggested Action Plan Structure
Please create a detailed development plan including:

Project architecture overview (clean architecture)
Testing approach (test driven development)
Database/data storage strategy
Streamlit UI structure
CrewAI agent configuration
Development phases and priorities
Deployment considerations