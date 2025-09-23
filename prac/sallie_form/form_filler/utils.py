"""Utility functions for timestamp generation, CSV logging, and directory management."""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def ts() -> str:
    """Generate a timestamp string in YYYY-MM-DD_HH-MM-SS format."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def ensure_output_dir() -> None:
    """Ensure the output directory exists."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)


def save_log(row: Dict[str, Any], path: str = "output/run_log.csv") -> None:
    """
    Append a CSV row to the log file, creating the file with headers if it doesn't exist.
    
    Args:
        row: Dictionary containing log data
        path: Path to the CSV file
    """
    ensure_output_dir()
    
    file_exists = Path(path).exists()
    
    with open(path, "a", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["timestamp", "url", "status", "error"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # Write header if file is new
        if not file_exists:
            writer.writeheader()
        
        # Ensure all required fields are present
        log_row = {
            "timestamp": row.get("timestamp", ts()),
            "url": row.get("url", ""),
            "status": row.get("status", "unknown"),
            "error": row.get("error", "")
        }
        
        writer.writerow(log_row)
