# Call Compliance Analyzer

![Project Status: Active](https://img.shields.io/badge/Status-Active-brightgreen)
![Python 3.12+](https://img.shields.io/badge/Python-3.12+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-blue)

## Project Overview

The **Call Compliance Analyzer** processes customer service call recordings to provide comprehensive insights through:

- **🔊 Transcription**: Converting audio to text using OpenAI's Whisper model
- **✅ Compliance Checks**: Detecting required greetings, closings, and disclaimers
- **🔒 Sensitive Information Detection**: Identifying and masking PII and profanity
- **😊 Sentiment Analysis**: Determining conversation tone and emotional context
- **🏷️ Call Categorization**: Classifying calls into meaningful business categories
- **⏱️ Diarization**: Measure customer-to-agent speaking ratio (agent should not dominate), detect excessive agent interruptions, and track time-to-first-token (TTFT) for agent responses.

Built with **FastAPI** for the backend, **Loguru** for logging, and **mkdocs-material** for documentation.

---

## Functionalities

### 1. Audio Transcription

- Converts audio files to text using OpenAI's Whisper model
- Supports multiple audio formats (`.wav`)
- Returns transcribed text with precise timestamps for each segment

### 2. Compliance Checks

Detects predefined phrases in calls:

| Category | Example Phrases |
|----------|----------------|
| **Greetings** | "Hello", "Thank you for calling" |
| **Closing Statements** | "Goodbye", "Have a great day" |
| **Disclaimers** | "Calls may be recorded", "Do not share sensitive information" |

Provides time markers for each detected phrase.

### 3. Sensitive Information Detection

- Detects and masks:
  - **PII**: Credit card numbers, email addresses, SSNs
  - **Profanity**: Offensive or inappropriate language
- Replaces sensitive information with `****`

### 4. Sentiment Analysis

- Analyzes call sentiment using Hugging Face's `sentiment-analysis` pipeline
- Returns:
  - Sentiment label (`POSITIVE`, `NEGATIVE`, `NEUTRAL`)
  - Confidence score

### 5. Call Categorization

Classifies calls into categories based on keywords:

| Category | Keywords |
|----------|----------|
| **Returns** | "Return", "Refund", "Exchange" |
| **Technical Support** | "Issue", "Error", "Fix" |
| **Billing** | "Bill", "Payment", "Invoice" |
| **General** | "Help", "Assist", "Support" |

### 6. Diarization

- Measure customer-to-agent speaking ratio
- detect excessive agent interruptions
- track time-to-first-token (TTFT) for agent responses.
