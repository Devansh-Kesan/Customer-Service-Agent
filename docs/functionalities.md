# How to Run the Project

### Prerequisites
1. Install Python 3.12
2. Install `just`
3. Install `uv` (package installer/environment manager)
4. Install ffmpeg 

```bash
# Install just 
sudo apt install just
```

```bash
# Install uv 
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 1: Setup Environment

```bash
# Setup environment and install all dependencies
just setup
```

This will:
- Set up your Python environment
- Install required dependencies

### Step 2: Configure Environment

Create a `.env` file in the project root with your Hugging Face token:

```
HF_TOKEN = "your HF token"
```

**Important:** Make sure to give access to the "pyannote/speaker-diarization-3.1" pretrained model on Hugging Face.

### Step 3: Start the Servers

You can start all servers at once with a single command:

```bash
# Start all servers (logging, backend, and frontend)
just start-all
```

This will start all servers in the background and save their output to respective log files:
- `logging_server.log`
- `backend_server.log`
- `frontend_server.log`

To stop all servers:
```bash
just stop-all
```

### Access Frontend
You can view you frontend at http://localhost:7860/

### mkdocs Documnetation
You can view your documentation at http://127.0.0.1:8000/


Alternatively, you can start each server individually in separate terminals:

```bash
# Start the Logging Server
just start-logging-server

# Start the FastAPI Application
just start-backend-server

# Start the Frontend Server
just start-frontend-server
```

### Step 4: Access the API

Open your browser and go to:
```
http://127.0.0.1:3000/docs
```

Use the Swagger UI to test the API endpoints.

### Step 5: Test Endpoints
- Upload an audio file to the `/analyze` endpoint for a complete analysis
- Use specialized endpoints for specific functionalities:
  - `/analyze` - all audio analysis, it includes all the endpoints
  - `/transcribe` - Audio transcription only
  - `/compliance` - Check for required phrases
  - `/profanity` - Detect and mask profanity
  - `/pii` - Check for profanity and sensitive information
  - `/mask_transcript` - Give masked transcription
  -`/sentiment_analysis`- Give sentiment analysis (positive , negative and neutral)
  -`/categorization`- give call category
  -`/diarization`- Measure customer-to-agent speaking ratio (agent should not dominate), detect excessive agent interruptions, and track time-to-first-token (TTFT) for agent responses

---

## How to Evaluate the Project

### 1. Test with Sample Audio Files
- Use sample customer service call recordings to test the system
- Verify accuracy of:
  - Transcription quality
  - Compliance phrase detection
  - PII and profanity masking
  - Sentiment analysis
  - Call categorization
  - diarization

### 2. Check Logs
- Verify logs are being sent to the logging server
- Review log files for errors, warnings, and debug information

### 3. Evaluate Performance
- Measure processing time for:
  - Transcription
  - Full analysis
- Assess accuracy of sentiment analysis and call categorization

### 4. Test Error Handling
- Upload invalid files (non-audio files) and verify error messages
- Check logs for proper exception handling