"""Call compliance analysis module for audio processing."""

import sys

from loguru import logger
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from analyzer.analyzer import CallComplianceAnalyzer
from config import LoggerConfig
from zmq_logger import zmq_logger

# Initialize Rich console
console = Console()


def log_analysis_results(results: dict) -> None:
    """Log the analysis results using Rich formatting."""
    # Main title panel
    console.print(
        Panel("Call Compliance Analysis Results", style="bold cyan", box=box.DOUBLE),
    )

    # Masked Transcript Section
    console.print(
        Panel(
            results.get("masked_transcript", "No transcript available"),
            title="[bold]Masked Transcript[/bold]",
            border_style="blue",
            padding=(0, 2),
        ),
    )

    # PII Section
    pii_table = Table(
        title="Detected Personal Identifiable Information (PII)", box=box.SIMPLE,
    )
    pii_table.add_column("Type", style="bold red")
    pii_table.add_column("Matches", style="yellow")

    for pii_type, matches in results.get("detected_pii", {}).items():
        if matches:
            pii_table.add_row(
                pii_type.replace("_", " ").title(),
                ", ".join(matches),
            )

    console.print(
        Panel(
            pii_table if pii_table.rows else "No PII detected",
            title="[bold]Detected PII[/bold]",
            border_style="red",
        ),
    )

    # Compliance Markers Section
    compliance_table = Table(title="Compliance Markers", box=box.SIMPLE)
    compliance_table.add_column("Type", style="bold green")
    compliance_table.add_column("Phrase")
    compliance_table.add_column("Start", style="cyan")
    compliance_table.add_column("End", style="cyan")

    for marker_type, markers in results.get("compliance_markers", {}).items():
        if markers:
            for phrase, start, end in markers:
                compliance_table.add_row(
                    marker_type.title(),
                    phrase,
                    f"{start:.2f}s",
                    f"{end:.2f}s",
                )

    console.print(
        Panel(
            compliance_table
            if compliance_table.rows
            else "No compliance markers found",
            title="[bold]Compliance Markers[/bold]",
            border_style="green",
        ),
    )

    # Sentiment Analysis Section
    sentiment = results.get("sentiment", {})
    sentiment_table = Table(title="Sentiment Analysis", box=box.SIMPLE)
    sentiment_table.add_column("Label", style="bold magenta")
    sentiment_table.add_column("Score", style="magenta")
    sentiment_table.add_row(
        sentiment.get("label", "N/A"),
        str(sentiment.get("score", "N/A")),
    )

    console.print(
        Panel(
            sentiment_table,
            title="[bold]Sentiment Analysis[/bold]",
            border_style="magenta",
        ),
    )

    # Diarization Metrics Section
    diarization = results.get("diarization_metrics", {})
    diarization_table = Table(title="Diarization Metrics", box=box.SIMPLE)
    diarization_table.add_column("Metric", style="bold yellow")
    diarization_table.add_column("Value", style="yellow")

    metrics = [
        (
            "Agent Speaking Speed",
            f"{diarization.get('agent_speaking_speed_wpm', 'N/A')} WPM",
        ),
        (
            "Customer/Agent Ratio",
            diarization.get("customer_to_agent_speaking_ratio", "N/A"),
        ),
        ("Agent Interruptions", diarization.get("interruptions_by_agent", "N/A")),
        ("Average TTFT", f"{diarization.get('average_ttft', 'N/A')}s"),
    ]

    for metric, value in metrics:
        diarization_table.add_row(metric, str(value))

    console.print(
        Panel(
            diarization_table,
            title="[bold]Diarization Metrics[/bold]",
            border_style="yellow",
        ),
    )

    # Call Category Section
    console.print(
        Panel(
            results.get("category", "N/A"),
            title="[bold]Call Category[/bold]",
            border_style="cyan",
            padding=(0, 2),
        ),
    )


if __name__ == "__main__":
    # Initialize the logger configuration

    LoggerConfig()
    # Validate command-line arguments
    MIN_ARGS = 2
    if len(sys.argv) < MIN_ARGS:
        logger.error("Usage: python main.py <audio_file_path>")
        sys.exit(1)
    audio_file = sys.argv[1]
    # Log startup message
    zmq_logger.log("INFO", "Starting main process...")
    try:
        # Initialize analyzer with HF token
        analyzer = CallComplianceAnalyzer()

        # Perform analysis
        results = analyzer.full_analysis(audio_file)

        # Log results using Rich
        log_analysis_results(results)
        zmq_logger.log("INFO", "Analysis completed successfully")

    except (OSError, ValueError, RuntimeError) as e:
        logger.exception(f"Analysis failed: {e!s}")
        zmq_logger.log("ERROR", f"Analysis failed: {e!s}")
        sys.exit(1)
