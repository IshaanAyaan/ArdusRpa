#!/usr/bin/env python3
"""Script to inspect the Airtable form and find available field labels."""

import time
from playwright.sync_api import sync_playwright

def inspect_form():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("Navigating to Airtable form...")
        page.goto("https://airtable.com/appNwbrMq410FQjiI/pagh1dLAVxJJf5mQz/form")
        page.wait_for_load_state("networkidle")
        
        print("Form loaded. Inspecting available fields...")
        
        # Wait a bit for the form to fully load
        time.sleep(3)
        
        # Find all labels
        labels = page.locator("label").all()
        print(f"\nFound {len(labels)} labels:")
        for i, label in enumerate(labels):
            try:
                text = label.text_content().strip()
                if text:
                    print(f"{i+1}. '{text}'")
            except:
                pass
        
        # Find all input fields
        inputs = page.locator("input, textarea, select").all()
        print(f"\nFound {len(inputs)} input fields:")
        for i, input_field in enumerate(inputs):
            try:
                input_type = input_field.get_attribute("type") or "text"
                placeholder = input_field.get_attribute("placeholder") or ""
                name = input_field.get_attribute("name") or ""
                print(f"{i+1}. Type: {input_type}, Name: '{name}', Placeholder: '{placeholder}'")
            except:
                pass
        
        # Find all buttons
        buttons = page.locator("button").all()
        print(f"\nFound {len(buttons)} buttons:")
        for i, button in enumerate(buttons):
            try:
                text = button.text_content().strip()
                button_type = button.get_attribute("type") or ""
                print(f"{i+1}. '{text}' (type: {button_type})")
            except:
                pass
        
        print("\nForm inspection complete. Browser will stay open for 30 seconds for manual inspection...")
        time.sleep(30)
        
        browser.close()

if __name__ == "__main__":
    inspect_form()
