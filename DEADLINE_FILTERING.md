# Deadline Filtering Implementation

This document describes the deadline filtering functionality that was added to the Dental AI Grant Finder to ensure expired opportunities are filtered out at multiple levels.

## Overview

The deadline filtering system implements a "deadline not passed" rule in three key places:

1. **Source-level filters (on fetch)** - Drop opportunities with expired deadlines during data fetching
2. **Pipeline guardrail** - Re-check and filter opportunities after merging from all sources
3. **Alert window filtering** - Only alert for opportunities within the alert window and not expired

## Implementation Details

### 1. Date Utility Functions (`src/utils.py`)

Added two core functions for date handling:

#### `parse_date(s: str | None) -> Optional[datetime]`
- Parses various date formats using `dateparser`
- Handles timezone conversion to America/Chicago
- Returns timezone-aware datetime objects
- Gracefully handles invalid or missing dates

#### `is_deadline_valid(deadline_dt: Optional[datetime]) -> bool`
- Checks if a deadline is still valid (not passed)
- Uses America/Chicago timezone for consistency
- Treats same-day deadlines as valid until 11:59pm
- Returns `True` for `None` deadlines (allows downstream logic to decide)

### 2. Source-Level Filtering

#### Grants.gov (`src/datasources/grants_gov.py`)
- Added import: `from ..utils import parse_date, is_deadline_valid`
- Modified `_parse_grants_gov_opportunity()` to:
  - Parse deadline using `parse_date(data.get("closeDate") or data.get("responseDate"))`
  - Filter out expired opportunities with `is_deadline_valid(deadline)`
  - Log skipped opportunities for debugging

#### SBIR.gov (`src/datasources/sbir_gov.py`)
- Added import: `from ..utils import parse_date, is_deadline_valid`
- Modified `_parse_sbir_opportunity()` to:
  - Parse deadline using `parse_date(data.get("dueDate") or data.get("closeDate") or data.get("endDate"))`
  - Filter out expired opportunities with `is_deadline_valid(deadline)`
  - Log skipped opportunities for debugging

### 3. Pipeline Guardrail (`src/pipeline.py`)

Added a new step in the pipeline after fetching but before processing:

```python
# Step 1.5: Pipeline guardrail - filter out expired deadlines
with display_progress("Filtering out expired deadlines..."):
    valid_opportunities = [op for op in opportunities if is_deadline_valid(op.deadline)]
    expired_count = len(opportunities) - len(valid_opportunities)
    if expired_count > 0:
        logger.info(f"Filtered out {expired_count} opportunities with expired deadlines")
    opportunities = valid_opportunities
```

### 4. Alert Window Filtering

Enhanced alert filtering to include deadline window checks:

#### `_filter_alerts_with_deadline_window(changes: List) -> List`
- Applies standard alert filtering first
- Then filters by deadline window using `_within_alert_window()`
- Logs filtered alerts for debugging

#### `_within_alert_window(opportunity: Opportunity) -> bool`
- Checks if opportunity is within `ALERT_WINDOW_DAYS`
- Returns `True` for opportunities with `None` deadlines (configurable)
- Uses date comparison in America/Chicago timezone

## Edge Cases Handled

### Rolling or Missing Deadlines
- Parsed as `None` by `parse_date()`
- Kept in pipeline but tagged as `deadline=None`
- Alert behavior configurable (currently keeps them)

### Multiple Due Dates
- `parse_date()` attempts to parse the first valid date found
- Falls back to `None` if parsing fails
- Relies on manual review for complex cases

### Timezone Handling
- All date comparisons use America/Chicago timezone
- Same-day deadlines treated as valid until end of day
- Prevents early cutoff due to timezone differences

### Archived/Closed Flags
- If APIs expose `archiveDate` or `status="closed"`, opportunities are dropped immediately
- Additional filtering can be added in data source parsers

## Testing

### Unit Tests (`tests/test_utils.py`)

Comprehensive test coverage for date utility functions:

- **Valid date formats**: ISO, natural language, various formats
- **Invalid formats**: None, empty strings, malformed dates
- **Timezone handling**: Proper localization to Central time
- **Deadline validation**: Future, past, same-day, edge cases
- **Rolling deadlines**: Handling of "ongoing", "continuous", etc.
- **Multiple dates**: Complex text with multiple date references

### Test Results
```
11 passed in 1.21s
```

All date utility tests pass successfully.

## Configuration

The deadline filtering uses these configuration values:

- `ALERT_WINDOW_DAYS` (default: 45) - Days within which to send alerts
- Timezone: America/Chicago (hardcoded for consistency)

## Google Sheets Integration

For additional safety in Google Sheets:

- **Saved Filter**: `Deadline is on or after =TODAY()`
- **Optional Helper Column**: `DAYS_LEFT =IF([@Deadline]="", "", [@Deadline]-TODAY())`

## Benefits

1. **No Expired Opportunities**: Users never see opportunities with passed deadlines
2. **Multiple Safety Nets**: Three levels of filtering ensure reliability
3. **Configurable Alerting**: Only alerts for relevant, non-expired opportunities
4. **Timezone Consistency**: All date handling uses Central time
5. **Graceful Degradation**: Handles missing or invalid dates appropriately
6. **Comprehensive Testing**: Full test coverage for edge cases

## Future Enhancements

1. **Configurable Timezone**: Allow timezone to be set via environment variable
2. **Rolling Deadline Alerts**: Option to alert for rolling/ongoing opportunities
3. **Multiple Date Parsing**: Enhanced parsing for complex deadline scenarios
4. **Deadline Extensions**: Track and handle deadline extensions
5. **Custom Alert Windows**: Different alert windows for different opportunity types 