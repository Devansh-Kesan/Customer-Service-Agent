"""Module for audio transcription using the Whisper model."""

import whisper
from loguru import logger


class Transcriber:
    """Transcribes audio files using OpenAI's Whisper model."""

    def __init__(self, model_name: str = "base") -> None:
        """Initialize the transcriber with the specified Whisper model.

        Args:
            model_name: Name of the Whisper model to use (default: "base")

        """
        try:
            logger.debug(f"Loading Whisper model: {model_name}")
            self.model = whisper.load_model(model_name)
            logger.success(f"Whisper model '{model_name}' loaded successfully")
        except Exception:
            logger.exception(f"Failed to load Whisper model '{model_name}'")
            raise

    def transcribe(self, audio_file: str) -> dict[str, object]:
        """Transcribe audio file to text using the Whisper model.

        Args:
            audio_file: Path to the audio file to transcribe

        Returns:
            Dictionary containing transcribed text and segment information

        """
        try:
            logger.info(f"Starting transcription for audio file: {audio_file}")
            result = self.model.transcribe(audio_file)
            logger.debug(f"Transcription completed for {audio_file}")
            logger.trace(
                f"Transcription result: {result}",
            )  # Use trace for verbose output

            return {
                "text": result["text"].strip(),
                "segments": result.get("segments", []),
            }
        except Exception:
            logger.exception(f"Transcription failed for {audio_file}")
            return {"text": "", "segments": []}
