"""Module for detecting and masking sensitive information and profanity in text."""

import re
from pathlib import Path

from better_profanity import profanity
from loguru import logger

from utils.yaml_loader import load_yaml


class SensitiveInfoDetector:
    """Detector for PII (Personally Identifiable Information) and profanity in text."""

    def __init__(self, yaml_file: str | None = None) -> None:
        """Initialize the detector and load PII patterns and bad words from YAML."""
        try:
            logger.debug("Initializing sensitive information detector")

            if yaml_file is None:
                # Get the parent directory of the current script
                parent_dir = Path(__file__).parent.parent
                yaml_file = str(parent_dir / "config" / "pii_profanity.yaml")

            self.config = load_yaml(yaml_file)
            self.pii_patterns = self.config.get("pii_patterns", {})
            self.custom_badwords = self.config.get("custom_badwords", [])
            # Load profanity filter with custom bad words
            profanity.load_censor_words()
            profanity.add_censor_words(self.custom_badwords)
            logger.debug("Loaded base profanity filter with custom words")
        except (FileNotFoundError, ValueError) as e:
            logger.exception(f"Configuration error: {e}")
            raise
        except RuntimeError as e:
            logger.exception(f"Profanity filter initialization error: {e}")
            raise
        else:
            logger.success("Sensitive info detector initialized successfully")

    def detect_profanity(self, text: str) -> list[str]:
        """Detect profane words in the text.

        Args:
            text: Input text to scan for profanity

        Returns:
            List of detected profane words

        """
        try:
            logger.debug(f"Scanning for profanity in text (length: {len(text)} chars)")
            words = text.split()
            logger.trace(f"Processing {len(words)} words for profanity")

            # Detect profanity
            profane_words = [
                word for word in words if profanity.contains_profanity(word)
            ]

            if profane_words:
                logger.warning(f"Detected {len(profane_words)} profane words")
            else:
                logger.debug("No profanity detected")
        except ValueError as e:
            logger.error(f"Invalid input for profanity detection: {e}")
            return []
        except RuntimeError as e:
            logger.error(f"Profanity detection runtime error: {e}")
            return []
        else:
            return profane_words

    def find_pii(self, text: str) -> dict[str, list[str]]:
        """Find PII in text using regex patterns.

        Args:
            text: Input text to scan for PII

        Returns:
            Dictionary mapping PII types to lists of matches

        """
        try:
            logger.debug(f"Scanning for PII in text (length: {len(text)} chars)")
            detected = {}

            for pii_type, pattern in self.pii_patterns.items():
                matches = re.findall(pattern, text)
                if matches:
                    logger.warning(f"Found {len(matches)} {pii_type} matches")
                    detected[pii_type] = matches
                else:
                    logger.trace(f"No {pii_type} detected")

            logger.info(f"Found PII in {len(detected)} categories")
        except ValueError as e:
            logger.error(f"Invalid input for PII detection: {e}")
            return {}
        except re.error as e:
            logger.error(f"Regex pattern error: {e}")
            return {}
        else:
            return detected

    def mask_content(self, text: str, pii_matches: dict[str, list[str]]) -> str:
        """Mask detected PII and profanity in the text.

        Args:
            text: Original text to mask
            pii_matches: Dictionary of PII matches to mask

        Returns:
            Text with PII and profanity masked

        """
        try:
            original_length = len(text)
            logger.debug(f"Masking content (original length: {original_length} chars)")

            # Mask profanity first
            masked = profanity.censor(text)
            logger.trace("Profanity masking completed")

            # Mask PII patterns
            replacement_count = 0
            for matches in pii_matches.values():
                for match in matches:
                    masked = masked.replace(match, "****")
                    replacement_count += 1

            logger.info(f"Made {replacement_count} sensitive content replacements")
            logger.trace(f"Final masked length: {len(masked)} chars")
        except ValueError as e:
            logger.error(f"Invalid input for content masking: {e}")
            return text
        except (AttributeError, TypeError) as e:
            logger.error(f"Content masking error: {e}")
            return text
        else:
            return masked
