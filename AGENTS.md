# GEMINI.md

This file provides guidance to Gemini when working with the Smart Parking Management System codebase.

## Project Overview

This is a **Smart Parking Management System** featuring a Streamlit frontend for user interaction. The system manages parking operations, including vehicle entry and exit, payment processing, and spot allocation. A key feature is an AI-powered assistant that allows users to query parking data using natural language.

## Development Commands

The project uses a `Makefile` to streamline common tasks.

### Application
- **Run Frontend (Streamlit):** `make run-frontend`

- **Initialize Database:** `python src/init_database.py`

### Testing & Quality
- **Run Tests:** `make test`

### Docker
- **Build and Run:** `make docker-compose`
- **Development Container:** `make docker-dev`
- **Production Container:** `make docker-prod`

## High-Level Architecture

The project follows a **Clean Architecture** approach, emphasizing separation of concerns and test-driven development (TDD).

### Core Components
1.  **Streamlit Frontend (`src/main_frontend.py`):** Provides a user interface for the parking dashboard and the AI assistant.
2.  **Domain (`src/domain/`):** Contains core business entities (`Vehicle`, `ParkingSpot`, `ParkingSession`) and pure business rules. Independent of any technology.
3.  **Application (`src/application/`):** Defines application-specific business rules and orchestrates the domain. Contains services (e.g., `ParkingService`, `AnalyticsService`) and abstract interfaces (ports) for external dependencies.
4.  **Infrastructure (`src/infrastructure/`):** Implements the abstract interfaces defined in the Application layer. This includes concrete database implementations (SQLAlchemy), UI frameworks (Streamlit), and ML integrations (CrewAI, LiteLLM).
5.  **AI Assistant (`src/infrastructure/ml_agents/`):** (Part of Infrastructure) Uses a Large Language Model (LLM) to understand and respond to user queries about parking data. Integrates with the database to provide real-time information.

### Configuration
- **Dependencies:** Managed in `pyproject.toml` with `uv`.
- **Environment Variables:** Loaded from a `.env` file (based on `.env.example`). See `src/config/settings_env.py`.

## Development Workflow

1.  **Setup:** Copy `.env.example` to `.env` and configure the necessary variables (database URL, parking settings, LLM provider).
2.  **Dependencies:** Run `make install-dev` to install dependencies using `uv`.
3.  **Database:** Run `python src/init_database.py` to set up the database schema and initial data.
4.  **Coding:** Make changes to the source code in `src/`.
5.  **Testing:** Run `make test` to ensure changes haven't broken existing functionality.

