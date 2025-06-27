# 🚗 Smart Parking Management

A web application built with Python 3.12 that manages a parking system lifecycle and includes an AI conversational agent for querying parking data.

## Features

### Core Functionalities

- **Vehicle Entry/Exit Management**: Track vehicles with timestamps and automatic spot assignment
- **Payment Calculation**: Automatic fee calculation based on parking duration
- **Real-time Status**: Monitor parking occupancy and availability
- **Multi-floor Support**: Manage parking spots across multiple floors with different spot types (regular, disabled, VIP)

### AI Conversational Agent

The AI-powered chatbot can answer queries like:

- "How many blue cars are currently in the parking?"
- "How much money have we generated in the last hour?"
- "How many cars are currently parked?"
- "What's the average daily number of cars using the parking?"
- "What's the average daily spending per user?"
- "What's the average parking duration for black cars?"

## Technology Stack

- **Python 3.12**
- **Streamlit** - Web framework for the dashboard
- **CrewAI** - AI agent system for natural language queries
- **LiteLLM** - Unified interface for multiple LLM providers
- **SQLAlchemy** - Database ORM with async support
- **Pydantic** - Data validation
- **Docker** - Containerization

## Installation

### Prerequisites

- Python 3.12
- Docker (optional, for containerized deployment)

### Quick Start

1. **Clone the repository**

```bash
git clone <repository-url>
cd smart_parking_management
```

2. **Create environment file**

```bash
cp .env.example .env
```

3. **Install dependencies**

```bash
make install-prod
```

4. **Run the application**

Option A: With local LLM (Ollama)

```bash
# Install and start Ollama
make install-ollama
make run-ollama

# Download the model
make download-ollama-model

# Run the application
make run-app
```

Option B: With OpenAI or other providers

```bash
# Edit .env file and set:
# OPENAI_API_KEY=your-api-key
# OPENAI_MODEL_NAME=gemma:2b

# Run the application
make run-app
```

5. **Access the application**

- Streamlit UI: http://localhost:8501

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
docker-compose up
```

This will start:

- Parking management system (Streamlit)
- Ollama for local LLM support

### Building Docker Image

```bash
docker build -t smart_parking_management .
docker run -p 8501:8501 smart_parking_management
```

## Usage

### 1. Parking Dashboard

Navigate to the Parking Dashboard to:

- Register vehicle entries with license plate, color, and brand
- Process vehicle exits and calculate payments
- View real-time parking status
- Monitor floor-wise occupancy

### 2. AI Assistant

Use the AI Assistant to:

- Ask natural language questions about parking data
- Get insights on revenue and occupancy
- Query vehicle statistics by color or brand
- Analyze parking patterns

## Configuration

### Environment Variables

Key configuration options in `.env`:

- `DEV_MODE` - Enable debug logging
- `DATABASE_URL` - Database connection string
- `OPENAI_API_KEY` - LLM provider API key
- `OPENAI_MODEL_NAME` - Model to use (e.g., gpt-3.5-turbo, ollama/qwen2.5)
- `HOURLY_RATE` - Parking fee per hour

### Database

The system uses SQLite by default. For production, configure PostgreSQL:

```
DATABASE_URL=postgresql://user:password@host:port/dbname
ASYNC_DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
```

## Architecture

### Components

1. **Frontend (Streamlit)**: User interface for parking operations and AI chat
2. **Database (SQLAlchemy)**: Data persistence with async support
3. **AI Agent (CrewAI)**: Natural language processing for queries using AI agents with tools
4. **Services Layer**: Business logic for parking operations and analytics

### Data Models

- **Vehicle**: Stores vehicle information (license plate, color, brand)
- **ParkingSpot**: Represents individual parking spaces
- **ParkingSession**: Tracks vehicle entry/exit and payments

## Development

### Running Tests

```bash
make test
```

### Code Quality

```bash
make pre-commit  # Run linting and formatting
```

### Adding New Features

1. Add models in `src/database/models.py`
2. Create Pydantic schemas in `src/schemas/`
3. Implement business logic in `src/services/`
4. Create UI components in `src/pages/`

## Development Best Practices

To ensure the long-term health and maintainability of this project, all contributors should adhere to the following principles:

- **Keep Documentation Updated**: Whenever you introduce a new feature, modify an existing one, or change a dependency, update the documentation to reflect your changes. Accurate documentation is crucial for collaboration and future development.

- **Embrace Test-Driven Development (TDD)**: Write unit tests _before_ writing the implementation code. This practice ensures that your code is testable, reliable, and meets requirements from the start. All new features should be accompanied by corresponding tests.

- **Maintain a Clean Architecture**: The project follows a service-based architecture to separate concerns. Continue to respect these boundaries by keeping business logic within the service layer, database interactions in the data layer, and UI code in the presentation layer. This makes the system easier to understand, test, and scale.

- **Prioritize Robust Solutions**: Always favor idempotent, automated, and self-correcting mechanisms over manual, one-off scripts. For example, database initialization should handle pre-existing data gracefully rather than requiring a separate, manual setup command.

## License

This project is created for educational purposes as part of a technical assessment.
