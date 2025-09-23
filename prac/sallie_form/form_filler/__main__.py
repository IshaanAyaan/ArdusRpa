"""CLI entry point for the Airtable form filler."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from .filler import fill_value, submit, wait_for_success
from .utils import ts, save_log, ensure_output_dir


def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {file_path}: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point."""
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Airtable Form Filler - Automate form submissions using Playwright"
    )
    parser.add_argument(
        "--url",
        help="Override the form URL (overrides config.page.url)"
    )
    parser.add_argument(
        "--data",
        default="data.json",
        help="Path to JSON file containing form data (default: data.json)"
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to JSON file containing configuration (default: config.json)"
    )
    parser.add_argument(
        "--headless",
        type=lambda x: x.lower() in ('true', '1', 'yes', 'on'),
        default=os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() in ('true', '1', 'yes', 'on'),
        help="Run browser in headless mode (default: from .env or false)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20000,
        help="Timeout in milliseconds (default: 20000)"
    )
    
    args = parser.parse_args()
    
    # Load configuration and data
    config = load_json_file(args.config)
    data = load_json_file(args.data)
    
    # Determine the form URL
    url = args.url or config.get("page", {}).get("url")
    if not url:
        print("Error: No URL provided. Use --url or set config.page.url")
        sys.exit(1)
    
    # Ensure output directory exists
    ensure_output_dir()
    
    # Initialize variables for logging
    timestamp = ts()
    status = "success"
    error_message = ""
    screenshot_path = f"output/{timestamp}.png"
    
    try:
        with sync_playwright() as p:
            # Launch browser
            browser = p.chromium.launch(headless=args.headless)
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            
            print(f"Navigating to: {url}")
            
            # Navigate to the form
            page.goto(url, wait_until="domcontentloaded", timeout=args.timeout)
            page.wait_for_load_state("networkidle", timeout=args.timeout)
            
            # Wait for idle spinner if configured
            page_config = config.get("page", {})
            if page_config.get("idle_spinner"):
                try:
                    page.wait_for_selector(page_config["idle_spinner"], state="detached", timeout=args.timeout)
                except PlaywrightTimeoutError:
                    print("Warning: Idle spinner did not disappear within timeout")
            
            print("Form loaded, starting to fill fields...")
            
            # Fill form fields
            if not isinstance(data, list):
                print("Error: data.json must contain a list of field objects")
                sys.exit(1)
            
            for field_data in data:
                if not isinstance(field_data, dict) or not all(key in field_data for key in ["label", "type", "value"]):
                    print("Error: Each field in data.json must have 'label', 'type', and 'value' keys")
                    sys.exit(1)
                
                label = field_data["label"]
                field_type = field_data["type"]
                value = field_data["value"]
                
                print(f"Filling field: {label} ({field_type}) = {value}")
                fill_value(page, field_type, label, value, args.timeout)
            
            print("All fields filled, submitting form...")
            
            # Submit the form
            submit(page, config)
            
            print("Form submitted, waiting for success confirmation...")
            
            # Take screenshot immediately after submission
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"Screenshot saved: {screenshot_path}")
            
            # Wait for success
            wait_for_success(page, config, args.timeout)
            
            print("Success! Form submitted successfully.")
            
    except PlaywrightTimeoutError as e:
        status = "timeout"
        error_message = f"Timeout error: {str(e)}"
        print(f"Error: {error_message}")
        
        # Take error screenshot
        try:
            page.screenshot(path=f"output/{timestamp}_error.png", full_page=True)
            print(f"Error screenshot saved: output/{timestamp}_error.png")
        except:
            pass
            
    except Exception as e:
        status = "error"
        error_message = str(e)
        print(f"Error: {error_message}")
        
        # Take error screenshot
        try:
            page.screenshot(path=f"output/{timestamp}_error.png", full_page=True)
            print(f"Error screenshot saved: output/{timestamp}_error.png")
        except:
            pass
    
    finally:
        # Log the result
        log_row = {
            "timestamp": timestamp,
            "url": url,
            "status": status,
            "error": error_message
        }
        save_log(log_row)
        
        # Clean up
        try:
            context.close()
            browser.close()
        except:
            pass
    
    # Exit with appropriate code
    if status == "success":
        print("Form filling completed successfully!")
        sys.exit(0)
    else:
        print(f"Form filling failed: {error_message}")
        sys.exit(1)


if __name__ == "__main__":
    main()
