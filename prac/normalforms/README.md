# Airtable Form Filler

A robust CLI tool for automating Airtable form submissions using Python and Playwright. This tool can fill various field types including text, selects, checkboxes, and file uploads.

## Features

- **Label-based field targeting**: Uses exact Airtable field labels for reliable form filling
- **Multiple field types**: Supports text, email, URL, phone, date, checkbox, single select, multi select, and file upload
- **Robust error handling**: Comprehensive error messages and timeout handling
- **Screenshot capture**: Takes full-page screenshots on success and error
- **CSV logging**: Logs all runs with timestamps and status
- **Headless operation**: Runs in headless mode by default with toggle option
- **Airtable-optimized**: Special handling for Airtable's custom select widgets

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install playwright python-dotenv
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

3. **Clone or download this project:**
   ```bash
   git clone <repository-url>
   cd normalforms
   ```

## Configuration

### 1. Environment Variables (Optional)

Copy `env.example` to `.env` and modify as needed:
```bash
cp env.example .env
```

Available options:
- `PLAYWRIGHT_HEADLESS=true` - Run browser in headless mode (default: true)
- `PLAYWRIGHT_TIMEOUT=20000` - Default timeout in milliseconds

### 2. Form Configuration (`config.json`)

```json
{
  "page": {
    "url": "https://airtable.com/appNwbrMq410FQjiI/pagh1dLAVxJJf5mQz/form",
    "idle_spinner": null,
    "success_selector": "text=/thank you|thanks|submitted|response/i",
    "success_url_contains": ""
  },
  "submit_selector": null
}
```

- `url`: The Airtable form URL
- `idle_spinner`: Optional CSS selector for loading spinner to wait for
- `success_selector`: Custom selector for success confirmation
- `success_url_contains`: URL fragment to check for success
- `submit_selector`: Custom CSS selector for submit button

### 3. Form Data (`data.json`)

```json
[
  {"label": "Full Name", "type": "text", "value": "Ishaan Ranjan"},
  {"label": "Email", "type": "email", "value": "ishaan@example.com"},
  {"label": "Phone", "type": "tel", "value": "+1 480 555 0100"},
  {"label": "Country", "type": "single_select", "value": "United States"},
  {"label": "Interests", "type": "multi_select", "value": ["AI", "Debate"]},
  {"label": "Date of Birth", "type": "date", "value": "2007-05-15"},
  {"label": "Subscribe to updates", "type": "checkbox", "value": true},
  {"label": "About you", "type": "long_text", "value": "Short bio here."},
  {"label": "Resume", "type": "attachment", "value": "/absolute/path/to/resume.pdf"}
]
```

**Important**: Use the **exact field labels** as they appear in your Airtable form for best results.

## Usage

### Basic Usage

```bash
python -m form_filler --data data.json --config config.json
```

### Advanced Usage

```bash
python -m form_filler \
  --url "https://airtable.com/your-form-url" \
  --data data.json \
  --config config.json \
  --headless true \
  --timeout 30000
```

### Command Line Options

- `--url`: Override the form URL (overrides config.page.url)
- `--data`: Path to JSON file containing form data (default: data.json)
- `--config`: Path to JSON file containing configuration (default: config.json)
- `--headless`: Run browser in headless mode (true/false, default from .env)
- `--timeout`: Timeout in milliseconds (default: 20000)

## Supported Field Types

| Type | Description | Example Value |
|------|-------------|---------------|
| `text` | Single-line text input | `"John Doe"` |
| `long_text` | Multi-line text area | `"This is a longer description..."` |
| `email` | Email input | `"user@example.com"` |
| `url` | URL input | `"https://example.com"` |
| `tel` | Phone number input | `"+1 555 123 4567"` |
| `number` | Numeric input | `42` |
| `date` | Date input | `"2007-05-15"` |
| `checkbox` | Checkbox (true/false) | `true` |
| `single_select` | Dropdown with single selection | `"United States"` |
| `multi_select` | Dropdown with multiple selections | `["Option 1", "Option 2"]` |
| `attachment` | File upload | `"/path/to/file.pdf"` |

## Output

The tool creates an `output/` directory with:

- **Screenshots**: `{timestamp}.png` (success) and `{timestamp}_error.png` (errors)
- **Logs**: `run_log.csv` with timestamp, URL, status, and error details

## Troubleshooting

### Common Issues

1. **Field not found**: Ensure field labels in `data.json` match exactly with the form
2. **Timeout errors**: Increase timeout value or check network connectivity
3. **Select fields not working**: Airtable uses custom widgets; the tool has special handling for these
4. **File uploads failing**: Ensure file paths are absolute and files exist

### Debug Mode

Run with `--headless false` to see the browser in action:
```bash
python -m form_filler --headless false --data data.json
```

### Private Forms

For private Airtable forms that require authentication:
1. Log in to Airtable in a regular browser
2. Copy the form URL
3. The tool will use your existing session

## Project Structure

```
normalforms/
├── form_filler/
│   ├── __init__.py
│   ├── __main__.py      # CLI entry point
│   ├── filler.py        # Core form filling logic
│   ├── airtable.py      # Airtable-specific helpers
│   └── utils.py         # Utilities (timestamps, logging)
├── config.json          # Form configuration
├── data.json            # Sample form data
├── env.example          # Environment variables template
├── pyproject.toml       # Project dependencies
└── README.md           # This file
```

## Requirements

- Python 3.10+
- Playwright
- python-dotenv

## License

This project is open source and available under the MIT License.
