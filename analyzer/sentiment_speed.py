"""Module for sentiment analysis and speech speed calculation in customer service calls.

This module provides functionality for analyzing sentiment in text using pre-trained
transformer models and calculating speech speed metrics.
"""

from typing import Any

from loguru import logger
from transformers import pipeline


class SentimentAnalyzer:
    """Analyzes sentiment in text using a pre-trained transformer model."""

    def __init__(self) -> None:
        """Initialize the sentiment analyzer with a pre-trained pipeline."""
        try:
            logger.debug("Loading sentiment analysis pipeline")
            self.pipeline = pipeline("sentiment-analysis")
        except ImportError as e:
            logger.exception(f"Required dependencies not installed: {e}")
            raise
        except RuntimeError as e:
            logger.exception(f"Failed to load model: {e}")
            raise
        else:
            logger.success("Sentiment analysis pipeline loaded successfully")

    def analyze(self, text: str) -> dict[str, Any]:
        """Analyze the sentiment of the given text.

        Args:
            text: The text to analyze

        Returns:
            Dictionary containing sentiment analysis results or error information

        """
        try:
            logger.debug(
                f"Analyzing sentiment for text: {text[:50]}...",
            )  # Log first 50 chars
            result = self.pipeline(text)[0]
            logger.info(f"Sentiment result: {result}")
        except ValueError as e:
            logger.error(f"Invalid input text: {e}")
            return {"error": str(e)}
        except RuntimeError as e:
            logger.exception("Model inference failed")
            return {"error": str(e)}
        else:
            return result
