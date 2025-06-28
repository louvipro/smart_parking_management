# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Parking Management System codebase.

## Project Overview

This is a **Parking Management System** with an AI-powered conversational agent. The system manages parking operations (vehicle entry/exit, payment processing, spot allocation) and includes a CrewAI-based assistant for natural language queries about parking data.

## Common Development Commands

### Running the Application
```bash
# Initialize the database (first time setup)
python src/init_database.py

# Run frontend only (Streamlit)
make run-frontend

# Run backend API (FastAPI)
make run-backend

# Run both frontend and backend
make run-app

# Run with local models (Ollama)
make run-ollama  # Start Ollama server
make download-ollama-model OLLAMA_MODEL_NAME=llama3.2:1b  # Download a model
```

### Testing and Quality Checks
```bash
# Run all tests
make test

# Run pre-commit checks (linting, formatting, secrets detection)
make pre-commit

# Install pre-commit hooks
make pre-commit-install
```

### Docker Development
```bash
# Build and run with docker-compose (includes Ollama)
make docker-compose

# Run development container
make docker-dev

# Run production container
make docker-prod
```

## High-Level Architecture

### Application Structure
The Parking Management System consists of:

1. **Streamlit Frontend** (`src/main_frontend.py`):
   - Parking Dashboard: Vehicle entry/exit, payment processing
   - AI Assistant: Natural language queries about parking data
   - Real-time parking status visualization

2. **FastAPI Backend** (`src/main_backend.py` + `src/api/`):
   - RESTful API for parking operations
   - Analytics endpoints
   - Async database operations

3. **Docker Deployment**:
   - Multi-container setup with parking app + Ollama
   - Production-ready with health checks

### Key Components

**Database Models** (`src/database/models.py`):
- `Vehicle`: License plate, color, brand information
- `ParkingSpot`: Spot details (number, floor, type, availability)
- `ParkingSession`: Tracks entry/exit times, payments, spot assignments

**Services Layer**:
- `ParkingService` (`src/services/parking_service.py`): Core parking operations
- `AnalyticsService` (`src/services/analytics_service.py`): Revenue and occupancy analytics

**AI Assistant** (`src/ml/parking_agent_*.py`):
- Multiple implementations: CrewAI-based, direct, hybrid
- Natural language processing for parking queries
- Tools for accessing real-time parking data
- Supports questions about:
  - Vehicle counts (total and by color)
  - Revenue analytics
  - Parking occupancy and availability
  - Color distribution

**API Endpoints** (`src/api/routers/parking.py`):
- `POST /api/parking/entry`: Register vehicle entry
- `POST /api/parking/exit/{license_plate}`: Process exit and payment
- `GET /api/parking/status`: Current parking status
- `GET /api/parking/analytics/*`: Various analytics endpoints

**Settings System** (`src/settings_env.py`):
- Environment-based configuration
- Parking-specific settings (hourly rate, floors, spots)
- LLM configuration for AI assistant

### Development Workflow

1. **Environment Setup**: 
   - Copy `.env.example` to `.env`
   - Configure LLM settings (OpenAI API key or Ollama)
   - Set parking parameters (HOURLY_RATE, PARKING_FLOORS, SPOTS_PER_FLOOR)

2. **Database Initialization**:
   ```bash
   python src/init_database.py  # Creates tables and sample parking spots
   ```

3. **Dependency Management**: 
   - Uses UV package manager
   - Run `make install-dev` for development setup

4. **Code Quality**: 
   - Pre-commit hooks enforce Ruff formatting
   - Conventional commits required
   - Security checks for secrets

5. **Testing**: 
   - pytest with async support
   - Tests located in `tests/`

### Important Configuration Files
- `pyproject.toml`: Package dependencies, tool configurations
- `.pre-commit-config.yaml`: Pre-commit hooks configuration
- `Makefile`: All development commands and workflows
- `.env`: Environment variables (create from `.env.example`)
- `docker-compose.yml`: Multi-container orchestration

### Environment Variables

Key parking-specific configurations:
```env
# Database
DATABASE_URL=sqlite:///./parking.db
ASYNC_DATABASE_URL=sqlite+aiosqlite:///./parking.db

# Parking Configuration
HOURLY_RATE=5.0
PARKING_FLOORS=3
SPOTS_PER_FLOOR=20

# LLM Configuration (for AI Assistant)
OPENAI_API_BASE=http://localhost:11434/v1
OPENAI_MODEL_NAME=ollama/llama3.2:1b
OPENAI_API_KEY=dummy  # Required for Ollama compatibility
```

### AI Assistant Notes

1. **Model Selection**:
   - For Ollama: Use llama3.2:1b or larger for tool usage
   - Smaller models (0.5b) may not handle CrewAI tools properly

2. **Tool Usage**:
   - The assistant has tools to query real parking data
   - Ensures accurate responses based on database state
   - Fallback mechanisms for reliability

3. **Query Types Supported**:
   - "How many cars are currently parked?"
   - "How many [color] cars are there?"
   - "What's the revenue from the last N hours?"
   - "What's the parking status?"
   - "Show me the color distribution"

### Common Issues and Solutions

1. **AI Assistant Hallucinating**:
   - Ensure using llama3.2:1b or larger model
   - Check that Ollama is running (`make run-ollama`)
   - The hybrid agent will fallback to direct queries if needed

2. **Database Not Found**:
   - Run `python src/init_database.py` to initialize
   - Check DATABASE_URL in .env

3. **Slow AI Responses**:
   - First load of Ollama models can be slow
   - Consider using smaller models for development
   - Or use OpenAI API for faster responses