"""Initialize the parking database."""
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.infrastructure.persistence.database import init_db

if __name__ == "__main__":
    print("Initializing parking database...")
    init_db()
    print("Database initialization complete!")