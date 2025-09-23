# Sallie Mae $2,000 No Essay Scholarship Form Filler

A robust CLI tool for automating the [Sallie Mae $2,000 No Essay Scholarship](https://www.sallie.com/scholarships/no-essay) application using Python and Playwright.

## About the Scholarship

The Sallie Mae $2,000 No Essay Scholarship is a monthly scholarship contest where:
- **Amount**: $2,000 per month
- **Deadline**: Monthly (current deadline: September 30, 2025)
- **Requirements**: No essay required, just fill out a simple form
- **Eligibility**: Legal residents of the US, age 16+, who meet one of four criteria:
  1. Parent with child enrolled in college/university
  2. Student currently enrolled in college/university  
  3. Parent with child enrolled as high school senior
  4. High school junior/senior planning to attend college

## Features

- **Automated form filling** for all scholarship application fields
- **Label-based targeting** for reliable form interaction
- **Screenshot capture** after submission
- **CSV logging** of all application attempts
- **Visible browser mode** by default for transparency
- **Robust error handling** with detailed logging

## Installation

1. **Install Python dependencies:**
   ```bash
   pip install playwright python-dotenv
   ```

2. **Install Playwright browsers:**
   ```bash
   playwright install
   ```

## Configuration

### Form Data (`data.json`)

The form includes these fields:
- Student/Parent status (radio button)
- High school graduation year (dropdown)
- Level of study (dropdown) 
- College/university name (text input)
- Phone number for texts (optional)
- Consent checkbox (required)

Example configuration:
```json
[
  {"label": "Are you a student or a parent of a student?", "type": "single_select", "value": "Student"},
  {"label": "What is the student's high school graduation year?", "type": "single_select", "value": "2026"},
  {"label": "What is the student's upcoming level of study?", "type": "single_select", "value": "Undergraduate"},
  {"label": "What college/university will you be attending, or are currently attending?", "type": "text", "value": "Stanford University"},
  {"label": "Want to receive texts around planning and paying for college?", "type": "tel", "value": "+1 555 123 4567"},
  {"label": "By checking this box, you consent to being entered for a chance to win this scholarship and agree to the Official Rules, receiving marketing emails, and the collection and use of your personal information by SLM Education Services, LLC in accordance with our Privacy Policy", "type": "checkbox", "value": true}
]
```

## Usage

### Basic Usage
```bash
python -m form_filler --data data.json --config config.json
```

### With Custom Options
```bash
python -m form_filler \
  --data data.json \
  --config config.json \
  --headless false \
  --timeout 30000
```

## Output

The tool creates an `output/` directory with:
- **Screenshots**: `{timestamp}.png` after each submission
- **Logs**: `run_log.csv` with timestamp, URL, status, and error details

## Important Notes

- **Monthly Applications**: You can apply each month for a new chance to win
- **Eligibility**: Make sure you meet the eligibility requirements before applying
- **Consent Required**: The consent checkbox must be checked to submit
- **Real Information**: Use accurate information as this is a legitimate scholarship

## Scholarship Details

- **Website**: [https://www.sallie.com/scholarships/no-essay](https://www.sallie.com/scholarships/no-essay)
- **Amount**: $2,000 per month
- **Frequency**: Monthly winners
- **Administrator**: US Sweeps (scholarship administration partner)
- **Payment**: Funds sent directly to winner's school

## Disclaimer

This tool is for educational purposes. Always ensure you meet eligibility requirements and provide accurate information when applying for scholarships.
