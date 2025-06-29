import sys
from loguru import logger as loguru_logger

from src.config.settings_env import settings




def initialize_logger():
    """Initialize the logger based on DEV_MODE setting."""
    loguru_logger.remove()
    
    if settings.DEV_MODE:
        loguru_logger.add(sys.stderr, level="TRACE")
    else:
        loguru_logger.add(sys.stderr, level="INFO")
    
    return loguru_logger


# Initialize logger
logger = initialize_logger()