#!/usr/bin/env python3
"""
Logging Configuration Module
Centralized logging configuration with rotating file handlers
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class LogConfig:
    """Centralized logging configuration manager"""

    _initialized = False
    _loggers = {}

    @classmethod
    def initialize(cls):
        """Initialize the logging system with rotating file handlers"""
        if cls._initialized:
            return

        # Get configuration from environment variables
        log_dir = os.getenv('LOG_DIR', 'logs')
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        log_max_bytes = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB default
        log_backup_count = int(os.getenv('LOG_BACKUP_COUNT', '10'))  # 10 files default
        log_format = os.getenv(
            'LOG_FORMAT',
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
        )
        log_date_format = os.getenv('LOG_DATE_FORMAT', '%Y-%m-%d %H:%M:%S')

        # Create logs directory if it doesn't exist
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Convert log level string to logging constant
        numeric_level = getattr(logging, log_level, logging.INFO)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)

        # Remove any existing handlers
        root_logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(log_format, datefmt=log_date_format)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # File handler with rotation - application.log
        app_log_file = os.path.join(log_dir, 'application.log')
        file_handler = RotatingFileHandler(
            app_log_file,
            maxBytes=log_max_bytes,
            backupCount=log_backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Error file handler - only ERROR and above
        error_log_file = os.path.join(log_dir, 'error.log')
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=log_max_bytes,
            backupCount=log_backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        root_logger.addHandler(error_handler)

        cls._initialized = True

        # Log initialization success
        root_logger.info("=" * 80)
        root_logger.info("Logging system initialized")
        root_logger.info(f"Log directory: {log_dir}")
        root_logger.info(f"Log level: {log_level}")
        root_logger.info(f"Max log file size: {log_max_bytes / 1024 / 1024:.1f} MB")
        root_logger.info(f"Backup count: {log_backup_count}")
        root_logger.info("=" * 80)

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Get a logger instance for the specified module

        Args:
            name: Name of the logger (typically __name__ from calling module)

        Returns:
            logging.Logger: Configured logger instance
        """
        if not cls._initialized:
            cls.initialize()

        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger

        return cls._loggers[name]

    @classmethod
    def shutdown(cls):
        """Shutdown logging system gracefully"""
        if cls._initialized:
            logging.info("Shutting down logging system")
            logging.shutdown()
            cls._initialized = False
            cls._loggers.clear()


# Convenience function for getting logger
def get_logger(name: str = None) -> logging.Logger:
    """
    Get a configured logger instance

    Args:
        name: Name of the logger (typically __name__)

    Returns:
        logging.Logger: Configured logger instance
    """
    if name is None:
        name = __name__

    return LogConfig.get_logger(name)


# Initialize logging system when module is imported
LogConfig.initialize()
