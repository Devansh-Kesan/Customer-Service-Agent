"""Customer Service API routes module.

This module defines the FastAPI routes for handling customer service-related tasks,
including transcription, compliance checks, sentiment analysis, and more.
"""

import hashlib
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
import toml
import zmq
from fastapi import FastAPI, HTTPException, UploadFile
from loguru import logger

from analyzer.analyzer import CallComplianceAnalyzer
from analyzer.compliance import ComplianceChecker
from analyzer.diarization import DiarizationAnalyzer
from analyzer.pii_profanity import SensitiveInfoDetector
from analyzer.sentiment_speed import SentimentAnalyzer
from analyzer.transcription import Transcriber
from config import LoggerConfig

# Load configuration
CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.toml"
config = toml.load(CONFIG_PATH)
FASTAPI_CONFIG = config["fastapi"]

# Initialize logging configuration first
logger_config = LoggerConfig()
context = zmq.Context()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    """Set up and tear down application-level resources.

    Args:
    ----
        _: The FastAPI application instance.

    """
    try:
        socket = context.socket(zmq.PUSH)
        socket.connect(logger_config.log_address)
        logger.remove()
        logger.add(lambda msg: socket.send_json({"record": msg.record}), serialize=True)
        logger.info("Logging client configured")
        yield
    finally:
        context.term()


# Initialize FastAPI with settings from config.toml
app = FastAPI(
    title=FASTAPI_CONFIG.get("title", "Customer Service API"),
    description=FASTAPI_CONFIG.get("description", ""),
    debug=FASTAPI_CONFIG.get("reload", False),
    # lifespan=lifespan,
)

# Initialize analyzers and other components
analyzer = CallComplianceAnalyzer()
pii_detector = SensitiveInfoDetector()
transcriber = Transcriber()
compliance_checker = ComplianceChecker()
sentiment_analyzer = SentimentAnalyzer()
diarization_analyzer = DiarizationAnalyzer()

# Cache for storing transcriptions
transcription_cache = {}


def get_file_hash(file_data: bytes) -> str:
    """Generate a SHA-256 hash for the uploaded file to use as a cache key.

    Args:
    ----
        file_data: The binary content of the file.

    Returns:
    -------
        A hexadecimal SHA-256 hash of the file data.

    """
    try:
        # logger.debug("Generating file hash")
        return hashlib.sha256(file_data).hexdigest()
    except (TypeError, ValueError) as e:
        logger.exception("Failed to generate file hash")
        raise HTTPException(status_code=500, detail="Hash generation failed") from e


def raise_transcription_error() -> None:
    """Raise a standardized transcription error."""
    raise HTTPException(status_code=500, detail="Transcription failed")


async def get_transcription(file: UploadFile) -> dict:
    """Retrieve transcription from cache or transcribe if not cached.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        The transcription data.

    Raises:
    ------
        HTTPException: If transcription fails.

    """
    file_data = await file.read()
    file_hash = get_file_hash(file_data)

    if file_hash in transcription_cache:
        logger.debug("Cache hit for transcription")
        return transcription_cache[file_hash]

    logger.debug("Cache miss - transcribing new file")
    async with aiofiles.open("temp_audio.mp3", "wb") as f:
        await f.write(file_data)

    transcribed_data = transcriber.transcribe("temp_audio.mp3")
    transcription_cache[file_hash] = transcribed_data
    logger.success("Transcription completed successfully")
    return transcribed_data


@app.post("/analyze")
async def analyze_call(file: UploadFile) -> dict:
    """Analyze the uploaded call audio for full compliance and categorization.

    Args:
    ----
        file (UploadFile): The uploaded audio file.

    Returns:
    -------
        dict: Analysis results including compliance and categorization.

    """
    await file.seek(0)
    transcribed_data = await get_transcription(file)

    audio_path = "temp_audio.mp3"
    await file.seek(0)
    async with aiofiles.open(audio_path, "wb") as f:
        await f.write(await file.read())

    return analyzer.full_analysis(audio_path, transcribed_data, "Completed")


@app.post("/transcribe")
async def transcribe_call(file: UploadFile) -> dict:
    """Transcribe the uploaded audio file.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        The transcription data.

    """
    try:
        logger.info(f"Transcription request for file: {file.filename}")
        return await get_transcription(file)
    except (OSError, ValueError) as e:
        logger.exception("Transcription endpoint failed")
        raise HTTPException(status_code=500, detail="Transcription failed") from e


@app.post("/compliance")
async def check_compliance(file: UploadFile) -> dict:
    """Check the uploaded audio file for compliance with greetings,
    closing, and disclaimers.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        Detected compliance phrases.

    """
    try:
        logger.info(f"Compliance check for file: {file.filename}")
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in compliance check")
            raise_transcription_error()

        transcribed_text = transcribed_data["text"]
        logger.debug("Detecting compliance phrases")

        detected = {
            "detected_greetings": compliance_checker.detect_phrases(
                transcribed_text,
                compliance_checker.greetings,
            ),
            "detected_closing": compliance_checker.detect_phrases(
                transcribed_text,
                compliance_checker.closing,
            ),
            "detected_disclaimers": compliance_checker.detect_phrases(
                transcribed_text,
                compliance_checker.disclaimers,
            ),
        }

        logger.debug(f"Compliance results: {len(detected)} items found")
    except (ValueError, KeyError) as e:
        logger.exception("Compliance check failed")
        raise HTTPException(
            status_code=500,
            detail="Compliance check error",
        ) from e
    return detected


@app.post("/profanity")
async def check_profanity(file: UploadFile) -> dict:
    """Detect profanity in the transcribed text of the uploaded audio file.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        Detected profanity information.

    """
    try:
        logger.info(f"Profanity check for file: {file.filename}")
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in profanity check")
            raise_transcription_error()

        result = pii_detector.detect_profanity(transcribed_data["text"])
        logger.debug(f"Found {len(result)} profane words")
    except (ValueError, KeyError) as e:
        logger.exception("Profanity check failed")
        raise HTTPException(
            status_code=500,
            detail="Profanity check error",
        ) from e
    return {"Profanity": result}


@app.post("/pii")
async def check_pii(file: UploadFile) -> dict:
    """Detect personally identifiable information (PII) in the transcribed text.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        Detected PII information.

    """
    try:
        logger.info(f"PII check for file: {file.filename}")
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in PII check")
            raise_transcription_error()

        result = pii_detector.find_pii(transcribed_data["text"])
        logger.debug(f"Found PII in {len(result)} categories")
    except (ValueError, KeyError) as e:
        logger.exception("PII check failed")
        raise HTTPException(status_code=500, detail="PII check error") from e
    return result


@app.post("/mask_transcript")
async def masked_transcript(file: UploadFile) -> dict:
    """Mask sensitive information (PII and profanity) in the transcribed text.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        Masked transcript.

    """
    try:
        logger.info(f"Masking transcript for file: {file.filename}")
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in masking")
            raise_transcription_error()

        transcribed_text = transcribed_data["text"]
        logger.debug("Masking sensitive content")

        profanity = pii_detector.detect_profanity(transcribed_text)
        pii = pii_detector.find_pii(transcribed_text)

        profane = {"profane": profanity}
        masked_text = pii_detector.mask_content(transcribed_text, profane)
        masked_text = pii_detector.mask_content(masked_text, pii)

        logger.success("Masking completed successfully")
    except (ValueError, KeyError) as e:
        logger.exception("Transcript masking failed")
        raise HTTPException(status_code=500, detail="Masking error") from e
    return {"masked_text": masked_text}


@app.post("/sentiment_analysis")
async def sentiment_analysis(file: UploadFile) -> dict:
    """Perform sentiment analysis on the transcribed text.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        Sentiment analysis results.

    """
    try:
        logger.info(f"Sentiment analysis for file: {file.filename}")
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in sentiment analysis")
            raise_transcription_error()

        result = sentiment_analyzer.analyze(transcribed_data["text"])
        logger.debug(f"Sentiment result: {result}")
    except (ValueError, KeyError) as e:
        logger.exception("Sentiment analysis failed")
        raise HTTPException(
            status_code=500,
            detail="Sentiment analysis error",
        ) from e
    return result


@app.post("/categorization")
async def categorize_call(file: UploadFile) -> dict:
    """Categorize the uploaded call based on its transcribed text.

    Args:
    ----
        file: The uploaded audio file.

    Returns:
    -------
        Call categorization results.

    """
    try:
        logger.info(f"Call categorization for file: {file.filename}")
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in categorization")
            raise_transcription_error()

        result = analyzer.categorize_call(transcribed_data["text"])
        logger.debug(f"Categorization result: {result}")
    except (ValueError, KeyError) as e:
        logger.exception("Categorization failed")
        raise HTTPException(
            status_code=500,
            detail="Categorization error",
        ) from e
    return {"Call_Category": result}


@app.post("/diarization")
async def diarize_call(file: UploadFile) -> dict:
    """Perform speaker diarization on the uploaded audio file.

    Args:
        file: The uploaded audio file.

    Returns:
        Diarization metrics and results.

    """
    try:
        logger.info(f"Call diarization for file: {file.filename}")

        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        async with aiofiles.open("temp_audio.mp3", "wb") as f:
            await f.write(file_data)

        transcribed_data = transcriber.transcribe("temp_audio.mp3")
        transcription_cache[file_hash] = transcribed_data

        segments = transcribed_data["segments"]
        transcript_for_diarization = [
            (seg["start"], seg["end"], seg["text"]) for seg in segments
        ]

        diarized_segments = diarization_analyzer.perform_diarization("temp_audio.mp3")
        diarized_with_roles = diarization_analyzer.assign_roles_with_context(
            diarized_segments, transcript_for_diarization,
        )
        diarization_metrics = diarization_analyzer.calculate_metrics(
            diarized_with_roles,
        )
    except (ValueError, KeyError) as e:
        logger.exception("Diarization failed")
        raise HTTPException(status_code=500, detail="Diarization error") from e
    return {"diarization_metrics": diarization_metrics}
