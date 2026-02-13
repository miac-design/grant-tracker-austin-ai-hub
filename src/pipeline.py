"""Main pipeline orchestrator for the dental AI grant finder."""

import argparse
import logging
import time
from datetime import datetime
from typing import List, Optional

from rich.console import Console

from .config import config
from .keywords import get_all_positive_keywords
from .models import Opportunity, PipelineResult
from .datasources import fetch_grants_gov, fetch_sbir
from .ranking import score_opportunity
from .storage import DatabaseManager, GoogleSheetsManager
from .notify import SlackNotifier, EmailNotifier
from .diff import detect_changes, filter_alerts
from .utils import (
    setup_logging, display_opportunities, display_changes, 
    display_pipeline_result, display_progress, print_banner,
    validate_configuration, parse_time_range, is_deadline_valid
)

console = Console()
logger = logging.getLogger(__name__)


class GrantFinderPipeline:
    """Main pipeline for finding and tracking grant opportunities."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.db_manager = None
        self.sheets_manager = None
        self.slack_notifier = None
        self.email_notifier = None
        
        if not dry_run:
            self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all pipeline components."""
        try:
            self.db_manager = DatabaseManager()
            self.sheets_manager = GoogleSheetsManager()
            self.slack_notifier = SlackNotifier()
            self.email_notifier = EmailNotifier()
            
            logger.info("Pipeline components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize pipeline components: {e}")
            raise
    
    def run(self, since: Optional[str] = None) -> PipelineResult:
        """
        Run the complete pipeline.
        
        Args:
            since: Optional time range to check for recent changes (e.g., "14d")
            
        Returns:
            PipelineResult with execution summary
        """
        start_time = time.time()
        result = PipelineResult()
        
        try:
            print_banner()
            
            # Validate configuration
            if not validate_configuration():
                result.errors.append("Configuration validation failed")
                return result
            
            # Step 1: Fetch opportunities
            with display_progress("Fetching opportunities from data sources..."):
                opportunities = self._fetch_opportunities()
                result.total_fetched = len(opportunities)
            
            if not opportunities:
                logger.warning("No opportunities fetched")
                return result
            
            # Step 1.5: Pipeline guardrail - filter out expired deadlines
            with display_progress("Filtering out expired deadlines..."):
                valid_opportunities = [op for op in opportunities if is_deadline_valid(op.deadline)]
                expired_count = len(opportunities) - len(valid_opportunities)
                if expired_count > 0:
                    logger.info(f"Filtered out {expired_count} opportunities with expired deadlines")
                opportunities = valid_opportunities
            
            # Step 2: Filter for for-profit eligibility
            with display_progress("Filtering for for-profit eligibility..."):
                filtered_opportunities = self._filter_opportunities(opportunities)
                result.total_filtered = len(filtered_opportunities)
            
            # Step 3: Score opportunities
            with display_progress("Scoring opportunities..."):
                scored_opportunities = self._score_opportunities(filtered_opportunities)
                result.total_scored = len(scored_opportunities)
            
            # Step 4: Detect changes (if not dry run)
            if not self.dry_run:
                with display_progress("Detecting changes..."):
                    changes = detect_changes(scored_opportunities, self.db_manager)
                    result.changes_detected = changes
                
                # Step 5: Filter alerts with deadline window check
                with display_progress("Filtering alerts..."):
                    alerts = self._filter_alerts_with_deadline_window(changes)
                
                # Step 6: Send notifications
                if alerts:
                    with display_progress("Sending notifications..."):
                        alerts_sent = self._send_notifications(alerts)
                        result.alerts_sent = alerts_sent
                
                # Step 7: Update Google Sheets
                with display_progress("Updating Google Sheets..."):
                    self._update_sheets(scored_opportunities)
            
            # Display results
            self._display_results(scored_opportunities, result)
            
        except Exception as e:
            error_msg = f"Pipeline execution failed: {e}"
            logger.error(error_msg)
            result.errors.append(error_msg)
        
        finally:
            result.runtime_seconds = time.time() - start_time
        
        return result
    
    def _fetch_opportunities(self) -> List[Opportunity]:
        """Fetch opportunities from all data sources."""
        opportunities = []
        keywords = get_all_positive_keywords()
        
        # Fetch from Grants.gov
        try:
            grants_gov_opps = fetch_grants_gov(
                keywords=keywords, 
                api_key=config.GRANTSGOV_API_KEY,
                days=180,
                only_open=True
            )
            opportunities.extend(grants_gov_opps)
            logger.info(f"Fetched {len(grants_gov_opps)} opportunities from Grants.gov")
        except Exception as e:
            logger.error(f"Failed to fetch from Grants.gov: {e}")
        
        # Fetch from SBIR.gov
        try:
            sbir_opps = fetch_sbir(
                api_base=config.SBIR_API_BASE, 
                keywords=keywords,
                days=180,
                only_open=True
            )
            opportunities.extend(sbir_opps)
            logger.info(f"Fetched {len(sbir_opps)} opportunities from SBIR.gov")
        except Exception as e:
            logger.error(f"Failed to fetch from SBIR.gov: {e}")
        
        return opportunities
    
    def _filter_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
        """Filter opportunities for for-profit eligibility."""
        filtered = []
        
        for opp in opportunities:
            # Check for-profit eligibility
            if opp.is_for_profit_eligible:
                filtered.append(opp)
            # Also include SBIR/STTR opportunities (they're inherently for-profit)
            elif "sbir" in opp.program_name.lower() or "sttr" in opp.program_name.lower():
                opp.is_for_profit_eligible = True
                filtered.append(opp)
        
        logger.info(f"Filtered {len(opportunities)} opportunities to {len(filtered)} for-profit eligible")
        return filtered
    
    def _score_opportunities(self, opportunities: List[Opportunity]) -> List[Opportunity]:
        """Score all opportunities."""
        scored = []
        
        for opp in opportunities:
            try:
                scored_opp = score_opportunity(opp)
                scored.append(scored_opp)
            except Exception as e:
                logger.error(f"Failed to score opportunity {opp.opportunity_id}: {e}")
                # Add with default scores
                scored.append(opp)
        
        # Sort by total score
        scored.sort(key=lambda x: x.total_score, reverse=True)
        
        logger.info(f"Scored {len(scored)} opportunities")
        return scored
    
    def _send_notifications(self, alerts: List[Opportunity]) -> int:
        """Send notifications for alerts."""
        alerts_sent = 0
        
        # Send Slack notifications
        if self.slack_notifier and self.slack_notifier.enabled:
            try:
                slack_sent = self.slack_notifier.send_bulk_alert(alerts)
                alerts_sent += slack_sent
            except Exception as e:
                logger.error(f"Failed to send Slack notifications: {e}")
        
        # Send email notifications
        if self.email_notifier and self.email_notifier.enabled:
            try:
                email_sent = self.email_notifier.send_bulk_alert(alerts)
                alerts_sent += email_sent
            except Exception as e:
                logger.error(f"Failed to send email notifications: {e}")
        
        logger.info(f"Sent {alerts_sent} notifications")
        return alerts_sent
    
    def _update_sheets(self, opportunities: List[Opportunity]) -> None:
        """Update Google Sheets with opportunities."""
        if not self.sheets_manager:
            return
        
        try:
            # Get top 200 opportunities by score
            top_opportunities = opportunities[:200]
            success = self.sheets_manager.write_opportunities(top_opportunities)
            
            if success:
                logger.info(f"Updated Google Sheets with {len(top_opportunities)} opportunities")
            else:
                logger.error("Failed to update Google Sheets")
                
        except Exception as e:
            logger.error(f"Failed to update Google Sheets: {e}")
    
    def _display_results(self, opportunities: List[Opportunity], result: PipelineResult) -> None:
        """Display pipeline results."""
        # Display top opportunities
        top_opportunities = opportunities[:10]
        display_opportunities(top_opportunities, "Top 10 Opportunities")
        
        # Display changes if any
        if result.changes_detected:
            display_changes(result.changes_detected)
        
        # Display pipeline result
        display_pipeline_result(result)
        
        # Show Google Sheets URL if available
        if self.sheets_manager and not self.dry_run:
            sheet_url = self.sheets_manager.get_sheet_url()
            if sheet_url:
                console.print(f"\n[green]Google Sheet:[/green] {sheet_url}")

    def _filter_alerts_with_deadline_window(self, changes: List) -> List:
        """Filter alerts to only include opportunities within the alert window."""
        from .diff import filter_alerts
        from datetime import datetime
        
        # First apply standard alert filtering
        alerts = filter_alerts(changes)
        
        # Then filter by deadline window
        now = datetime.now()
        window_alerts = []
        
        for alert in alerts:
            if self._within_alert_window(alert):
                window_alerts.append(alert)
            else:
                logger.debug(f"Alert filtered out - outside alert window: {alert.opportunity_id}")
        
        logger.info(f"Filtered {len(alerts)} alerts to {len(window_alerts)} within alert window")
        return window_alerts
    
    def _within_alert_window(self, opportunity: Opportunity) -> bool:
        """Check if opportunity is within the alert window."""
        if not opportunity.deadline:
            return True  # Keep if unknown; you can choose False if you prefer strict
        
        now = datetime.now()
        delta = (opportunity.deadline.date() - now.date()).days
        return 0 <= delta <= config.ALERT_WINDOW_DAYS


def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(description="Dental AI Grant Finder Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--since", type=str, help="Check for changes since (e.g., '14d', '2w')")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Run pipeline
    pipeline = GrantFinderPipeline(dry_run=args.dry_run)
    result = pipeline.run(since=args.since)
    
    # Exit with error code if there were errors
    if result.errors:
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 