"""Slack notification module."""

import json
import logging
from typing import List, Optional

import requests

from ..models import ChangeEvent, Opportunity
from ..config import config

logger = logging.getLogger(__name__)


class SlackNotifier:
    """Handles Slack notifications for grant opportunities."""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or config.SLACK_WEBHOOK_URL
        self.enabled = bool(self.webhook_url)
    
    def send_alert(self, change_event: ChangeEvent) -> bool:
        """
        Send a Slack alert for a change event.
        
        Args:
            change_event: The change event to alert about
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Slack notifications disabled")
            return False
        
        try:
            message = self._build_message(change_event)
            return self._send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
    
    def send_bulk_alert(self, change_events: List[ChangeEvent]) -> int:
        """
        Send bulk alerts for multiple change events.
        
        Args:
            change_events: List of change events to alert about
            
        Returns:
            Number of alerts sent successfully
        """
        if not self.enabled:
            logger.debug("Slack notifications disabled")
            return 0
        
        sent_count = 0
        
        for event in change_events:
            if self.send_alert(event):
                sent_count += 1
        
        logger.info(f"Sent {sent_count}/{len(change_events)} Slack alerts")
        return sent_count
    
    def send_summary(self, opportunities: List[Opportunity], changes_count: int) -> bool:
        """
        Send a summary of the pipeline run.
        
        Args:
            opportunities: List of opportunities processed
            changes_count: Number of changes detected
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            message = self._build_summary_message(opportunities, changes_count)
            return self._send_message(message)
            
        except Exception as e:
            logger.error(f"Failed to send Slack summary: {e}")
            return False
    
    def _build_message(self, change_event: ChangeEvent) -> dict:
        """Build a Slack message for a change event."""
        opportunity = change_event.opportunity
        
        # Determine color based on change type
        color = "#36a64f" if change_event.change_type.value == "ADDED" else "#ff9500"
        
        # Build fields
        fields = [
            {
                "title": "Program",
                "value": opportunity.program_name[:100] + "..." if len(opportunity.program_name) > 100 else opportunity.program_name,
                "short": True
            },
            {
                "title": "Agency",
                "value": opportunity.agency,
                "short": True
            },
            {
                "title": "Score",
                "value": f"{opportunity.total_score}/100",
                "short": True
            }
        ]
        
        # Add deadline if available
        if opportunity.deadline:
            days_left = opportunity.get_days_to_deadline()
            if days_left is not None:
                deadline_text = f"{opportunity.deadline.isoformat()} ({days_left} days left)"
                fields.append({
                    "title": "Deadline",
                    "value": deadline_text,
                    "short": True
                })
        
        # Add award if available
        if opportunity.estimated_award:
            fields.append({
                "title": "Award",
                "value": opportunity.estimated_award,
                "short": True
            })
        
        # Build attachment
        attachment = {
            "color": color,
            "title": f"{change_event.change_type.value}: {opportunity.opportunity_id}",
            "title_link": opportunity.url,
            "text": opportunity.summary[:200] + "..." if len(opportunity.summary) > 200 else opportunity.summary,
            "fields": fields,
            "footer": "Dental AI Grant Finder",
            "ts": int(change_event.detected_at.timestamp())
        }
        
        # Add what changed for updates
        if change_event.change_type.value == "UPDATED" and change_event.what_changed:
            attachment["text"] = f"*Changed:* {', '.join(change_event.what_changed)}\n\n{attachment['text']}"
        
        return {
            "text": f"🔔 {change_event.get_change_summary()}",
            "attachments": [attachment]
        }
    
    def _build_summary_message(self, opportunities: List[Opportunity], changes_count: int) -> dict:
        """Build a summary message for the pipeline run."""
        # Get top opportunities
        top_opportunities = sorted(opportunities, key=lambda x: x.total_score, reverse=True)[:5]
        
        # Build summary text
        summary_text = f"📊 Pipeline Summary\n"
        summary_text += f"• Total opportunities: {len(opportunities)}\n"
        summary_text += f"• Changes detected: {changes_count}\n"
        summary_text += f"• Top opportunities:\n"
        
        for i, opp in enumerate(top_opportunities, 1):
            summary_text += f"  {i}. {opp.program_name[:50]}... (Score: {opp.total_score})\n"
        
        return {
            "text": summary_text,
            "attachments": []
        }
    
    def _send_message(self, message: dict) -> bool:
        """Send a message to Slack."""
        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                timeout=10
            )
            response.raise_for_status()
            
            logger.debug("Slack message sent successfully")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test the Slack webhook connection."""
        if not self.enabled:
            return False
        
        try:
            test_message = {
                "text": "🧪 Test message from Dental AI Grant Finder"
            }
            return self._send_message(test_message)
            
        except Exception as e:
            logger.error(f"Slack connection test failed: {e}")
            return False 