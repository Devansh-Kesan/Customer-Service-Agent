"""Start server script for the Customer Service API.

This script initializes and starts the FastAPI server using configuration
from a TOML file.
"""
import sys
from pathlib import Path

import toml
import uvicorn
from loguru import logger

# Define the path to the configuration file
CONFIG_PATH = Path(__file__).parent / "config" / "config.toml"

def load_config() -> dict:
    """Load configuration from a TOML file.

    Returns:
        dict: Configuration dictionary or an empty dictionary if an error occurs.

    """
    try:
        logger.info(f"Loading configuration from: {CONFIG_PATH}")
        config = toml.load(CONFIG_PATH)
        logger.success("Configuration loaded successfully")
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {CONFIG_PATH}")
        return {}
    except toml.TomlDecodeError as e:
        logger.error(f"TOML parsing error in {CONFIG_PATH}: {e!s}")
        return {}
    except RuntimeError as e:  # More specific than catching Exception
        logger.error(f"Unexpected error while loading configuration: {e!s}")
        return {}
    else:
        return config

if __name__ == "__main__":
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration. Exiting.")
        sys.exit(1)

    # Extract FastAPI configuration
    fastapi_config = config.get("fastapi", {})
    if not fastapi_config:
        logger.error("FastAPI configuration not found in config file. Exiting.")
        sys.exit(1)

    # Log server startup details
    logger.info("Starting FastAPI server...")
    logger.info(f"Host: {fastapi_config.get('host')}")
    logger.info(f"Port: {fastapi_config.get('port')}")
    logger.info(f"Workers: {fastapi_config.get('workers')}")
    logger.info(f"Reload: {fastapi_config.get('reload', False)}")

    try:
        # Start the server
        uvicorn.run(
            # "routes" is the module, "app" is the FastAPI instance
            "routes.routes:app",
            host=fastapi_config["host"],
            port=fastapi_config["port"],
            workers=fastapi_config["workers"],
            reload=fastapi_config.get("reload", False),
        )
    except RuntimeError as e:  # More specific than catching Exception
        logger.error(f"Failed to start FastAPI server: {e!s}")
        sys.exit(1)
