"""Unit tests for change detection and diff functionality."""

import pytest
from datetime import date, datetime
from unittest.mock import Mock, patch

from src.models import Opportunity, ChangeEvent, ChangeType, Source
from src.diff import detect_changes, filter_alerts, should_alert_for_opportunity, get_alert_summary


class TestChangeDetection:
    """Test cases for change detection."""
    
    def test_detect_changes_new_opportunity(self):
        """Test detecting a new opportunity."""
        # Mock database manager
        mock_db = Mock()
        mock_db.upsert_opportunities.return_value = [
            ChangeEvent(
                change_type=ChangeType.ADDED,
                opportunity_id="TEST001",
                source=Source.GRANTS_GOV,
                what_changed=["new opportunity"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.GRANTS_GOV,
                    program_name="Test Grant",
                    agency="Test Agency",
                    opportunity_id="TEST001",
                    url="https://example.com",
                    summary="Test summary",
                    eligibility="Test eligibility",
                    hash_signature="test_hash"
                )
            )
        ]
        
        opportunities = [
            Opportunity(
                source=Source.GRANTS_GOV,
                program_name="Test Grant",
                agency="Test Agency",
                opportunity_id="TEST001",
                url="https://example.com",
                summary="Test summary",
                eligibility="Test eligibility",
                hash_signature="test_hash"
            )
        ]
        
        changes = detect_changes(opportunities, mock_db)
        
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.ADDED
        assert changes[0].opportunity_id == "TEST001"
        mock_db.upsert_opportunities.assert_called_once_with(opportunities)
    
    def test_detect_changes_updated_opportunity(self):
        """Test detecting an updated opportunity."""
        mock_db = Mock()
        mock_db.upsert_opportunities.return_value = [
            ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id="TEST002",
                source=Source.SBIR_GOV,
                what_changed=["deadline", "total_score"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.SBIR_GOV,
                    program_name="Updated Grant",
                    agency="Test Agency",
                    opportunity_id="TEST002",
                    url="https://example.com",
                    summary="Updated summary",
                    eligibility="Test eligibility",
                    deadline=date.today() + date.resolution,
                    hash_signature="updated_hash"
                )
            )
        ]
        
        opportunities = [
            Opportunity(
                source=Source.SBIR_GOV,
                program_name="Updated Grant",
                agency="Test Agency",
                opportunity_id="TEST002",
                url="https://example.com",
                summary="Updated summary",
                eligibility="Test eligibility",
                deadline=date.today() + date.resolution,
                hash_signature="updated_hash"
            )
        ]
        
        changes = detect_changes(opportunities, mock_db)
        
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.UPDATED
        assert changes[0].what_changed == ["deadline", "total_score"]
    
    def test_detect_changes_no_changes(self):
        """Test when no changes are detected."""
        mock_db = Mock()
        mock_db.upsert_opportunities.return_value = []
        
        opportunities = [
            Opportunity(
                source=Source.GRANTS_GOV,
                program_name="Existing Grant",
                agency="Test Agency",
                opportunity_id="TEST003",
                url="https://example.com",
                summary="Existing summary",
                eligibility="Test eligibility",
                hash_signature="existing_hash"
            )
        ]
        
        changes = detect_changes(opportunities, mock_db)
        
        assert len(changes) == 0


class TestAlertFiltering:
    """Test cases for alert filtering."""
    
    def test_filter_alerts_added_opportunity(self):
        """Test filtering alerts for added opportunities."""
        changes = [
            ChangeEvent(
                change_type=ChangeType.ADDED,
                opportunity_id="TEST001",
                source=Source.GRANTS_GOV,
                what_changed=["new opportunity"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.GRANTS_GOV,
                    program_name="New Grant",
                    agency="Test Agency",
                    opportunity_id="TEST001",
                    url="https://example.com",
                    summary="New summary",
                    eligibility="Test eligibility",
                    total_score=50,
                    hash_signature="new_hash"
                )
            )
        ]
        
        alerts = filter_alerts(changes)
        
        assert len(alerts) == 1
        assert alerts[0].change_type == ChangeType.ADDED
    
    def test_filter_alerts_updated_important_changes(self):
        """Test filtering alerts for updates with important changes."""
        changes = [
            ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id="TEST002",
                source=Source.SBIR_GOV,
                what_changed=["deadline", "estimated_award"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.SBIR_GOV,
                    program_name="Updated Grant",
                    agency="Test Agency",
                    opportunity_id="TEST002",
                    url="https://example.com",
                    summary="Updated summary",
                    eligibility="Test eligibility",
                    total_score=40,
                    hash_signature="updated_hash"
                )
            )
        ]
        
        alerts = filter_alerts(changes)
        
        assert len(alerts) == 1
        assert alerts[0].change_type == ChangeType.UPDATED
    
    def test_filter_alerts_high_score_deadline_soon(self):
        """Test filtering alerts for high-scoring opportunities with soon deadlines."""
        changes = [
            ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id="TEST003",
                source=Source.GRANTS_GOV,
                what_changed=["total_score"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.GRANTS_GOV,
                    program_name="High Score Grant",
                    agency="Test Agency",
                    opportunity_id="TEST003",
                    url="https://example.com",
                    summary="High score summary",
                    eligibility="Test eligibility",
                    total_score=80,
                    deadline=date.today() + date.resolution * 30,  # 30 days from now
                    hash_signature="high_score_hash"
                )
            )
        ]
        
        alerts = filter_alerts(changes, alert_window_days=45)
        
        assert len(alerts) == 1
        assert alerts[0].opportunity.total_score >= 60
    
    def test_filter_alerts_low_score_no_deadline(self):
        """Test filtering alerts for low-scoring opportunities without deadline."""
        changes = [
            ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id="TEST004",
                source=Source.GRANTS_GOV,
                what_changed=["summary"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.GRANTS_GOV,
                    program_name="Low Score Grant",
                    agency="Test Agency",
                    opportunity_id="TEST004",
                    url="https://example.com",
                    summary="Low score summary",
                    eligibility="Test eligibility",
                    total_score=30,
                    hash_signature="low_score_hash"
                )
            )
        ]
        
        alerts = filter_alerts(changes)
        
        # Should not alert for low score with no important changes
        assert len(alerts) == 0
    
    def test_filter_alerts_mixed_changes(self):
        """Test filtering alerts for mixed types of changes."""
        changes = [
            # Added opportunity (should alert)
            ChangeEvent(
                change_type=ChangeType.ADDED,
                opportunity_id="TEST005",
                source=Source.GRANTS_GOV,
                what_changed=["new opportunity"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.GRANTS_GOV,
                    program_name="New Grant",
                    agency="Test Agency",
                    opportunity_id="TEST005",
                    url="https://example.com",
                    summary="New summary",
                    eligibility="Test eligibility",
                    total_score=45,
                    hash_signature="new_hash"
                )
            ),
            # Updated with important changes (should alert)
            ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id="TEST006",
                source=Source.SBIR_GOV,
                what_changed=["deadline"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.SBIR_GOV,
                    program_name="Updated Grant",
                    agency="Test Agency",
                    opportunity_id="TEST006",
                    url="https://example.com",
                    summary="Updated summary",
                    eligibility="Test eligibility",
                    total_score=35,
                    hash_signature="updated_hash"
                )
            ),
            # Updated with minor changes (should not alert)
            ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id="TEST007",
                source=Source.GRANTS_GOV,
                what_changed=["summary"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.GRANTS_GOV,
                    program_name="Minor Update Grant",
                    agency="Test Agency",
                    opportunity_id="TEST007",
                    url="https://example.com",
                    summary="Minor update summary",
                    eligibility="Test eligibility",
                    total_score=25,
                    hash_signature="minor_hash"
                )
            )
        ]
        
        alerts = filter_alerts(changes)
        
        # Should only alert for added and important updates
        assert len(alerts) == 2
        alert_ids = {alert.opportunity_id for alert in alerts}
        assert "TEST005" in alert_ids
        assert "TEST006" in alert_ids
        assert "TEST007" not in alert_ids


class TestAlertCriteria:
    """Test cases for alert criteria functions."""
    
    def test_should_alert_for_opportunity_high_score_deadline_soon(self):
        """Test alert criteria for high score with deadline soon."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="High Score Grant",
            agency="Test Agency",
            opportunity_id="TEST008",
            url="https://example.com",
            summary="High score summary",
            eligibility="Test eligibility",
            total_score=75,
            deadline=date.today() + date.resolution * 20,  # 20 days from now
            hash_signature="test_hash"
        )
        
        should_alert = should_alert_for_opportunity(opp, alert_window_days=45)
        assert should_alert is True
    
    def test_should_alert_for_opportunity_for_profit_good_fit(self):
        """Test alert criteria for for-profit with good fit."""
        opp = Opportunity(
            source=Source.SBIR_GOV,
            program_name="For-Profit Grant",
            agency="Test Agency",
            opportunity_id="TEST009",
            url="https://example.com",
            summary="For-profit summary",
            eligibility="For-profit eligible",
            is_for_profit_eligible=True,
            fit_score=75,
            total_score=45,
            hash_signature="test_hash"
        )
        
        should_alert = should_alert_for_opportunity(opp)
        assert should_alert is True
    
    def test_should_alert_for_opportunity_low_score(self):
        """Test alert criteria for low score opportunity."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Low Score Grant",
            agency="Test Agency",
            opportunity_id="TEST010",
            url="https://example.com",
            summary="Low score summary",
            eligibility="Test eligibility",
            total_score=30,
            fit_score=25,
            hash_signature="test_hash"
        )
        
        should_alert = should_alert_for_opportunity(opp)
        assert should_alert is False
    
    def test_get_alert_summary(self):
        """Test getting alert summary."""
        changes = [
            ChangeEvent(
                change_type=ChangeType.ADDED,
                opportunity_id="TEST011",
                source=Source.GRANTS_GOV,
                what_changed=["new opportunity"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.GRANTS_GOV,
                    program_name="Added Grant",
                    agency="Test Agency",
                    opportunity_id="TEST011",
                    url="https://example.com",
                    summary="Added summary",
                    eligibility="Test eligibility",
                    is_for_profit_eligible=True,
                    total_score=70,
                    deadline=date.today() + date.resolution * 10,
                    hash_signature="added_hash"
                )
            ),
            ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id="TEST012",
                source=Source.SBIR_GOV,
                what_changed=["deadline"],
                url="https://example.com",
                opportunity=Opportunity(
                    source=Source.SBIR_GOV,
                    program_name="Updated Grant",
                    agency="Test Agency",
                    opportunity_id="TEST012",
                    url="https://example.com",
                    summary="Updated summary",
                    eligibility="Test eligibility",
                    is_for_profit_eligible=False,
                    total_score=45,
                    hash_signature="updated_hash"
                )
            )
        ]
        
        summary = get_alert_summary(changes)
        
        assert summary["total_changes"] == 2
        assert summary["added"] == 1
        assert summary["updated"] == 1
        assert summary["high_score"] == 1  # Only the added one has score >= 60
        assert summary["deadline_soon"] == 1  # Only the added one has deadline soon
        assert summary["for_profit"] == 1  # Only the added one is for-profit 