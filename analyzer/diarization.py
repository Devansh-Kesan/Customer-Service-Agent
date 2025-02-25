"""Module for speaker diarization analysis using pyannote.audio pipeline."""

from typing import Any

import numpy as np
from loguru import logger
from pyannote.audio import Pipeline

# Constants
EXPECTED_SPEAKERS = 2


class DiarizationAnalyzer:
    """Analyzer class for performing speaker diarization and role assignment."""

    def __init__(self, hf_token: str) -> None:
        """Initialize the diarization pipeline.

        Args:
        ----
            hf_token (str): Hugging Face authentication token

        """
        try:
            logger.debug("Initializing DiarizationAnalyzer")
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=hf_token,
            )
            logger.success("DiarizationAnalyzer initialized successfully")
        except Exception:
            logger.exception("Failed to initialize DiarizationAnalyzer")
            raise

    def perform_diarization(self, audio_file: str) -> list[dict[str, Any]]:
        """Perform speaker diarization on an audio file.

        Args:
        ----
            audio_file (str): Path to audio file

        Returns:
        -------
            List of diarization segments with start/end times and speaker labels

        """
        try:
            logger.debug(f"Performing diarization for {audio_file}")
            diarization = self.pipeline(audio_file)
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(
                    {"start": turn.start, "end": turn.end, "speaker": speaker},
                )
        except Exception:
            logger.exception("Diarization failed")
            raise
        else:
            logger.success("Diarization completed successfully")
            return segments

    def assign_roles_with_context(
        self,
        diarized_segments: list[dict[str, Any]],
        transcript: list[tuple[float, float, str]],
    ) -> list[dict[str, Any]]:
        """Assign agent/customer roles based on contextual phrases.

        Args:
        ----
            diarized_segments: List of speaker segments from diarization
            transcript: List of transcript entries (start, end, text)

        Returns:
        -------
            Segments with added 'role' field

        """
        try:
            logger.debug("Assigning roles based on context")
            agent_phrases = [
                "hello",
                "thank you for calling",
                "how may i assist you",
                "how can i help you",
                "is there anything else",
                "have a great day",
            ]

            unique_speakers = {seg["speaker"] for seg in diarized_segments}
            if len(unique_speakers) != EXPECTED_SPEAKERS:
                msg = (
                    f"Expected {EXPECTED_SPEAKERS} speakers, "
                    f"found {len(unique_speakers)}"
                )
                raise ValueError(msg)

            speaker_phrase_counts = {speaker: 0 for speaker in unique_speakers}
            for segment in diarized_segments:
                speaker = segment["speaker"]
                start = segment["start"]
                end = segment["end"]
                speaker_text = " ".join(
                    text.lower()
                    for t_start, t_end, text in transcript
                    if t_start >= start and t_end <= end
                )
                for phrase in agent_phrases:
                    if phrase in speaker_text:
                        speaker_phrase_counts[speaker] += 1

            sorted_speakers = sorted(
                speaker_phrase_counts,
                key=speaker_phrase_counts.get,
                reverse=True,
            )
            role_mapping = {sorted_speakers[0]: "agent", sorted_speakers[1]: "customer"}
            for seg in diarized_segments:
                seg["role"] = role_mapping[seg["speaker"]]
        except Exception:
            logger.exception("Role assignment failed")
            raise
        else:
            logger.success("Roles assigned successfully")
            return diarized_segments

    def calculate_metrics(
        self,
        diarized_segments: list[dict[str, Any]],
    ) -> dict[str, float]:
        """Calculate conversation metrics from diarized segments.

        Args:
        ----
            diarized_segments: Segments with role assignments

        Returns:
        -------
            Dictionary of calculated metrics

        """
        try:
            logger.debug("Calculating diarization metrics")
            customer_time = 0.0
            agent_time = 0.0
            interruptions = 0
            ttfts = []

            for i in range(1, len(diarized_segments)):
                prev = diarized_segments[i - 1]
                curr = diarized_segments[i]

                if prev["role"] == "customer":
                    customer_time += prev["end"] - prev["start"]
                elif prev["role"] == "agent":
                    agent_time += prev["end"] - prev["start"]

                if prev["role"] != curr["role"]:
                    ttft = curr["start"] - prev["end"]
                    ttfts.append(ttft)
                    if curr["role"] == "agent" and prev["role"] == "customer":
                        interruptions += 1

            last = diarized_segments[-1]
            if last["role"] == "customer":
                customer_time += last["end"] - last["start"]
            elif last["role"] == "agent":
                agent_time += last["end"] - last["start"]

            agent_segments = [s for s in diarized_segments if s["role"] == "agent"]
            agent_speed = (
                (agent_time * 60) / len(agent_segments) if agent_segments else 0.0
            )
            ratio = customer_time / agent_time if agent_time > 0 else float("inf")
            avg_ttft = np.mean(ttfts) if ttfts else 0.0

            metrics = {
                "agent_speaking_speed_wpm": agent_speed,
                "customer_to_agent_speaking_ratio": ratio,
                "interruptions_by_agent": interruptions,
                "average_ttft": avg_ttft,
            }
        except Exception:
            logger.exception("Metric calculation failed")
            raise
        else:
            logger.success("Metrics calculated successfully")
            return metrics
