"""Utility functions for the dental AI grant finder."""

import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional

import pytz
import dateparser
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .models import Opportunity, ChangeEvent, PipelineResult

console = Console()
logger = logging.getLogger(__name__)

# Timezone for deadline validation
CENTRAL = pytz.timezone("America/Chicago")


def parse_date(s: str | None) -> Optional[datetime]:
    """
    Parse a date string into a timezone-aware datetime object.
    
    Args:
        s: Date string to parse (e.g., "Sep 30, 2025", "2025-09-30", etc.)
        
    Returns:
        Timezone-aware datetime object or None if parsing fails
    """
    if not s:
        return None
    
    try:
        dt = dateparser.parse(s)
        if not dt:
            return None
        
        # Remove timezone info if present and localize to Central time
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        
        return CENTRAL.localize(dt)
    except Exception as e:
        logger.warning(f"Failed to parse date '{s}': {e}")
        return None


def is_deadline_valid(deadline_dt: Optional[datetime]) -> bool:
    """
    Check if a deadline is still valid (not passed).
    
    Args:
        deadline_dt: Deadline datetime object
        
    Returns:
        True if deadline is valid (not passed), False otherwise
    """
    if not deadline_dt:
        # Keep if unknown; downstream logic can decide
        return True
    
    now = datetime.now(CENTRAL)
    
    # Treat same-day deadlines as valid until 11:59pm local time
    return deadline_dt.date() >= now.date()


def setup_logging(level: str = "INFO") -> None:
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('grant_finder.log')
        ]
    )


def display_opportunities(opportunities: List[Opportunity], title: str = "Opportunities") -> None:
    """Display opportunities in a rich table."""
    if not opportunities:
        console.print(f"[yellow]No {title.lower()} found[/yellow]")
        return
    
    table = Table(title=title)
    table.add_column("Score", justify="center", style="cyan")
    table.add_column("Program", style="green")
    table.add_column("Agency", style="blue")
    table.add_column("Deadline", justify="center")
    table.add_column("Award", style="yellow")
    table.add_column("Source", justify="center")
    
    for opp in opportunities:
        deadline = opp.deadline.isoformat() if opp.deadline else "N/A"
        award = opp.estimated_award or "N/A"
        
        table.add_row(
            str(opp.total_score),
            opp.program_name[:50] + "..." if len(opp.program_name) > 50 else opp.program_name,
            opp.agency,
            deadline,
            award,
            opp.source.value
        )
    
    console.print(table)


def display_changes(changes: List[ChangeEvent], title: str = "Changes Detected") -> None:
    """Display change events in a rich table."""
    if not changes:
        console.print(f"[yellow]No {title.lower()} found[/yellow]")
        return
    
    table = Table(title=title)
    table.add_column("Type", justify="center", style="cyan")
    table.add_column("ID", style="green")
    table.add_column("Program", style="blue")
    table.add_column("Changes", style="yellow")
    table.add_column("Score", justify="center")
    
    for change in changes:
        opportunity = change.opportunity
        changes_text = ", ".join(change.what_changed) if change.what_changed else "N/A"
        
        table.add_row(
            change.change_type.value,
            opportunity.opportunity_id,
            opportunity.program_name[:40] + "..." if len(opportunity.program_name) > 40 else opportunity.program_name,
            changes_text,
            str(opportunity.total_score)
        )
    
    console.print(table)


def display_pipeline_result(result: PipelineResult) -> None:
    """Display pipeline result summary."""
    # Create summary panel
    summary_text = f"""
    [bold]Pipeline Summary[/bold]
    
    [green]✓[/green] Fetched: {result.total_fetched} opportunities
    [green]✓[/green] Filtered: {result.total_filtered} opportunities  
    [green]✓[/green] Scored: {result.total_scored} opportunities
    [green]✓[/green] Changes: {len(result.changes_detected)} detected
    [green]✓[/green] Alerts: {result.alerts_sent} sent
    [green]✓[/green] Runtime: {result.runtime_seconds:.1f}s
    """
    
    if result.errors:
        summary_text += f"\n[red]✗[/red] Errors: {len(result.errors)}"
        for error in result.errors:
            summary_text += f"\n  - {error}"
    
    panel = Panel(summary_text, title="Pipeline Complete", border_style="green")
    console.print(panel)


def display_progress(description: str = "Processing..."):
    """Context manager for displaying progress."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    )


def parse_time_range(time_str: str) -> Optional[timedelta]:
    """
    Parse a time range string (e.g., "14d", "2w", "1m").
    
    Args:
        time_str: Time string like "14d", "2w", "1m"
        
    Returns:
        Timedelta object or None if invalid
    """
    if not time_str:
        return None
    
    try:
        value = int(time_str[:-1])
        unit = time_str[-1].lower()
        
        if unit == 'd':
            return timedelta(days=value)
        elif unit == 'w':
            return timedelta(weeks=value)
        elif unit == 'm':
            return timedelta(days=value * 30)  # Approximate
        elif unit == 'y':
            return timedelta(days=value * 365)  # Approximate
        else:
            logger.warning(f"Unknown time unit: {unit}")
            return None
            
    except (ValueError, IndexError):
        logger.warning(f"Invalid time format: {time_str}")
        return None


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def get_top_opportunities_by_category(opportunities: List[Opportunity], limit: int = 5) -> dict:
    """Get top opportunities by different categories."""
    categories = {
        "highest_score": sorted(opportunities, key=lambda x: x.total_score, reverse=True)[:limit],
        "deadline_soon": sorted(
            [opp for opp in opportunities if opp.deadline and opp.get_days_to_deadline() and opp.get_days_to_deadline() > 0],
            key=lambda x: x.get_days_to_deadline()
        )[:limit],
        "highest_award": sorted(
            [opp for opp in opportunities if opp.estimated_award],
            key=lambda x: _extract_award_value(x.estimated_award),
            reverse=True
        )[:limit],
        "for_profit": [opp for opp in opportunities if opp.is_for_profit_eligible][:limit]
    }
    
    return categories


def _extract_award_value(award_text: str) -> float:
    """Extract numeric value from award text for sorting."""
    import re
    
    if not award_text:
        return 0.0
    
    # Extract numbers
    numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', award_text)
    if not numbers:
        return 0.0
    
    # Take the highest number
    max_value = max(float(num.replace(',', '')) for num in numbers)
    
    # Apply multipliers
    if 'k' in award_text.lower() or 'thousand' in award_text.lower():
        max_value *= 1000
    elif 'm' in award_text.lower() or 'million' in award_text.lower():
        max_value *= 1000000
    
    return max_value


def validate_configuration() -> bool:
    """Validate the configuration is complete."""
    from .config import config
    
    errors = []
    
    # Check required files
    import os
    if not os.path.exists(config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH):
        errors.append(f"Google service account JSON not found: {config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH}")
    
    # Check required settings
    if not config.GOOGLE_SHEET_NAME:
        errors.append("GOOGLE_SHEET_NAME not configured")
    
    if not config.GOOGLE_SHEET_TAB:
        errors.append("GOOGLE_SHEET_TAB not configured")
    
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for error in errors:
            console.print(f"  [red]•[/red] {error}")
        return False
    
    return True


def print_banner() -> None:
    """Print the application banner."""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                    Dental AI Grant Finder                    ║
    ║              SBIR/Grants.gov Opportunity Tracker             ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue") 