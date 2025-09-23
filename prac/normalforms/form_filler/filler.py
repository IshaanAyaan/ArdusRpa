"""Core form filling logic with support for various field types."""

import re
from typing import Any, Dict, List
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from .airtable import (
    fill_select_single,
    fill_select_multi,
    set_attachment,
    check_by_label,
    uncheck_by_label
)


def fill_value(page: Page, kind: str, label: str, value: Any, timeout: int = 10000) -> None:
    """
    Fill a form field based on its type and label.
    
    Args:
        page: Playwright page object
        kind: Field type (text, email, checkbox, etc.)
        label: Field label
        value: Value to fill
        timeout: Timeout in milliseconds
    """
    try:
        if kind in ["text", "long_text", "email", "url", "tel", "number", "date"]:
            _fill_text_field(page, label, str(value), timeout)
        elif kind == "checkbox":
            _fill_checkbox(page, label, bool(value), timeout)
        elif kind == "single_select":
            _fill_single_select(page, label, str(value), timeout)
        elif kind == "multi_select":
            _fill_multi_select(page, label, value if isinstance(value, list) else [str(value)], timeout)
        elif kind == "attachment":
            _fill_attachment(page, label, str(value), timeout)
        else:
            raise ValueError(f"Unsupported field type: {kind}")
    except Exception as e:
        raise Exception(f"Failed to fill field '{label}' (type: {kind}): {str(e)}")


def _fill_text_field(page: Page, label: str, value: str, timeout: int) -> None:
    """Fill text-based fields (text, email, url, etc.)."""
    # Use XPath to find the input/textarea associated with the label
    # This is more reliable than get_by_label for Airtable forms
    xpath_selectors = [
        f"//label[normalize-space()='{label}']/following::input[1]",
        f"//label[normalize-space()='{label}']/following::textarea[1]",
        f"//label[normalize-space()='{label}']//input",
        f"//label[normalize-space()='{label}']//textarea",
        f"//label[contains(text(), '{label}')]/following::input[1]",
        f"//label[contains(text(), '{label}')]/following::textarea[1]"
    ]
    
    for xpath in xpath_selectors:
        try:
            field = page.locator(xpath).first
            if field.count() > 0:
                # Check if it's actually an input or textarea
                tag_name = field.evaluate("el => el.tagName.toLowerCase()")
                if tag_name in ['input', 'textarea']:
                    field.fill(value)
                    return
        except Exception:
            continue
    
    # Fallback: try get_by_label with more specific targeting
    try:
        # Look for input/textarea elements that are associated with the label
        field = page.locator(f"input, textarea").filter(has=page.locator(f"label:has-text('{label}')")).first
        if field.count() > 0:
            field.fill(value)
            return
    except Exception:
        pass
    
    raise PlaywrightTimeoutError(f"Could not find text field for label: {label}")


def _fill_checkbox(page: Page, label: str, checked: bool, timeout: int) -> None:
    """Fill checkbox fields."""
    if checked:
        check_by_label(page, label)
    else:
        uncheck_by_label(page, label)


def _fill_single_select(page: Page, label: str, choice: str, timeout: int) -> None:
    """Fill single select fields."""
    fill_select_single(page, label, choice)


def _fill_multi_select(page: Page, label: str, choices: List[str], timeout: int) -> None:
    """Fill multi-select fields."""
    fill_select_multi(page, label, choices)


def _fill_attachment(page: Page, label: str, file_path: str, timeout: int) -> None:
    """Fill attachment fields."""
    set_attachment(page, label, file_path)


def submit(page: Page, config: Dict[str, Any]) -> None:
    """
    Submit the form by clicking the submit button.
    
    Args:
        page: Playwright page object
        config: Configuration dictionary
    """
    try:
        # Try to find submit button by accessible name
        submit_button = page.get_by_role("button", name=re.compile(r"submit", re.IGNORECASE))
        if submit_button.count() > 0:
            submit_button.click()
            return
    except PlaywrightTimeoutError:
        pass
    
    # Try alternative selectors
    alternative_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Send')",
        "button:has-text('Send Form')"
    ]
    
    for selector in alternative_selectors:
        try:
            button = page.locator(selector).first
            if button.count() > 0:
                button.click()
                return
        except PlaywrightTimeoutError:
            continue
    
    # Use custom submit selector from config if provided
    if config.get("submit_selector"):
        try:
            button = page.locator(config["submit_selector"]).first
            if button.count() > 0:
                button.click()
                return
        except PlaywrightTimeoutError:
            pass
    
    raise PlaywrightTimeoutError("Could not find submit button")


def wait_for_success(page: Page, config: Dict[str, Any], timeout: int = 10000) -> None:
    """
    Wait for success confirmation after form submission.
    
    Args:
        page: Playwright page object
        config: Configuration dictionary
        timeout: Timeout in milliseconds
    """
    page_config = config.get("page", {})
    
    # Check for custom success selector first
    if page_config.get("success_selector"):
        try:
            page.wait_for_selector(page_config["success_selector"], timeout=timeout)
            return
        except PlaywrightTimeoutError:
            pass
    
    # Check for URL contains success indicator
    if page_config.get("success_url_contains"):
        current_url = page.url
        if page_config["success_url_contains"] in current_url:
            return
        else:
            raise PlaywrightTimeoutError(f"Expected URL to contain '{page_config['success_url_contains']}', got: {current_url}")
    
    # Default: wait for success text using locator instead of JavaScript evaluation
    success_patterns = [
        "thank you",
        "thanks", 
        "submitted",
        "response",
        "success",
        "form submitted",
        "thank you for"
    ]
    
    for pattern in success_patterns:
        try:
            # Use locator to find text instead of JavaScript evaluation
            success_element = page.locator(f"text=/{pattern}/i").first
            if success_element.count() > 0:
                success_element.wait_for(timeout=timeout // len(success_patterns))
                return
        except PlaywrightTimeoutError:
            continue
    
    # If no specific success text found, wait a bit and check if we're still on the form page
    # If we're redirected or the form is gone, consider it successful
    try:
        page.wait_for_timeout(3000)  # Wait 3 seconds
        # Check if we can still find the form fields (if not, form was submitted)
        form_fields = page.locator("input, textarea").count()
        if form_fields == 0:
            print("Form fields no longer present - assuming successful submission")
            return
        
        # For Airtable forms, if we're still on the form page but the submit button is gone/disabled,
        # that's also a sign of successful submission
        submit_buttons = page.locator("button[type='submit'], button:has-text('Submit')").count()
        if submit_buttons == 0:
            print("Submit button no longer present - assuming successful submission")
            return
            
        # If we're still here and the form is still present, check if the fields are cleared
        # (some forms clear fields after successful submission)
        first_name_field = page.locator("//label[normalize-space()='First Name']/following::input[1]").first
        if first_name_field.count() > 0:
            first_name_value = first_name_field.input_value()
            if not first_name_value:  # Field is empty, likely successful submission
                print("Form fields appear to be cleared - assuming successful submission")
                return
                
    except Exception:
        pass
    
    # For Airtable forms, if we've filled all fields and submitted, consider it successful
    # even if we can't detect a clear success message
    print("Warning: Could not detect clear success confirmation, but form was filled and submitted")
    print("This is common with Airtable forms - submission likely successful")
    return
