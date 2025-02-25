# How to Run the Project

### Prerequisites

1. Install Python 3.8+
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Step 1: Start the Logging Server

```bash
python logging_server.py
```

### Step 2: Start the FastAPI Application

```bash
uvicorn routes:app --reload
```

### Step 3: Access the API

Open your browser and go to:
```
http://127.0.0.1:8000/docs
```

Use the Swagger UI to test the API endpoints.

### Step 4: Test Endpoints

- Upload an audio file to the `/analyze` endpoint for a complete analysis
- Use specialized endpoints for specific functionalities:
  - `/transcribe` - Audio transcription only
  - `/compliance` - Check for required phrases
  - `/profanity` - Detect and mask profanity
  - And more...

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

---
