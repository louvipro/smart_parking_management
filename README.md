# 🚗 Smart Parking Management System

Welcome to the Smart Parking Management System! This project provides a complete web application to manage a parking facility, enhanced with an AI-powered assistant to query data using natural language.

---

### 📖 Table of Contents
- [✨ Features](#-features)
- [💻 Technology Stack](#-technology-stack)
- [🚀 Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation & Setup](#installation--setup)
- [🏃 Running the Application](#-running-the-application)
- [🐳 Docker Deployment](#-docker-deployment)
- [🔧 Usage](#-usage)
- [⚙️ Configuration](#️-configuration)
- [🏗️ Architecture](#️-architecture)
- [🧪 Development & Testing](#-development--testing)

---

## ✨ Features

### Core Parking Management
- **Vehicle Entry/Exit**: Track vehicle entries and exits with precise timestamps and automatic spot assignments.
- **Payment Calculation**: Automatically calculate parking fees based on duration.
- **Real-time Dashboard**: Monitor parking occupancy, availability, and revenue in real-time.
- **Multi-floor Support**: Manage spots across multiple floors with types like Regular, Disabled, and VIP.

### 🤖 AI Conversational Assistant
Ask the AI anything about the parking status:
- "How many blue cars are currently parked?"
- "How much money was generated in the last hour?"
- "What is the current occupancy rate?"
- "What's the average parking duration for black cars?"

---

## 💻 Technology Stack

- **Python 3.12**
- **Streamlit**: For the interactive web dashboard.
- **CrewAI**: For the AI agent system.
- **LiteLLM**: As a unified interface for LLM providers (OpenAI, Ollama, etc.).
- **SQLAlchemy**: For robust, asynchronous database communication.
- **Pydantic**: For strict data validation.
- **Docker**: For containerized deployment.

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12**
- **Git**
- **Docker** (Optional, for container deployment)

### Installation & Setup

**1. Clone the Repository**
```bash
git clone https://github.com/your-username/smart-parking-management.git
cd smart-parking-management
```

**2. Create Environment File**

This file stores your API keys and configuration.

- **On macOS or Linux:**
  ```bash
  cp .env.example .env
  ```
- **On Windows:**
  ```bash
  copy .env.example .env
  ```

**3. Install Dependencies**

Dependencies are managed with `uv`. The following commands will create a virtual environment and install all required packages.

- **On macOS or Linux (Recommended):**
  ```bash
  # This command uses the Makefile to install dependencies
  make install-dev
  ```

- **On Windows (Manual):**
  ```bash
  # Install uv if you haven't already
  pip install uv
  
  # Create a virtual environment
  uv venv
  
  # Activate the virtual environment
  # (Use `.venv\Scripts\activate` for cmd, or `source .venv/bin/activate` for Git Bash/WSL)
  source .venv/bin/activate 
  
  # Sync dependencies
  uv sync
  ```

---

## 🏃 Running the Application

First, ensure your database is initialized. This command is safe to run multiple times.
```bash
python src/init_database.py
```

Then, launch the Streamlit frontend.

- **On macOS or Linux (Recommended):**
  ```bash
  make run-frontend
  ```

- **On Windows (Manual):**
  ```bash
  uv run streamlit run src/infrastructure/ui/0_Home.py
  ```

Finally, open your browser and go to **http://localhost:8501**.

---

## 🐳 Docker Deployment

The easiest way to run the entire stack, including the Ollama LLM for local AI, is with Docker Compose.

```bash
# This command builds the images and starts the services.
docker-compose up --build
```
This will start the Streamlit application and the Ollama service. You can then use a local model like `qwen2.5:0.5b` without needing an API key.

---

## 🔧 Usage

### 1. Parking Dashboard
Navigate to the **Parking Dashboard** to:
- Register vehicle entries and exits.
- View real-time parking status and floor-wise occupancy.
- Monitor revenue and vehicle flow.

### 2. AI Assistant
Navigate to the **AI Assistant** to:
- Ask natural language questions about parking data.
- Get instant insights on revenue, occupancy, and vehicle statistics.

---

## ⚙️ Configuration

All configuration is managed via the `.env` file:
- `DEV_MODE`: Set to `True` for detailed debug logging.
- `DATABASE_URL`: The connection string for your database (defaults to SQLite).
- `OPENAI_API_KEY`: Your API key for providers like OpenAI.
- `OPENAI_MODEL_NAME`: The model to use (e.g., `gpt-4o-mini`, `ollama/qwen2.5:0.5b`).
- `HOURLY_RATE`: The parking fee per hour.

---

## 🏗️ Architecture

This project follows **Clean Architecture** principles to ensure a separation of concerns, making it scalable, testable, and maintainable.

- **Domain**: Contains the core business logic and entities, with no external dependencies.
- **Application**: Orchestrates the domain logic and defines interfaces for external services.
- **Infrastructure**: Provides concrete implementations for databases, AI agents, and the UI.

---

## 🧪 Development & Testing

We use `pytest` for testing.

- **On macOS or Linux (Recommended):**
  ```bash
  make test
  ```

- **On Windows (Manual):**
  ```bash
  uv run pytest tests/
  ```