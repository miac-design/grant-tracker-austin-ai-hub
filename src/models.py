"""Data models for the dental AI grant finder."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Source(str, Enum):
    """Data source for opportunities."""
    GRANTS_GOV = "GRANTS_GOV"
    SBIR_GOV = "SBIR_GOV"


class ChangeType(str, Enum):
    """Type of change detected."""
    ADDED = "ADDED"
    UPDATED = "UPDATED"


class Opportunity(BaseModel):
    """Represents a grant opportunity."""
    
    # Core identification
    source: Source
    program_name: str
    agency: str
    opportunity_id: str = Field(..., description="Official NOFO/Solicitation number")
    url: str
    
    # Content
    summary: str
    eligibility: str
    is_for_profit_eligible: bool = False
    
    # Categorization
    topic_tags: List[str] = Field(default_factory=list)
    
    # Key dates and amounts
    deadline: Optional[date] = None
    estimated_award: Optional[str] = None
    contact: Optional[str] = None
    
    # Metadata
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Scoring (computed)
    fit_score: int = Field(default=0, ge=0, le=100)
    deadline_score: int = Field(default=0, ge=0, le=100)
    award_score: int = Field(default=0, ge=0, le=100)
    total_score: int = Field(default=0, ge=0, le=100)
    
    # Change detection
    hash_signature: str = Field(..., description="Deterministic hash for change detection")
    
    def get_days_to_deadline(self) -> Optional[int]:
        """Get days until deadline (negative if passed)."""
        if not self.deadline:
            return None
        
        today = date.today()
        delta = self.deadline - today
        return delta.days
    
    def is_deadline_soon(self, window_days: int = 45) -> bool:
        """Check if deadline is within the alert window."""
        days = self.get_days_to_deadline()
        return days is not None and 0 <= days <= window_days
    
    def get_top_tags(self, max_tags: int = 3) -> List[str]:
        """Get top topic tags for display."""
        return self.topic_tags[:max_tags] if self.topic_tags else []
    
    def get_why_it_fits(self) -> str:
        """Get a brief explanation of why this opportunity fits."""
        reasons = []
        
        if self.fit_score >= 80:
            reasons.append("Excellent fit for dental AI")
        elif self.fit_score >= 60:
            reasons.append("Good fit for dental AI")
        
        if self.is_for_profit_eligible:
            reasons.append("For-profit eligible")
        
        if self.deadline and self.get_days_to_deadline() and self.get_days_to_deadline() <= 30:
            reasons.append("Deadline soon")
        
        if self.estimated_award:
            reasons.append(f"Award: {self.estimated_award}")
        
        return "; ".join(reasons) if reasons else "General opportunity"


class ChangeEvent(BaseModel):
    """Represents a change detected in an opportunity."""
    
    change_type: ChangeType
    opportunity_id: str
    source: Source
    what_changed: List[str] = Field(default_factory=list)
    url: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Optional: include opportunity data for notifications
    opportunity: Optional[Opportunity] = None
    
    def get_change_summary(self) -> str:
        """Get a human-readable summary of the change."""
        if self.change_type == ChangeType.ADDED:
            return f"New opportunity: {self.opportunity_id}"
        else:
            changes = ", ".join(self.what_changed) if self.what_changed else "details updated"
            return f"Updated opportunity: {self.opportunity_id} ({changes})"


class PipelineResult(BaseModel):
    """Result of running the pipeline."""
    
    total_fetched: int = 0
    total_filtered: int = 0
    total_scored: int = 0
    changes_detected: List[ChangeEvent] = Field(default_factory=list)
    alerts_sent: int = 0
    errors: List[str] = Field(default_factory=list)
    runtime_seconds: float = 0.0
    
    def get_summary(self) -> str:
        """Get a summary of the pipeline run."""
        return (
            f"Pipeline completed in {self.runtime_seconds:.1f}s: "
            f"{self.total_fetched} fetched, {self.total_filtered} filtered, "
            f"{self.total_scored} scored, {len(self.changes_detected)} changes, "
            f"{self.alerts_sent} alerts sent"
        )


class NotificationConfig(BaseModel):
    """Configuration for notifications."""
    
    slack_webhook: Optional[str] = None
    email: Optional[dict] = None
    timezone: str = "America/Chicago"
    alert_window_days: int = 45
    min_score_threshold: int = 60
    
    def has_slack(self) -> bool:
        """Check if Slack notifications are configured."""
        return bool(self.slack_webhook)
    
    def has_email(self) -> bool:
        """Check if email notifications are configured."""
        return bool(self.email and self.email.get("host")) 