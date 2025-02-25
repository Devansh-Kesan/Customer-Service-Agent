"""Module for analyzing call compliance, sentiment, and other metrics."""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from loguru import logger

from utils.yaml_loader import load_yaml

from .compliance import ComplianceChecker
from .diarization import DiarizationAnalyzer
from .pii_profanity import SensitiveInfoDetector
from .sentiment_speed import SentimentAnalyzer
from .transcription import Transcriber

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")


def raise_value_error(message: str) -> Callable:
    """Create a function to raise a ValueError with the given message."""

    def _raise_error():
        raise ValueError(message)

    return _raise_error


class CallComplianceAnalyzer:
    """A class to analyze call compliance, sentiment, speed, and categorization.

    Attributes
    ----------
        transcriber (Transcriber): Instance for transcription.
        compliance (ComplianceChecker): Instance for compliance checks.
        pii_detector (SensitiveInfoDetector): Instance for PII detection.
        sentiment (SentimentAnalyzer): Instance for sentiment analysis.
        diarization_analyzer (DiarizationAnalyzer): Instance for diarization.
        categories (dict): Categories for call classification.

    """

    def __init__(self, yaml_file: str | None = None) -> None:
        """Initialize the analyzer with optional YAML configuration.

        Args:
        ----
            yaml_file (str | None): Path to the YAML configuration file.

        """
        try:
            hf_token = os.getenv("HF_TOKEN")
            if not hf_token:
                error_message = "HF_TOKEN environment variable is required"
                logger.error(error_message)
                raise_value_error(error_message)()

            logger.debug("Initializing CallComplianceAnalyzer")
            self.transcriber = Transcriber()
            self.compliance = ComplianceChecker()
            self.pii_detector = SensitiveInfoDetector()
            self.sentiment = SentimentAnalyzer()
            self.diarization_analyzer = DiarizationAnalyzer(hf_token)

            if yaml_file is None:
                parent_dir = Path(__file__).parent.parent
                yaml_file = parent_dir / "config" / "call_category.yaml"

            data = load_yaml(yaml_file)
            self.categories = data.get("categories", {})
            logger.success("CallComplianceAnalyzer initialized successfully")
        except Exception:
            logger.exception("Failed to initialize CallComplianceAnalyzer")
            raise

    def categorize_call(self, text: str) -> str:
        """Categorize a call based on its content.

        Args:
        ----
            text (str): The transcribed text of the call.

        Returns:
        -------
            str: The category of the call.

        """
        try:
            scores = {category: 0 for category in self.categories}
            words = text.lower().split()
            for word in words:
                for category, keywords in self.categories.items():
                    if word in keywords:
                        scores[category] += 1

            category = max(scores, key=scores.get, default="other")
            logger.info(f"Call categorized as: {category}")
        except (AttributeError, ValueError) as e:
            logger.exception(f"Call categorization failed: {e}")
            return "other"
        else:
            return category

    def full_analysis(
        self,
        audio_file: str,
        transcribed_text: dict[str, Any] | None = None,
        transcription_status: str | None = None,
    ) -> dict[str, Any]:
        """Analyze call including transcription, sentiment, and compliance.

        Performs comprehensive analysis including transcription, sentiment analysis,
        compliance checking, and call categorization.

        Args:
        ----
            audio_file (str): Path to the audio file.
            transcribed_text (dict[str, Any] | None): Pre-transcribed text (optional).
            transcription_status (str | None): Status of transcription.

        Returns:
        -------
            dict[str, Any]: Analysis results including masked transcript,
                detected phrases, compliance data, sentiment, and category.

        """
        try:
            logger.info(f"Starting analysis for {audio_file}")
            if transcription_status != "completed":
                logger.debug("Transcribing audio")
                transcription = self.transcriber.transcribe(audio_file)
            else:
                logger.debug("Using pre-transcribed text")
                transcription = transcribed_text

            text = transcription.get("text", "")
            segments = transcription.get("segments", [])

            if not text:
                error_message = "Transcription failed"
                logger.error("Empty transcription")
                raise_value_error(error_message)()

            # Convert segments to (start, end, text) tuples for diarization
            transcript_for_diarization = [
                (seg["start"], seg["end"], seg["text"]) for seg in segments
            ]

            detected_pii = self.pii_detector.find_pii(text)
            masked_text = self.pii_detector.mask_content(text, detected_pii)

            compliance_markers = {
                "disclaimers": self.compliance.get_time_markers(
                    segments,
                    self.compliance.disclaimers,
                ),
            }

            sentiment_result = self.sentiment.analyze(text)
            diarized_segments = self.diarization_analyzer.perform_diarization(
                audio_file,
            )
            diarized_with_roles = self.diarization_analyzer.assign_roles_with_context(
                diarized_segments,
                transcript_for_diarization,
            )
            diarization_metrics = self.diarization_analyzer.calculate_metrics(
                diarized_with_roles,
            )

            result = {
                "masked_transcript": masked_text,
                "detected_pii": detected_pii,
                "compliance_markers": compliance_markers,
                "sentiment": sentiment_result,
                "diarization_metrics": diarization_metrics,
                "category": self.categorize_call(text),
            }
        except (ValueError, OSError, RuntimeError) as e:
            logger.exception(f"Analysis failed: {e!s}")
            return {"error": str(e)}
        else:
            return result
