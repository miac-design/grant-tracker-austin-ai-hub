# Dental AI Grant Finder

A production-ready agent that automatically discovers, scores, and tracks SBIR/Grants.gov opportunities relevant to dental AI, appointment scheduling, and patient engagement. **Targets for-profit (SBIR/STTR) eligibility** and provides intelligent change detection with alerts.

## What It Does

- **Queries** Grants.gov (Applicant API) and SBIR.gov for dental AI opportunities
- **Filters** for for-profit (SBIR/STTR) eligibility 
- **Scores** opportunities by fit, deadline proximity, and award size
- **Persists state** and sends alerts **only for new or changed** items
- **Outputs** to Google Sheets with optional Slack/email notifications
- **Runs on schedule** (cron/GitHub Actions) or manually

## Quick Start

### 1. Setup Google Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Create a Service Account
5. Download the JSON key file
6. Place it at `./creds/service_account.json`

### 2. Create Google Sheet

1. Create a new Google Sheet
2. Share it with your service account email (found in the JSON file)
3. Note the sheet name and tab name

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings:
# - GOOGLE_SHEET_NAME
# - GOOGLE_SHEET_TAB  
# - Optional: SLACK_WEBHOOK_URL, email settings
```

### 4. Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the pipeline
python -m src.pipeline

# Dry run (no writes)
python -m src.pipeline --dry-run

# Check recent changes
python -m src.pipeline --since 14d
```

## Configuration

### Required Settings

- `GOOGLE_SERVICE_ACCOUNT_JSON_PATH`: Path to your service account JSON
- `GOOGLE_SHEET_NAME`: Name of your Google Sheet
- `GOOGLE_SHEET_TAB`: Worksheet tab name

### Optional APIs

- `GRANTSGOV_API_KEY`: Grants.gov API key (can be blank)
- `SBIR_API_BASE`: SBIR.gov API endpoint

### Notifications

- `SLACK_WEBHOOK_URL`: Slack webhook for alerts
- Email settings: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`, etc.

### Scheduling

- `ALERT_WINDOW_DAYS`: Days ahead to alert for deadlines (default: 45)
- `TIMEZONE`: Your timezone (default: America/Chicago)

## How Alerts Work

The system only alerts you when:

- **NEW** opportunities are found
- **CHANGED** opportunities (deadline/award updates)
- Opportunities with `total_score >= 60` within `ALERT_WINDOW_DAYS`

### Alert Channels

- **Slack**: Concise markdown with program, agency, deadline, score, URL
- **Email**: Plain text or HTML template with full details
- **Google Sheets**: Always updated with current opportunities

## Customization

### Keywords & Scoring

Edit `src/keywords.py` to modify:
- Positive keywords for matching
- Exclusion keywords
- Agency preferences

Edit `src/ranking/rules.py` to adjust:
- Scoring weights (fit/deadline/award)
- Score thresholds
- Agency bonuses

### Scheduling

**Local Cron:**
```bash
# Add to crontab
0 9 * * * cd /path/to/dental-ai-grant-finder && python -m src.pipeline
```

**GitHub Actions:**
- Enable the workflow in `.github/workflows/daily-run.yml`
- Add secrets for Google service account JSON
- Runs daily at 2 PM UTC

## Development

```bash
# Format code
make format

# Lint code  
make lint

# Run tests
make test

# Install pre-commit hooks
pre-commit install
```

## Project Structure

```
dental-ai-grant-finder/
├── src/
│   ├── datasources/     # Grants.gov & SBIR.gov APIs
│   ├── ranking/         # Scoring algorithms
│   ├── storage/         # SQLite DB & Google Sheets
│   ├── notify/          # Slack & email alerts
│   └── pipeline.py      # Main orchestrator
├── tests/               # Unit tests
├── ops/                 # Deployment scripts
└── creds/               # Service account JSON
```

## API Endpoints (Optional)

If you enable the FastAPI server:

```bash
python -m src.api
```

- `GET /healthz`: Health check
- `GET /latest`: Top 20 opportunities
- `GET /opportunities`: Fresh opportunities with advanced filtering

### `/opportunities` Endpoint

The main endpoint for fetching fresh opportunities from Grants.gov and SBIR.gov:

**URL**: `http://127.0.0.1:8000/opportunities?days=180&min_score=40&only_open=true`

**Query Parameters:**
- `q` (optional): Keyword filter - search in title/summary
- `days` (default: 180): Lookback window in days for posted date
- `min_score` (default: 0): Minimum total_score to include
- `only_open` (default: true): Exclude past-deadline items if true
- `limit` (default: 100): Maximum number of results to return

**Example Requests:**

```bash
# Get all open opportunities from last 180 days
curl "http://127.0.0.1:8000/opportunities"

# Search for dental-specific opportunities
curl "http://127.0.0.1:8000/opportunities?q=dental&days=365&min_score=40"

# Get high-scoring opportunities only
curl "http://127.0.0.1:8000/opportunities?min_score=70&only_open=true"

# Search for AI/scheduling opportunities
curl "http://127.0.0.1:8000/opportunities?q=appointment%20scheduling&days=90"
```

**Response Format:**
```json
{
  "count": 3,
  "total_fetched": 3,
  "last_updated": "2025-01-15T10:30:00",
  "filters": {
    "query": null,
    "days": 180,
    "min_score": 40,
    "only_open": true,
    "limit": 100
  },
  "results": [
    {
      "title": "SBIR Phase I: AI-Powered Dental Appointment Management System",
      "agency": "NIH",
      "deadline": "2025-02-15",
      "award": "$225,000",
      "url": "https://grants.nih.gov/grants/guide/pa-files/PAR-24-XXX.html",
      "total_score": 85,
      "why_it_fits": "Dental/oral health focus; Appointment/scheduling focus; AI/ML technology; Preferred agency; SBIR/STTR program; For-profit eligible",
      "opportunity_id": "FALLBACK001",
      "source": "SBIR_GOV",
      "summary": "Development of an AI-powered system for dental appointment scheduling, patient engagement, and practice management..."
    }
  ]
}
```

**Features:**
- **Fallback Data**: Returns mock opportunities when real APIs are unavailable
- **Smart Filtering**: Filters by keywords, deadline, and score
- **Scoring**: Each opportunity includes a total_score and why_it_fits explanation
- **Real-time**: Fetches fresh data from Grants.gov and SBIR.gov APIs
- **Healthcare Focus**: Prioritizes dental, AI, and healthcare technology opportunities

## Troubleshooting

### Common Issues

1. **Google Sheets Permission Error**: Ensure service account email has edit access
2. **API Rate Limits**: Grants.gov has rate limits; the system handles this gracefully
3. **Missing Opportunities**: Check keywords in `src/keywords.py`
4. **No Alerts**: Verify notification settings and check `ALERT_WINDOW_DAYS`

### Logs

The system uses `rich` for pretty console output. Check for:
- Fetch counts from each source
- Change detection results
- Alert delivery status

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run `make test` and `make lint`
5. Submit a pull request

## License

MIT License - see LICENSE file for details. 