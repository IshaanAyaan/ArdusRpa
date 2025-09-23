"""Airtable-specific helpers for handling custom widgets like selects and attachments."""

from pathlib import Path
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError


def open_field(page: Page, label: str) -> None:
    """
    Focus a field by clicking the control next to the label text.
    
    Args:
        page: Playwright page object
        label: Exact field label text
    """
    try:
        # Try the standard get_by_label approach first, but use .first to avoid strict mode violations
        field = page.get_by_label(label).first
        if field.count() > 0:
            field.click()
            return
    except PlaywrightTimeoutError:
        pass
    
    # XPath fallback: find label and click the nearest focusable element
    try:
        xpath = f"//label[normalize-space()='{label}']"
        label_element = page.locator(xpath).first
        
        if label_element.count() > 0:
            # Try to find a focusable element after the label
            focusable_xpath = f"{xpath}/following::input[1] | {xpath}/following::textarea[1] | {xpath}/following::select[1] | {xpath}/following::button[1]"
            focusable = page.locator(focusable_xpath).first
            
            if focusable.count() > 0:
                focusable.click()
                return
            
            # If no focusable element found, try clicking the label itself
            label_element.click()
    except PlaywrightTimeoutError:
        raise PlaywrightTimeoutError(f"Could not find field with label: {label}")


def fill_select_single(page: Page, label: str, choice: str) -> None:
    """
    Fill a single select field by opening it and selecting the choice.
    
    Args:
        page: Playwright page object
        label: Field label
        choice: Option to select
    """
    open_field(page, label)
    
    # Open the dropdown (try Enter or Space)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)  # Brief wait for dropdown to open
    
    # Type the choice and press Enter to select
    page.keyboard.insert_text(choice)
    page.keyboard.press("Enter")
    page.wait_for_timeout(300)  # Brief wait for selection to register


def fill_select_multi(page: Page, label: str, choices: list) -> None:
    """
    Fill a multi-select field by selecting multiple options.
    
    Args:
        page: Playwright page object
        label: Field label
        choices: List of options to select
    """
    for choice in choices:
        open_field(page, label)
        
        # Open the dropdown
        page.keyboard.press("Enter")
        page.wait_for_timeout(500)
        
        # Type the choice and press Enter to select
        page.keyboard.insert_text(choice)
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        
        # For multi-select, we might need to click elsewhere to deselect
        # or press Escape to close the dropdown before selecting the next option
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)


def set_attachment(page: Page, label: str, file_path: str) -> None:
    """
    Upload a file to an attachment field.
    
    Args:
        page: Playwright page object
        label: Field label
        file_path: Path to the file to upload
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        # Try to find file input by label first
        file_input = page.get_by_label(label).locator("input[type='file']")
        if file_input.count() > 0:
            file_input.set_input_files(str(file_path))
            return
    except PlaywrightTimeoutError:
        pass
    
    # XPath fallback: find file input near the label
    try:
        xpath = f"//label[normalize-space()='{label}']//input[@type='file']"
        file_input = page.locator(xpath).first
        
        if file_input.count() > 0:
            file_input.set_input_files(str(file_path))
        else:
            raise PlaywrightTimeoutError(f"Could not find file input for label: {label}")
    except PlaywrightTimeoutError:
        raise PlaywrightTimeoutError(f"Could not find file input for label: {label}")


def check_by_label(page: Page, label: str) -> None:
    """
    Check a checkbox by its label.
    
    Args:
        page: Playwright page object
        label: Checkbox label
    """
    try:
        checkbox = page.get_by_label(label)
        if checkbox.count() > 0:
            checkbox.check()
            return
    except PlaywrightTimeoutError:
        pass
    
    # XPath fallback
    xpath = f"//label[normalize-space()='{label}']//input[@type='checkbox']"
    checkbox = page.locator(xpath).first
    if checkbox.count() > 0:
        checkbox.check()
    else:
        raise PlaywrightTimeoutError(f"Could not find checkbox for label: {label}")


def uncheck_by_label(page: Page, label: str) -> None:
    """
    Uncheck a checkbox by its label.
    
    Args:
        page: Playwright page object
        label: Checkbox label
    """
    try:
        checkbox = page.get_by_label(label)
        if checkbox.count() > 0:
            checkbox.uncheck()
            return
    except PlaywrightTimeoutError:
        pass
    
    # XPath fallback
    xpath = f"//label[normalize-space()='{label}']//input[@type='checkbox']"
    checkbox = page.locator(xpath).first
    if checkbox.count() > 0:
        checkbox.uncheck()
    else:
        raise PlaywrightTimeoutError(f"Could not find checkbox for label: {label}")
