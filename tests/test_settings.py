from src.config.settings_env import Settings
import os
from unittest.mock import patch
from loguru import logger as loguru_logger


def test_settings():
    Settings()


def test_initialize_logger_dev_mode():
    with patch.dict(os.environ, {"DEV_MODE": "True"}):
        # Reload settings_env to pick up the patched environment variable
        import src.config.settings_env as settings_env
        import importlib
        importlib.reload(settings_env)
        
        # Reload utils to re-initialize the logger with new settings
        import src.shared.utils
        importlib.reload(src.shared.utils)
        
        logger = src.shared.utils.initialize_logger()
        assert logger.level("TRACE").no == loguru_logger.level("TRACE").no


def test_initialize_logger_prod_mode():
    with patch.dict(os.environ, {"DEV_MODE": "False"}):
        # Reload settings_env to pick up the patched environment variable
        import src.config.settings_env as settings_env
        import importlib
        importlib.reload(settings_env)
        
        # Reload utils to re-initialize the logger with new settings
        import src.shared.utils
        importlib.reload(src.shared.utils)
        
        logger = src.shared.utils.initialize_logger()
        assert logger.level("INFO").no == loguru_logger.level("INFO").no