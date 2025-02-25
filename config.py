"""Configuration loader for the Customer Service API.

This module handles loading and configuring logging settings from TOML configuration.
"""

import toml
from loguru import logger


class LoggerConfig:
    """Manages logging configuration loaded from TOML files.

    Handles setup and management of logging settings including file handling,
    rotation, compression, and network streaming configuration.
    """

    def __init__(self, config_path: str = "config/config.toml") -> None:
        """Initialize logger configuration.

        Args:
            config_path: Path to TOML config file

        """
        self.config = toml.load(config_path)
        self._setup_logger()

    def _setup_logger(self) -> None:
        """Configure loguru logger based on TOML settings.

        Raises:
            ValueError: If required logging configuration is missing
            IOError: If log file cannot be created/accessed

        """
        try:
            logger.remove()  # Remove default handler
            log_cfg = self.config.get("logging", {})

            # Add file handler with rotation and compression
            logger.add(
                log_cfg.get("log_file", "service.log"),
                rotation=log_cfg.get("log_rotation", "00:00"),
                compression=log_cfg.get("log_compression", "zip"),
                level=log_cfg.get("min_log_level", "INFO"),
            )
        except (OSError, ValueError) as e:
            logger.exception(f"Failed to configure logger: {e}")
            raise

    @property
    def log_address(self) -> str:
        """Get log address from config.

        Returns:
            TCP address for log streaming

        """
        return self.config["logging"].get("log_address", "tcp://127.0.0.1:5555")
