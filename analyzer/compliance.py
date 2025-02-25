"""Module for checking compliance in customer service conversations."""

from pathlib import Path

from loguru import logger

from utils.yaml_loader import load_yaml


class ComplianceChecker:
    """Handles compliance checking for customer service conversations
    using predefined phrases.

    This class provides functionality to detect specific phrases and their timing in
    customer service conversations for compliance monitoring.
    """

    def __init__(self, yaml_file: str | None = None) -> None:
        """Initialize the compliance checker with phrase definitions.

        Args:
            yaml_file: Path to YAML file containing compliance phrases. If None,
                uses the default phrases.yaml in the parent directory.

        Raises:
            RuntimeError: If initialization fails

        """
        try:
            logger.debug("Initializing compliance checker")
            if yaml_file is None:
                # Get the parent directory of the current script
                parent_dir = Path(__file__).parent.parent
                yaml_file = str(parent_dir / "config" / "phrases.yaml")

            self.phrases = load_yaml(yaml_file)
            self.greetings = self.phrases.get("greetings", [])
            self.closing = self.phrases.get("closing", [])
            self.disclaimers = self.phrases.get("disclaimers", [])
            logger.success("Compliance checker initialized successfully")

        except (OSError, RuntimeError) as e:
            logger.exception("Failed to initialize compliance checker")
            err_init_failed = "Failed to initialize compliance checker"
            raise RuntimeError(err_init_failed) from e

    def detect_phrases(self, text: str, phrases: list[str]) -> list[str]:
        """Detect which phrases from a list appear in the given text.

        Args:
            text: The text to search in
            phrases: List of phrases to look for

        Returns:
            List of phrases found in the text

        """
        try:
            logger.debug(f"Detecting phrases in text (length: {len(text)} chars)")
            logger.trace(f"Phrases to detect: {phrases}")
            detected = [p for p in phrases if p.lower() in text.lower()]

            if detected:
                logger.info(f"Detected {len(detected)} phrases: {detected}")
            else:
                logger.debug("No phrases detected")

        except (AttributeError, ValueError):
            logger.exception("Phrase detection failed")
            return []
        else:
            return detected

    def get_time_markers(
        self,
        segments: list[dict[str, object]],
        phrases: list[str],
    ) -> list[tuple[str, float, float]]:
        """Find time markers for specific phrases in segmented text.

        Args:
            segments: List of text segments with start/end times
            phrases: List of phrases to search for

        Returns:
            List of tuples containing (phrase, start_time, end_time)

        """
        try:
            logger.debug(f"Getting time markers for {len(segments)} segments")
            logger.trace(f"Phrases to detect: {phrases}")
            markers = [
                (phrase, seg["start"], seg["end"])
                for seg in segments
                for phrase in phrases
                if phrase.lower() in seg["text"].lower()
            ]

            if markers:
                logger.info(f"Found {len(markers)} time markers")
            else:
                logger.debug("No time markers found")

        except (KeyError, TypeError, AttributeError):
            logger.exception("Failed to get time markers")
            return []
        else:
            return markers
