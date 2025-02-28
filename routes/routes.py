"""Customer Service API routes module.

This module defines the FastAPI routes for handling customer service-related tasks,
including transcription, compliance checks, sentiment analysis, and more.
"""

import hashlib
import os
import pickle
import glob
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

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

# Directory for saving pickle files
PICKLE_DIR = Path(__file__).parent.parent / "data" / "saved_results"
os.makedirs(PICKLE_DIR, exist_ok=True)


async def save_pickle(data, prefix, file_id):
    """Save data to a pickle file.
    
    Args:
    ----
        data: The data to save.
        prefix: The prefix for the filename.
        file_id: Unique identifier for the file.
    
    Returns:
    -------
        Path to the saved pickle file.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_{file_id}_{timestamp}.pkl"
    filepath = PICKLE_DIR / filename
    
    try:
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(pickle.dumps(data))
        logger.debug(f"Saved {prefix} data to {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Failed to save pickle file: {e}")
        return None


async def load_pickle(prefix, file_id):
    """Load data from the most recent pickle file for a given prefix and file_id.
    
    Args:
    ----
        prefix: The prefix for the filename.
        file_id: Unique identifier for the file.
    
    Returns:
    -------
        The loaded data or None if no file is found.
    """
    pattern = str(PICKLE_DIR / f"{prefix}_{file_id}_*.pkl")
    try:
        # Find all matching files
        files = sorted(glob.glob(pattern))
        if not files:
            logger.debug(f"No saved {prefix} data found for {file_id}")
            return None
            
        # Get the most recent file (should be the last one when sorted)
        latest_file = files[-1]
        logger.debug(f"Found saved {prefix} data: {latest_file}")
        
        # Load the data
        async with aiofiles.open(latest_file, "rb") as f:
            data = pickle.loads(await f.read())
        logger.debug(f"Loaded {prefix} data from {latest_file}")
        return data
    except Exception as e:
        logger.error(f"Failed to load pickle file: {e}")
        return None


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
)

# Initialize analyzers and other components
analyzer = CallComplianceAnalyzer()
pii_detector = SensitiveInfoDetector()
transcriber = Transcriber()
compliance_checker = ComplianceChecker()
sentiment_analyzer = SentimentAnalyzer()

hf_token = os.getenv("HF_TOKEN")

diarization_analyzer = DiarizationAnalyzer(hf_token)

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
        logger.debug("Generating file hash")
        return hashlib.sha256(file_data).hexdigest()
    except (TypeError, ValueError) as e:
        logger.exception("Failed to generate file hash")
        raise HTTPException(status_code=500, detail="Hash generation failed") from e


def raise_transcription_error() -> None:
    """Raise a standardized transcription error."""
    raise HTTPException(status_code=500, detail="Transcription failed")


async def get_transcription(file: UploadFile) -> dict:
    """Retrieve transcription from cache, pickled file, or transcribe if not available.

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
    file_id = file_hash[:8]
    
    # First check in-memory cache
    if file_hash in transcription_cache:
        logger.debug("Cache hit for transcription")
        return transcription_cache[file_hash]
    
    # Then check if we have a saved pickle
    saved_transcription = await load_pickle("transcription", file_id)
    if saved_transcription is not None:
        logger.debug("Loaded transcription from pickle file")
        transcription_cache[file_hash] = saved_transcription
        return saved_transcription
    
    # If not in cache or pickle, process the file
    logger.debug("No cached or saved transcription - transcribing new file")
    async with aiofiles.open("temp_audio.mp3", "wb") as f:
        await f.write(file_data)

    transcribed_data = transcriber.transcribe("temp_audio.mp3")
    transcription_cache[file_hash] = transcribed_data
    
    # Save transcription to pickle file
    await save_pickle(transcribed_data, "transcription", file_id)
    
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
    # Get file hash for checking saved results
    file_data = await file.read()
    file_hash = get_file_hash(file_data)
    file_id = file_hash[:8]
    
    # Check if analysis results are already saved
    saved_analysis = await load_pickle("analysis", file_id)
    if saved_analysis is not None:
        logger.debug(f"Using saved analysis results for {file_id}")
        return saved_analysis
    
    # If not saved, perform the analysis
    await file.seek(0)
    transcribed_data = await get_transcription(file)

    audio_path = "temp_audio.mp3"
    await file.seek(0)
    async with aiofiles.open(audio_path, "wb") as f:
        await f.write(await file.read())

    analysis_result = analyzer.full_analysis(audio_path, transcribed_data, "Completed")
    
    # Save analysis result to pickle file
    await save_pickle(analysis_result, "analysis", file_id)
    
    return analysis_result


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
        result = await get_transcription(file)
        return result
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
        # Get file hash for checking saved results
        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        file_id = file_hash[:8]
        
        # Check if compliance results are already saved
        saved_compliance = await load_pickle("compliance", file_id)
        if saved_compliance is not None:
            logger.debug(f"Using saved compliance results for {file_id}")
            return saved_compliance
        
        logger.info(f"Compliance check for file: {file.filename}")
        await file.seek(0)
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
        
        # Save compliance check results
        await save_pickle(detected, "compliance", file_id)
        
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
        # Get file hash for checking saved results
        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        file_id = file_hash[:8]
        
        # Check if profanity results are already saved
        saved_profanity = await load_pickle("profanity", file_id)
        if saved_profanity is not None:
            logger.debug(f"Using saved profanity results for {file_id}")
            return saved_profanity
        
        logger.info(f"Profanity check for file: {file.filename}")
        await file.seek(0)
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in profanity check")
            raise_transcription_error()

        result = pii_detector.detect_profanity(transcribed_data["text"])
        logger.debug(f"Found {len(result)} profane words")
        
        # Save profanity check results
        profanity_result = {"Profanity": result}
        await save_pickle(profanity_result, "profanity", file_id)
        
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
        # Get file hash for checking saved results
        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        file_id = file_hash[:8]
        
        # Check if PII results are already saved
        saved_pii = await load_pickle("pii", file_id)
        if saved_pii is not None:
            logger.debug(f"Using saved PII results for {file_id}")
            return saved_pii
            
        logger.info(f"PII check for file: {file.filename}")
        await file.seek(0)
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in PII check")
            raise_transcription_error()

        result = pii_detector.find_pii(transcribed_data["text"])
        logger.debug(f"Found PII in {len(result)} categories")
        
        # Save PII check results
        await save_pickle(result, "pii", file_id)
        
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
        # Get file hash for checking saved results
        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        file_id = file_hash[:8]
        
        # Check if masked transcript is already saved
        saved_masked = await load_pickle("masked", file_id)
        if saved_masked is not None:
            logger.debug(f"Using saved masked transcript for {file_id}")
            return saved_masked
            
        logger.info(f"Masking transcript for file: {file.filename}")
        await file.seek(0)
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
        
        result = {"masked_text": masked_text}
        
        # Save masked transcript
        await save_pickle(result, "masked", file_id)
        
        logger.success("Masking completed successfully")
    except (ValueError, KeyError) as e:
        logger.exception("Transcript masking failed")
        raise HTTPException(status_code=500, detail="Masking error") from e
    return result


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
        # Get file hash for checking saved results
        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        file_id = file_hash[:8]
        
        # Check if sentiment analysis results are already saved
        saved_sentiment = await load_pickle("sentiment", file_id)
        if saved_sentiment is not None:
            logger.debug(f"Using saved sentiment analysis for {file_id}")
            return saved_sentiment
            
        logger.info(f"Sentiment analysis for file: {file.filename}")
        await file.seek(0)
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in sentiment analysis")
            raise_transcription_error()

        result = sentiment_analyzer.analyze(transcribed_data["text"])
        logger.debug(f"Sentiment result: {result}")
        
        # Save sentiment analysis results
        await save_pickle(result, "sentiment", file_id)
        
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
        # Get file hash for checking saved results
        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        file_id = file_hash[:8]
        
        # Check if categorization results are already saved
        saved_category = await load_pickle("category", file_id)
        if saved_category is not None:
            logger.debug(f"Using saved categorization for {file_id}")
            return saved_category
            
        logger.info(f"Call categorization for file: {file.filename}")
        await file.seek(0)
        transcribed_data = await get_transcription(file)

        if "text" not in transcribed_data:
            logger.error("Missing transcription text in categorization")
            raise_transcription_error()

        result = analyzer.categorize_call(transcribed_data["text"])
        logger.debug(f"Categorization result: {result}")
        
        # Save categorization results
        category_result = {"Call_Category": result}
        await save_pickle(category_result, "category", file_id)
        
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
        # Get file hash for checking saved results
        file_data = await file.read()
        file_hash = get_file_hash(file_data)
        file_id = file_hash[:8]
        
        # Check if diarization results are already saved
        saved_diarization = await load_pickle("diarization", file_id)
        if saved_diarization is not None:
            logger.debug(f"Using saved diarization for {file_id}")
            return {"diarization_metrics": saved_diarization["diarization_metrics"]}
        
        logger.info(f"Call diarization for file: {file.filename}")
        await file.seek(0)
        
        async with aiofiles.open("temp_audio.mp3", "wb") as f:
            await f.write(file_data)

        # Reuse transcription if available
        if file_hash in transcription_cache:
            transcribed_data = transcription_cache[file_hash]
        else:
            transcribed_data = transcriber.transcribe("temp_audio.mp3")
            transcription_cache[file_hash] = transcribed_data
            # Save transcription if not already saved
            await save_pickle(transcribed_data, "transcription", file_id)

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
        
        # Save all diarization results
        full_diarization_results = {
            "diarized_segments": diarized_segments,
            "diarized_with_roles": diarized_with_roles,
            "diarization_metrics": diarization_metrics
        }
        
        await save_pickle(full_diarization_results, "diarization", file_id)
        logger.debug(f"Saved diarization data for file hash: {file_id}")
        
    except (ValueError, KeyError) as e:
        logger.exception("Diarization failed")
        raise HTTPException(status_code=500, detail="Diarization error") from e
    return {"diarization_metrics": diarization_metrics}