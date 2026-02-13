"""Change detection and alert filtering logic."""

import logging
from typing import List

from .models import ChangeEvent, Opportunity
from .config import config

logger = logging.getLogger(__name__)


def detect_changes(new_items: List[Opportunity], db_manager) -> List[ChangeEvent]:
    """
    Detect changes in opportunities using the database manager.
    
    Args:
        new_items: List of new opportunities
        db_manager: Database manager instance
        
    Returns:
        List of change events detected
    """
    return db_manager.upsert_opportunities(new_items)


def filter_alerts(changes: List[ChangeEvent], alert_window_days: int = None) -> List[ChangeEvent]:
    """
    Filter changes to determine which should trigger alerts.
    
    Alert criteria:
    - ADDED items, OR
    - UPDATED items where deadline or award changed, OR
    - Items with total_score >= 60 AND deadline within alert_window_days
    
    Args:
        changes: List of change events
        alert_window_days: Days ahead to alert for deadlines (default from config)
        
    Returns:
        List of change events that should trigger alerts
    """
    if alert_window_days is None:
        alert_window_days = config.ALERT_WINDOW_DAYS
    
    alerts = []
    
    for change in changes:
        opportunity = change.opportunity
        
        # Always alert for new opportunities
        if change.change_type.value == "ADDED":
            alerts.append(change)
            continue
        
        # Alert for updates with important changes
        if change.change_type.value == "UPDATED":
            important_changes = ["deadline", "estimated_award", "total_score"]
            if any(change_type in change.what_changed for change_type in important_changes):
                alerts.append(change)
                continue
        
        # Alert for high-scoring opportunities within deadline window
        if (opportunity.total_score >= 60 and 
            opportunity.is_deadline_soon(alert_window_days)):
            alerts.append(change)
            continue
    
    logger.info(f"Filtered {len(changes)} changes to {len(alerts)} alerts")
    return alerts


def should_alert_for_opportunity(opportunity: Opportunity, alert_window_days: int = None) -> bool:
    """
    Check if an opportunity should trigger an alert.
    
    Args:
        opportunity: The opportunity to check
        alert_window_days: Days ahead to alert for deadlines
        
    Returns:
        True if should alert, False otherwise
    """
    if alert_window_days is None:
        alert_window_days = config.ALERT_WINDOW_DAYS
    
    # High score and deadline soon
    if opportunity.total_score >= 60 and opportunity.is_deadline_soon(alert_window_days):
        return True
    
    # For-profit eligible and good fit
    if opportunity.is_for_profit_eligible and opportunity.fit_score >= 70:
        return True
    
    return False


def get_alert_summary(changes: List[ChangeEvent]) -> dict:
    """
    Get a summary of changes for alerting.
    
    Args:
        changes: List of change events
        
    Returns:
        Summary dictionary
    """
    summary = {
        "total_changes": len(changes),
        "added": 0,
        "updated": 0,
        "high_score": 0,
        "deadline_soon": 0,
        "for_profit": 0
    }
    
    for change in changes:
        opportunity = change.opportunity
        
        if change.change_type.value == "ADDED":
            summary["added"] += 1
        else:
            summary["updated"] += 1
        
        if opportunity.total_score >= 60:
            summary["high_score"] += 1
        
        if opportunity.is_deadline_soon():
            summary["deadline_soon"] += 1
        
        if opportunity.is_for_profit_eligible:
            summary["for_profit"] += 1
    
    return summary 