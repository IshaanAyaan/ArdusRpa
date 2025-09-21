import os
import csv
import time
import argparse
from typing import Dict, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    # webdriver-manager simplifies driver setup; falls back to local driver if unavailable
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service as ChromeService
    HAVE_WDM = True
except Exception:
    HAVE_WDM = False


DEFAULT_FORM_URL = (
    "https://docs.google.com/forms/d/e/1FAIpQLScA-rqyk6M4voXpfloq5HnZUrlXt8JG32qboWXNqJpW7lhUQQ/viewform?usp=dialog"
)


def setup_driver(headless: bool = False) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    if headless:
        # Use new headless for Chrome 109+
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1000")

    # Helpful if popups/notifications appear
    prefs = {
        "profile.default_content_setting_values.notifications": 2,
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
    }
    options.add_experimental_option("prefs", prefs)

    try:
        if HAVE_WDM:
            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=options)
        # Fallback to system-provided chromedriver
        return webdriver.Chrome(options=options)
    except Exception as e:
        raise RuntimeError(
            f"Failed to start Chrome WebDriver. Ensure Chrome/Chromedriver are installed and compatible. Original error: {e}"
        )


def wait_for_form_ready(driver: webdriver.Chrome, timeout: int = 20) -> None:
    WebDriverWait(driver, timeout).until(
        EC.any_of(
            EC.presence_of_element_located((By.XPATH, "//form")),
            EC.presence_of_element_located((By.XPATH, "//input[@aria-label]")),
            EC.presence_of_element_located((By.XPATH, "//textarea[@aria-label]")),
        )
    )


def _candidate_label_variants(label: str) -> List[str]:
    # Google Forms sometimes appends "(Required)" or an asterisk; try a few variants
    base = label.strip()
    variants = [base, f"{base} (Required)", f"{base} *", f"{base}*"]
    return variants


def _xpath_literal(s: str) -> str:
    """Return an XPath string literal representing s.
    Handles cases where s contains both single and double quotes.
    """
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    # Contains both quote types: use concat with pieces
    parts = s.split("'")
    tokens: List[str] = []
    for i, p in enumerate(parts):
        if p:
            tokens.append(f"'{p}'")
        if i != len(parts) - 1:
            tokens.append("\"'\"")  # an XPath literal for a single quote
    return "concat(" + ", ".join(tokens) + ")"


def _find_in_question_container(driver: webdriver.Chrome, label: str, inner_xpath: str):
    # Try to scope search to the question block containing the label text
    qlit = _xpath_literal(label)
    containers = driver.find_elements(By.XPATH, f"//div[@role='listitem' and .//*[normalize-space()={qlit}]]")
    for c in containers:
        try:
            el = c.find_element(By.XPATH, inner_xpath)
            return el
        except NoSuchElementException:
            continue
    return None


def fill_text_field(driver: webdriver.Chrome, label: str, value: str) -> bool:
    variants = _candidate_label_variants(label)
    locators = []
    for v in variants:
        vq = _xpath_literal(v)
        locators.extend(
            [
                f"//input[@aria-label={vq}]",
                f"//textarea[@aria-label={vq}]",
                f"//input[contains(@aria-label, {vq})]",
                f"//textarea[contains(@aria-label, {vq})]",
            ]
        )

    # Try scoped to question container first
    for v in variants:
        el = _find_in_question_container(
            driver, v, ".//input | .//textarea"
        )
        if el is not None:
            try:
                el.clear()
            except Exception:
                pass
            el.send_keys(value)
            return True

    # Fallback to global locators
    for xp in locators:
        try:
            el = driver.find_element(By.XPATH, xp)
            try:
                el.clear()
            except Exception:
                pass
            el.send_keys(value)
            return True
        except NoSuchElementException:
            continue
    return False


def select_radio(driver: webdriver.Chrome, question_label: str, option_value: str) -> bool:
    # Prefer within the question container
    ov = _xpath_literal(option_value)
    el = _find_in_question_container(driver, question_label, f".//div[@role='radio' and @aria-label={ov}]")
    if el is None:
        # fallback: global search by aria-label
        try:
            el = driver.find_element(By.XPATH, f"//div[@role='radio' and @aria-label={ov}]")
        except NoSuchElementException:
            # As a last resort, try contains()
            try:
                el = driver.find_element(By.XPATH, f"//div[@role='radio' and contains(@aria-label, {ov})]")
            except NoSuchElementException:
                el = None
    if el is not None:
        el.click()
        return True
    return False


def select_checkboxes(driver: webdriver.Chrome, question_label: str, option_values: List[str]) -> bool:
    success = True
    for opt in option_values:
        opt = opt.strip()
        if not opt:
            continue
        ov = _xpath_literal(opt)
        el = _find_in_question_container(driver, question_label, f".//div[@role='checkbox' and @aria-label={ov}]")
        if el is None:
            # fallback global
            try:
                el = driver.find_element(By.XPATH, f"//div[@role='checkbox' and @aria-label={ov}]")
            except NoSuchElementException:
                try:
                    el = driver.find_element(By.XPATH, f"//div[@role='checkbox' and contains(@aria-label, {ov})]")
                except NoSuchElementException:
                    el = None
        if el is not None:
            # Click only if not already selected
            aria_checked = el.get_attribute("aria-checked")
            if aria_checked != "true":
                el.click()
        else:
            success = False
    return success


def click_button_by_text(driver: webdriver.Chrome, texts: List[str], timeout: int = 5) -> bool:
    # Google Forms buttons are role='button' with nested span text
    for t in texts:
        tnorm = t.strip()
        tlit = _xpath_literal(tnorm)
        xpath = f"//div[@role='button' and .//span[normalize-space()={tlit}]]"
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            el.click()
            return True
        except TimeoutException:
            continue
    return False


def submit_form(driver: webdriver.Chrome) -> None:
    # Some forms have multiple pages; click Next until Submit appears
    for _ in range(5):
        if click_button_by_text(driver, ["Submit", "Send"]):
            return
        # If no Submit yet, try Next
        if not click_button_by_text(driver, ["Next", "Continue"]):
            break
        time.sleep(0.8)
    # Final attempt at Submit after last Next
    click_button_by_text(driver, ["Submit", "Send"])  # best effort


def accept_cookies_if_present(driver: webdriver.Chrome) -> None:
    # Best-effort: handle possible consent dialogs
    click_button_by_text(driver, ["I agree", "Accept all", "Accept All", "Accept"], timeout=2)


def parse_row_types(row: Dict[str, str]):
    text_fields = {}
    radio_fields = {}
    checkbox_fields = {}
    for key, val in row.items():
        if val is None:
            continue
        k = key.strip()
        v = str(val).strip()
        if not k or v == "":
            continue
        if k.lower().endswith("(choice)"):
            label = k[: -len("(choice)")].strip()
            radio_fields[label] = v
        elif k.lower().endswith("(multi)"):
            label = k[: -len("(multi)")].strip()
            checkbox_fields[label] = [s.strip() for s in v.split(";") if s.strip()]
        else:
            text_fields[k] = v
    return text_fields, radio_fields, checkbox_fields


def fill_and_submit_once(driver: webdriver.Chrome, form_url: str, row: Dict[str, str]) -> None:
    driver.get(form_url)
    wait_for_form_ready(driver)
    accept_cookies_if_present(driver)

    text_fields, radio_fields, checkbox_fields = parse_row_types(row)

    # Fill text/textarea
    for label, value in text_fields.items():
        ok = fill_text_field(driver, label, value)
        print(f"[text] {label} -> {'OK' if ok else 'NOT FOUND'}")

    # Radios
    for label, option in radio_fields.items():
        ok = select_radio(driver, label, option)
        print(f"[radio] {label} = {option} -> {'OK' if ok else 'NOT FOUND'}")

    # Checkboxes
    for label, options in checkbox_fields.items():
        ok = select_checkboxes(driver, label, options)
        opts = "; ".join(options)
        print(f"[check] {label} = {opts} -> {'OK' if ok else 'PARTIAL/NOT FOUND'}")

    # Submit
    submit_form(driver)

    # Small wait so the submission page loads
    time.sleep(1.5)


def read_csv_rows(csv_path: str) -> List[Dict[str, str]]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _text(el) -> str:
    try:
        return el.text.strip()
    except Exception:
        return ""


def _first_text(el, xpaths: List[str]) -> str:
    for xp in xpaths:
        try:
            found = el.find_element(By.XPATH, xp)
            t = _text(found)
            if t:
                return t
        except NoSuchElementException:
            continue
    return ""


def _collect_aria_labels(container, role: str) -> List[str]:
    try:
        els = container.find_elements(By.XPATH, f".//div[@role='{role}']")
        labels = [e.get_attribute("aria-label") or "" for e in els]
        return [l.strip() for l in labels if l and l.strip()]
    except Exception:
        return []


def extract_form_questions(driver: webdriver.Chrome) -> List[Dict[str, object]]:
    # Assumes driver is already on the form page
    wait_for_form_ready(driver)
    accept_cookies_if_present(driver)

    items = driver.find_elements(By.XPATH, "//div[@role='listitem']")
    questions = []
    for idx, item in enumerate(items, start=1):
        # Determine type
        radios = _collect_aria_labels(item, "radio")
        checks = _collect_aria_labels(item, "checkbox")
        has_textarea = len(item.find_elements(By.XPATH, ".//textarea")) > 0
        has_input = len(item.find_elements(By.XPATH, ".//input")) > 0

        # Label candidates
        label = _first_text(item, [
            ".//div[@role='heading']//span",
            ".//div[@role='heading']",
        ])
        if not label:
            # Fallback to aria-label of first input/textarea
            try:
                el = item.find_element(By.XPATH, ".//input | .//textarea")
                label = el.get_attribute("aria-label") or ""
            except NoSuchElementException:
                label = ""

        label = (label or f"Question {idx}").strip()

        if radios:
            qtype = "choice"
            options = radios
        elif checks:
            qtype = "multi"
            options = checks
        elif has_textarea:
            qtype = "paragraph"
            options = []
        elif has_input:
            qtype = "text"
            options = []
        else:
            # Unknown/unsupported (e.g., dropdown/date/time/file upload)
            qtype = "unknown"
            # Try detect dropdown listbox
            listbox = item.find_elements(By.XPATH, ".//*[@role='listbox']")
            if listbox:
                qtype = "choice"  # treat dropdown like single choice for CSV
            options = []

        questions.append({
            "label": label,
            "type": qtype,
            "options": options,
        })
    return questions


def run_inspector(driver: webdriver.Chrome, form_url: str, write_template: str = "") -> None:
    driver.get(form_url)
    qs = extract_form_questions(driver)

    print("Detected Questions:\n")
    for i, q in enumerate(qs, start=1):
        line = f"{i}. [{q['type']}] {q['label']}"
        if q["options"]:
            opts = ", ".join(q["options"][:10])
            if len(q["options"]) > 10:
                opts += ", ..."
            line += f"\n   Options: {opts}"
        print(line)

    # Build CSV header suggestion
    headers: List[str] = []
    sample: Dict[str, str] = {}
    for q in qs:
        t = q["type"]
        lbl = q["label"]
        if t == "text" or t == "paragraph":
            headers.append(lbl)
            sample[lbl] = f"Sample {lbl}"[:60]
        elif t == "choice":
            h = f"{lbl} (choice)"
            headers.append(h)
            sample[h] = q["options"][0] if q["options"] else ""
        elif t == "multi":
            h = f"{lbl} (multi)"
            headers.append(h)
            if q["options"]:
                sample[h] = "; ".join(q["options"][:2])
            else:
                sample[h] = ""
        else:
            # Unsupported: skip from CSV to avoid confusion
            continue

    print("\nSuggested CSV headers:")
    print(",".join([f'"{h}"' if ("," in h or "\"" in h) else h for h in headers]))

    if write_template:
        path = write_template
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerow(sample)
            print(f"\nWrote template with sample row to: {path}")
        except Exception as e:
            print(f"Failed to write template: {e}")


def main():
    parser = argparse.ArgumentParser(description="Google Forms RPA filler from CSV")
    parser.add_argument("--csv", default="form_data.csv", help="Path to CSV with submissions")
    parser.add_argument("--url", default=DEFAULT_FORM_URL, help="Google Form URL (viewform)")
    parser.add_argument("--headless", action="store_true", help="Run Chrome in headless mode")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of rows to submit (0 = all)")
    parser.add_argument("--inspect", action="store_true", help="Inspect the form and print detected questions")
    parser.add_argument("--write-template", default="", help="Write a CSV template with detected headers")
    args = parser.parse_args()

    driver = setup_driver(headless=args.headless or os.getenv("HEADLESS") == "1")
    try:
        if args.inspect:
            run_inspector(driver, args.url, args.write_template)
            return

        rows = read_csv_rows(args.csv)
        if args.limit > 0:
            rows = rows[: args.limit]
        if not rows:
            print("No rows found in CSV. Nothing to submit.")
            return

        for i, row in enumerate(rows, start=1):
            print(f"\n--- Submitting row {i}/{len(rows)} ---")
            fill_and_submit_once(driver, args.url, row)
            if i < len(rows):
                driver.get(args.url)
                time.sleep(0.8)
        print("\nDone.")
    finally:
        # Keep browser open if not headless for quick inspection
        if args.headless or os.getenv("KEEP_OPEN") != "1":
            driver.quit()


if __name__ == "__main__":
    main()
