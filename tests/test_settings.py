from settings_env import Settings
import os
from unittest.mock import patch
from src.utils import initialize_logger
from loguru import logger as loguru_logger


def test_settings():
    Settings()


def test_initialize_logger_dev_mode():
    with patch.dict(os.environ, {"DEV_MODE": "True"}):
        # Reload settings_env to pick up the patched environment variable
        import settings_env
        import importlib
        importlib.reload(settings_env)
        
        # Reload utils to re-initialize the logger with new settings
        import src.utils
        importlib.reload(src.utils)
        
        logger = src.utils.initialize_logger()
        assert logger.level("TRACE").no == loguru_logger.level("TRACE").no


def test_initialize_logger_prod_mode():
    with patch.dict(os.environ, {"DEV_MODE": "False"}):
        # Reload settings_env to pick up the patched environment variable
        import settings_env
        import importlib
        importlib.reload(settings_env)
        
        # Reload utils to re-initialize the logger with new settings
        import src.utils
        importlib.reload(src.utils)
        
        logger = src.utils.initialize_logger()
        assert logger.level("INFO").no == loguru_logger.level("INFO").no