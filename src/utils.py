import os
import sys
from pathlib import Path
from loguru import logger as loguru_logger

from settings_env import settings

# Check if we run the code from the src directory
if Path("src").is_dir():
    loguru_logger.warning("Changing working directory to src")
    loguru_logger.warning(f" Current working dir is {Path.cwd()}")
    os.chdir("src")
elif Path("ml").is_dir():
    pass
else:
    raise Exception(
        f"Project should always run from the src directory. But current working dir is {Path.cwd()}"
    )


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