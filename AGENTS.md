# GEMINI.md

This file provides guidance to Gemini when working with the Smart Parking Management System codebase.

## Project Overview

This is a **Smart Parking Management System** featuring a Streamlit frontend for user interaction and a FastAPI backend for handling the core logic. The system manages parking operations, including vehicle entry and exit, payment processing, and spot allocation. A key feature is an AI-powered assistant that allows users to query parking data using natural language.

## Development Commands

The project uses a `Makefile` to streamline common tasks.

### Application
- **Run Frontend (Streamlit):** `make run-frontend`
- **Run Both:** `make run-app`
- **Initialize Database:** `python src/init_database.py`

### Testing & Quality
- **Run Tests:** `make test`
- **Run Pre-commit Checks:** `make pre-commit`
- **Install Hooks:** `make pre-commit-install`

### Docker
- **Build and Run:** `make docker-compose`
- **Development Container:** `make docker-dev`
- **Production Container:** `make docker-prod`

## High-Level Architecture

### Core Components
1.  **Streamlit Frontend (`src/main_frontend.py`):** Provides a user interface for the parking dashboard and the AI assistant.
2.  **FastAPI Backend (`src/main_backend.py`):** A RESTful API for all parking operations and analytics.
3.  **Database (`src/database/`):** Uses SQLAlchemy and contains models for `Vehicle`, `ParkingSpot`, and `ParkingSession`.
4.  **Services (`src/services/`):**
    *   `ParkingService`: Manages core logic for vehicle entry, exit, and spot assignment.
    *   `AnalyticsService`: Provides data for analytics queries.
5.  **AI Assistant (`src/ml/`):**
    *   Uses a Large Language Model (LLM) to understand and respond to user queries about parking data.
    *   Integrates with the database to provide real-time information.

### Configuration
- **Dependencies:** Managed in `pyproject.toml` with `uv`.
- **Environment Variables:** Loaded from a `.env` file (based on `.env.example`). See `src/settings_env.py`.
- **Pre-commit Hooks:** Configured in `.pre-commit-config.yaml`.

## Development Workflow

1.  **Setup:** Copy `.env.example` to `.env` and configure the necessary variables (database URL, parking settings, LLM provider).
2.  **Dependencies:** Run `make install-dev` to install dependencies using `uv`.
3.  **Database:** Run `python src/init_database.py` to set up the database schema and initial data.
4.  **Coding:** Make changes to the source code in `src/`.
5.  **Testing:** Run `make test` to ensure changes haven't broken existing functionality.
6.  **Linting/Formatting:** Run `make pre-commit` to ensure code quality before committing.
