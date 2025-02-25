"""Utility module for loading YAML files.

This module provides a function to load data from a YAML file into a dictionary.
"""
from pathlib import Path

import yaml
from loguru import logger

# Define the configuration directory
CONFIG_DIR = Path(__file__).parent.parent / "config"

def load_yaml(yaml_file: str) -> dict:
    """Load data from a YAML file and return it as a dictionary.

    Args:
        yaml_file (str): Path to the YAML file.

    Returns:
        Dict: Dictionary containing YAML data or an empty dictionary if an error occurs.

    """
    try:
        # Construct the full path to the YAML file
        yaml_path = CONFIG_DIR / yaml_file
        logger.info(f"Loading YAML file: {yaml_path}")

        # Open and load the YAML file
        with yaml_path.open(encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        logger.success(f"Successfully loaded YAML file: {yaml_path}")
    except FileNotFoundError:
        logger.error(f"YAML file not found: {yaml_path}")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {yaml_path}: {e!s}")
        return {}
    except OSError as e:
        # More specific error handling for file system related errors
        logger.error(f"File system error while loading {yaml_path}: {e!s}")
        return {}
    else:
        return data
