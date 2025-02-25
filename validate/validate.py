"""Validation module for YAML and TOML configuration files.

This module defines Pydantic models to validate the structure of YAML and TOML files
used in the application. It also provides functions to load and validate these files.
"""

from pathlib import Path

import toml
import yaml
from loguru import logger
from pydantic import BaseModel, ValidationError


# ------------------- Phrases YAML Validation -------------------
class PhrasesConfig(BaseModel):
    """Model for validating phrases configuration in YAML files.

    Attributes:
        greetings (list[str]): List of greeting phrases.
        closing (list[str]): List of closing phrases.
        disclaimers (list[str]): List of disclaimer phrases.

    """

    greetings: list[str]
    closing: list[str]
    disclaimers: list[str]


# ------------------- PII & Profanity YAML Validation -------------------
class PIIProfanityConfig(BaseModel):
    """Model for validating PII and profanity configuration in YAML files.

    Attributes:
        pii_patterns (dict[str, str]): Dictionary of regex patterns for PII detection.
        custom_badwords (list[str]): List of custom bad words.

    """

    pii_patterns: dict[str, str]  # Dictionary of regex patterns
    custom_badwords: list[str]  # List of bad words


# ------------------- Call Categories YAML Validation -------------------
class CallCategoryConfig(BaseModel):
    """Model for validating call category configuration in YAML files.

    Attributes:
        categories (dict[str, list[str]]): Mapping of categories to lists of words.

    """

    categories: dict[str, list[str]]  # Each category should map to a list of words


# ------------------- FastAPI Config (TOML) -------------------
class FastAPIConfig(BaseModel):
    """Model for validating FastAPI configuration in TOML files.

    Attributes:
        host (str): Host address for the FastAPI server.
        port (int): Port number for the FastAPI server.
        workers (int): Number of worker processes.
        reload (bool): Whether to enable auto-reload in development mode.
        title (str): Title of the FastAPI application.
        description (str): Description of the FastAPI application.

    """

    host: str
    port: int
    workers: int
    reload: bool
    title: str
    description: str


class LoggingConfig(BaseModel):
    """Model for validating logging configuration in TOML files.

    Attributes:
        log_file (str): Name of the log file.
        min_log_level (str): Minimum log level (e.g., DEBUG, INFO).
        log_rotation (str): Log rotation policy.
        log_compression (str): Log compression method.
        log_address (str): Address for the logging server.

    """

    log_file: str
    min_log_level: str
    log_rotation: str
    log_compression: str
    log_address: str


class AppConfig(BaseModel):
    """Top-level model for validating the entire application configuration.

    Attributes:
        fastapi (FastAPIConfig): FastAPI configuration.
        logging (LoggingConfig): Logging configuration.

    """

    fastapi: FastAPIConfig
    logging: LoggingConfig


# ------------------- YAML and TOML Validation Functions -------------------
def validate_yaml(file_path: Path, model: type[BaseModel]) -> BaseModel | None:
    """Validate a YAML file using a given Pydantic model.

    Args:
        file_path (Path): Path to the YAML file.
        model (type[BaseModel]): Pydantic model to validate the YAML data.

    Returns:
        Optional[BaseModel]: Validated model instance or None if validation fails.

    """
    try:
        logger.info(f"Validating YAML file: {file_path}")
        with file_path.open() as f:
            data = yaml.safe_load(f)
        validated_model = model(**data)
        logger.success(f"Validation successful for {file_path}")
    except yaml.YAMLError as e:
        logger.error(f"YAML parsing error in {file_path}: {e!s}")
        return None
    except ValidationError as e:
        logger.error(f"Validation error in {file_path}: {e!s}")
        return None
    except OSError as e:
        logger.error(f"File system error while validating {file_path}: {e!s}")
        return None
    else:
        return validated_model


def validate_toml(file_path: Path) -> AppConfig | None:
    """Validate a TOML file using the AppConfig Pydantic model.

    Args:
        file_path (Path): Path to the TOML file.

    Returns:
        Optional[AppConfig]: Validated AppConfig instance or None if validation fails.

    """
    try:
        logger.info(f"Validating TOML file: {file_path}")
        with file_path.open() as f:
            data = toml.load(f)
        validated_config = AppConfig(**data)
        logger.success(f"Validation successful for {file_path}")
    except toml.TomlDecodeError as e:
        logger.error(f"TOML parsing error in {file_path}: {e!s}")
        return None
    except ValidationError as e:
        logger.error(f"Validation error in {file_path}: {e!s}")
        return None
    except OSError as e:
        logger.error(f"File system error while validating {file_path}: {e!s}")
        return None
    else:
        return validated_config


# ------------------- Run Validations -------------------
if __name__ == "__main__":
    # Configure logger
    logger.add("validation.log", rotation="10 MB", level="INFO")

    # Define the base directory (parent of the validation folder)
    BASE_DIR = Path(__file__).parent.parent
    PHRASES_YAML = BASE_DIR / "config" / "phrases.yaml"
    PII_PROFANITY_YAML = BASE_DIR / "config" / "pii_profanity.yaml"
    CALL_CATEGORY_YAML = BASE_DIR / "config" / "call_category.yaml"
    CONFIG_TOML = BASE_DIR / "config" / "config.toml"

    # Validate YAML files
    phrases_config = validate_yaml(PHRASES_YAML, PhrasesConfig)
    pii_profanity_config = validate_yaml(PII_PROFANITY_YAML, PIIProfanityConfig)
    call_category_config = validate_yaml(CALL_CATEGORY_YAML, CallCategoryConfig)

    # Validate TOML file
    app_config = validate_toml(CONFIG_TOML)

    # Log final results
    if phrases_config:
        logger.info("Phrases YAML validation successful.")
    if pii_profanity_config:
        logger.info("PII & Profanity YAML validation successful.")
    if call_category_config:
        logger.info("Call Category YAML validation successful.")
    if app_config:
        logger.info("TOML validation successful.")
