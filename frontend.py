import gradio as gr
import httpx

BASE_URL = "http://localhost:3000"

def analyze_call(audio_file_path, analysis_options):
    # Map analysis options to backend features
    features = set()
    if "Transcript" in analysis_options:
        features.add("transcribe")
    if any(x in analysis_options for x in ["Detected Greetings", "Detected Closing Statements", "Detected Disclaimers"]):
        features.add("compliance")
    if "Detected PII" in analysis_options:
        features.add("pii")
    if "Detected Profanity" in analysis_options:
        features.add("profanity")
    if "Masked Transcript" in analysis_options:
        features.add("mask_transcript")
    if "Sentiment Analysis" in analysis_options:
        features.add("sentiment_analysis")

    results = {}
    with open(audio_file_path, "rb") as audio_file:
        files = {"file": (audio_file_path, audio_file.read(), "audio/mpeg")}
        
        if "transcribe" in features:
            response = httpx.post(f"{BASE_URL}/transcribe", files=files, timeout=300)
            results["transcription"] = response.json()
            
        if "compliance" in features:
            response = httpx.post(f"{BASE_URL}/compliance", files=files, timeout=300)
            results["compliance"] = response.json()
            
        if "profanity" in features:
            response = httpx.post(f"{BASE_URL}/profanity", files=files, timeout=300)
            results["profanity"] = response.json()
            
        if "pii" in features:
            response = httpx.post(f"{BASE_URL}/pii", files=files, timeout=300)
            results["pii"] = response.json()
            
        if "mask_transcript" in features:
            response = httpx.post(f"{BASE_URL}/mask_transcript", files=files, timeout=300)
            results["masked_transcript"] = response.json()
            
        if "sentiment_analysis" in features:
            response = httpx.post(f"{BASE_URL}/sentiment_analysis", files=files, timeout=300)
            results["sentiment"] = response.json()

    return format_results(results, analysis_options)

def format_results(results, analysis_options):
    formatted = [""] * 9  # Initialize empty results for all possible outputs
    
    # Threshold Transcript
    if "Transcript" in analysis_options:
        formatted[0] = results.get("transcription", {}).get("text", "")
    
    # Masked Transcript
    if "Masked Transcript" in analysis_options:
        formatted[1] = results.get("masked_transcript", {}).get("masked_text", "")
    
    # Compliance results
    compliance_data = results.get("compliance", {})
    if "Detected Greetings" in analysis_options:
        formatted[2] = ", ".join(compliance_data.get("detected_greetings", []))
    if "Detected Closing Statements" in analysis_options:
        formatted[3] = ", ".join(compliance_data.get("detected_closing", []))
    if "Detected Disclaimers" in analysis_options:
        formatted[4] = ", ".join(compliance_data.get("detected_disclaimers", []))
    
    # PII
    if "Detected PII" in analysis_options:
        pii_data = results.get("pii", {})
        pii_output = []
        if cc := pii_data.get("credit_card", []):
            pii_output.append(f"Credit Card: {', '.join(cc)}")
        if acc := pii_data.get("bank_account_number", []):
            pii_output.append(f"Account Number: {', '.join(acc)}")
        formatted[5] = "\n".join(pii_output)
    
    # Profanity
    if "Detected Profanity" in analysis_options:
        formatted[6] = ", ".join(results.get("profanity", {}).get("Profanity", []))
    
    # Sentiment Analysis
    if "Sentiment Analysis" in analysis_options:
        sentiment = results.get("sentiment", {})
        formatted[7] = f"Label: {sentiment.get('label', '')}\nScore: {sentiment.get('score', '')}"
    
    return formatted

iface = gr.Interface(
    fn=analyze_call,
    inputs=[
        gr.Audio(type="filepath", label="Upload Audio File"),
        gr.CheckboxGroup(
            label="Analysis Options",
            choices=[
                "Transcript",
                "Masked Transcript",
                "Detected Greetings",
                "Detected Closing Statements",
                "Detected Disclaimers",
                "Detected PII",
                "Detected Profanity",
                "Sentiment Analysis"
            ]
        )
    ],
    outputs=[
        gr.Textbox(label="Transcript"),
        gr.Textbox(label="Masked Transcript"),
        gr.Textbox(label="Detected Greetings"),
        gr.Textbox(label="Detected Closing Statements"),
        gr.Textbox(label="Detected Disclaimers"),
        gr.Textbox(label="Detected PII"),
        gr.Textbox(label="Detected Profanity"),
        gr.Textbox(label="Sentiment Analysis")
    ],
    title="Call Compliance Analyzer",
    description="Analyze audio calls for compliance, PII and quality metrics"
)

iface.launch()