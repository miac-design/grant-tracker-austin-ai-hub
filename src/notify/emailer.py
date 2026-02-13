"""Email notification module."""

import logging
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional

from jinja2 import Template

from ..models import ChangeEvent, Opportunity
from ..config import config

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handles email notifications for grant opportunities."""
    
    def __init__(self, email_config: Optional[dict] = None):
        self.config = email_config or config.get_notification_config().get("email")
        self.enabled = bool(self.config and self.config.get("host"))
    
    def send_alert(self, change_event: ChangeEvent) -> bool:
        """
        Send an email alert for a change event.
        
        Args:
            change_event: The change event to alert about
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("Email notifications disabled")
            return False
        
        try:
            subject, body = self._build_email(change_event)
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
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
            logger.debug("Email notifications disabled")
            return 0
        
        if not change_events:
            return 0
        
        try:
            subject, body = self._build_bulk_email(change_events)
            if self._send_email(subject, body):
                return len(change_events)
            return 0
            
        except Exception as e:
            logger.error(f"Failed to send bulk email alert: {e}")
            return 0
    
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
            subject = f"Dental AI Grant Finder - Daily Summary ({datetime.now().strftime('%Y-%m-%d')})"
            body = self._build_summary_email(opportunities, changes_count)
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send email summary: {e}")
            return False
    
    def _build_email(self, change_event: ChangeEvent) -> tuple[str, str]:
        """Build email subject and body for a change event."""
        opportunity = change_event.opportunity
        
        # Subject
        subject = f"Grant Alert: {change_event.change_type.value} - {opportunity.program_name[:50]}"
        
        # Body template
        template = Template("""
        <html>
        <body>
            <h2>🔔 Grant Opportunity {{ change_type }}</h2>
            
            <h3>{{ opportunity.program_name }}</h3>
            <p><strong>Agency:</strong> {{ opportunity.agency }}</p>
            <p><strong>Score:</strong> {{ opportunity.total_score }}/100</p>
            
            {% if opportunity.deadline %}
            <p><strong>Deadline:</strong> {{ opportunity.deadline.isoformat() }}
            {% set days = opportunity.get_days_to_deadline() %}
            {% if days is not none %}
                ({{ days }} days left)
            {% endif %}
            </p>
            {% endif %}
            
            {% if opportunity.estimated_award %}
            <p><strong>Award:</strong> {{ opportunity.estimated_award }}</p>
            {% endif %}
            
            <p><strong>Summary:</strong><br>
            {{ opportunity.summary[:300] }}{% if opportunity.summary|length > 300 %}...{% endif %}
            </p>
            
            {% if change_event.what_changed %}
            <p><strong>Changes:</strong> {{ change_event.what_changed|join(', ') }}</p>
            {% endif %}
            
            <p><strong>Why it fits:</strong> {{ opportunity.get_why_it_fits() }}</p>
            
            <p><a href="{{ opportunity.url }}">View Full Details</a></p>
            
            <hr>
            <p><small>Sent by Dental AI Grant Finder on {{ detected_at.strftime('%Y-%m-%d %H:%M') }}</small></p>
        </body>
        </html>
        """)
        
        body = template.render(
            change_type=change_event.change_type.value,
            opportunity=opportunity,
            change_event=change_event,
            detected_at=change_event.detected_at
        )
        
        return subject, body
    
    def _build_bulk_email(self, change_events: List[ChangeEvent]) -> tuple[str, str]:
        """Build email for multiple change events."""
        subject = f"Grant Alerts: {len(change_events)} New/Updated Opportunities"
        
        template = Template("""
        <html>
        <body>
            <h2>🔔 Grant Opportunities Update</h2>
            <p>{{ change_events|length }} opportunities have been added or updated.</p>
            
            {% for event in change_events %}
            <hr>
            <h3>{{ event.change_type.value }}: {{ event.opportunity.program_name }}</h3>
            <p><strong>Agency:</strong> {{ event.opportunity.agency }}</p>
            <p><strong>Score:</strong> {{ event.opportunity.total_score }}/100</p>
            
            {% if event.opportunity.deadline %}
            <p><strong>Deadline:</strong> {{ event.opportunity.deadline.isoformat() }}</p>
            {% endif %}
            
            {% if event.opportunity.estimated_award %}
            <p><strong>Award:</strong> {{ event.opportunity.estimated_award }}</p>
            {% endif %}
            
            <p><a href="{{ event.opportunity.url }}">View Details</a></p>
            {% endfor %}
            
            <hr>
            <p><small>Sent by Dental AI Grant Finder on {{ datetime.now().strftime('%Y-%m-%d %H:%M') }}</small></p>
        </body>
        </html>
        """)
        
        body = template.render(change_events=change_events)
        
        return subject, body
    
    def _build_summary_email(self, opportunities: List[Opportunity], changes_count: int) -> str:
        """Build summary email."""
        top_opportunities = sorted(opportunities, key=lambda x: x.total_score, reverse=True)[:10]
        
        template = Template("""
        <html>
        <body>
            <h2>📊 Dental AI Grant Finder - Daily Summary</h2>
            
            <h3>Statistics</h3>
            <ul>
                <li>Total opportunities tracked: {{ opportunities|length }}</li>
                <li>Changes detected today: {{ changes_count }}</li>
                <li>Top opportunities by score: {{ top_opportunities|length }}</li>
            </ul>
            
            <h3>Top Opportunities</h3>
            {% for opp in top_opportunities %}
            <div style="margin-bottom: 20px; padding: 10px; border: 1px solid #ddd;">
                <h4>{{ loop.index }}. {{ opp.program_name }}</h4>
                <p><strong>Agency:</strong> {{ opp.agency }}</p>
                <p><strong>Score:</strong> {{ opp.total_score }}/100</p>
                {% if opp.deadline %}
                <p><strong>Deadline:</strong> {{ opp.deadline.isoformat() }}</p>
                {% endif %}
                {% if opp.estimated_award %}
                <p><strong>Award:</strong> {{ opp.estimated_award }}</p>
                {% endif %}
                <p><a href="{{ opp.url }}">View Details</a></p>
            </div>
            {% endfor %}
            
            <hr>
            <p><small>Generated by Dental AI Grant Finder on {{ datetime.now().strftime('%Y-%m-%d %H:%M') }}</small></p>
        </body>
        </html>
        """)
        
        return template.render(
            opportunities=opportunities,
            changes_count=changes_count,
            top_opportunities=top_opportunities
        )
    
    def _send_email(self, subject: str, body: str) -> bool:
        """Send an email."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.config['from_email']
            msg['To'] = self.config['to_email']
            
            # Add HTML body
            html_part = MIMEText(body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.config['host'], self.config['port']) as server:
                if self.config.get('user') and self.config.get('password'):
                    server.starttls()
                    server.login(self.config['user'], self.config['password'])
                
                server.send_message(msg)
            
            logger.debug("Email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test the email connection."""
        if not self.enabled:
            return False
        
        try:
            test_subject = "🧪 Test Email from Dental AI Grant Finder"
            test_body = "<p>This is a test email to verify the email configuration.</p>"
            return self._send_email(test_subject, test_body)
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False 