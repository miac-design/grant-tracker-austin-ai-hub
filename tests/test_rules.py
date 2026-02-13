"""Unit tests for ranking rules."""

import pytest
from datetime import date, timedelta

from src.models import Opportunity, Source
from src.ranking.rules import (
    score_opportunity, calculate_fit_score, 
    calculate_deadline_score, calculate_award_score
)


class TestRankingRules:
    """Test cases for ranking rules."""
    
    def test_calculate_fit_score_dental_keywords(self):
        """Test fit score calculation with dental keywords."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Dental AI Innovation Grant",
            agency="NIH",
            opportunity_id="TEST001",
            url="https://example.com",
            summary="This grant focuses on dental health and AI technology",
            eligibility="For-profit eligible",
            is_for_profit_eligible=True,
            hash_signature="test_hash"
        )
        
        score = calculate_fit_score(opp)
        # Should get +20 for dental, +15 for AI, +10 for NIH, +5 for for-profit, +10 for SBIR-like
        expected_min = 60  # 20 + 15 + 10 + 5 + 10
        assert score >= expected_min
    
    def test_calculate_fit_score_scheduling_keywords(self):
        """Test fit score calculation with scheduling keywords."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Patient Appointment Scheduling System",
            agency="HHS",
            opportunity_id="TEST002",
            url="https://example.com",
            summary="Innovative appointment scheduling and no-show prevention",
            eligibility="Small business eligible",
            is_for_profit_eligible=True,
            hash_signature="test_hash"
        )
        
        score = calculate_fit_score(opp)
        # Should get +10 for scheduling, +10 for HHS, +5 for for-profit
        expected_min = 25
        assert score >= expected_min
    
    def test_calculate_fit_score_ai_keywords(self):
        """Test fit score calculation with AI keywords."""
        opp = Opportunity(
            source=Source.SBIR_GOV,
            program_name="Artificial Intelligence for Healthcare",
            agency="NSF",
            opportunity_id="TEST003",
            url="https://example.com",
            summary="Machine learning and natural language processing for healthcare",
            eligibility="SBIR Phase I",
            is_for_profit_eligible=True,
            hash_signature="test_hash"
        )
        
        score = calculate_fit_score(opp)
        # Should get +15 for AI, +10 for NSF, +5 for for-profit, +10 for SBIR
        expected_min = 40
        assert score >= expected_min
    
    def test_calculate_deadline_score_passed(self):
        """Test deadline score for passed deadline."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Test Grant",
            agency="Test Agency",
            opportunity_id="TEST004",
            url="https://example.com",
            summary="Test summary",
            eligibility="Test eligibility",
            deadline=date.today() - timedelta(days=1),  # Yesterday
            hash_signature="test_hash"
        )
        
        score = calculate_deadline_score(opp)
        assert score == 0
    
    def test_calculate_deadline_score_soon(self):
        """Test deadline score for deadline soon."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Test Grant",
            agency="Test Agency",
            opportunity_id="TEST005",
            url="https://example.com",
            summary="Test summary",
            eligibility="Test eligibility",
            deadline=date.today() + timedelta(days=3),  # 3 days from now
            hash_signature="test_hash"
        )
        
        score = calculate_deadline_score(opp)
        assert score == 100
    
    def test_calculate_deadline_score_medium(self):
        """Test deadline score for medium-term deadline."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Test Grant",
            agency="Test Agency",
            opportunity_id="TEST006",
            url="https://example.com",
            summary="Test summary",
            eligibility="Test eligibility",
            deadline=date.today() + timedelta(days=45),  # 45 days from now
            hash_signature="test_hash"
        )
        
        score = calculate_deadline_score(opp)
        assert score == 60
    
    def test_calculate_deadline_score_far(self):
        """Test deadline score for far deadline."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Test Grant",
            agency="Test Agency",
            opportunity_id="TEST007",
            url="https://example.com",
            summary="Test summary",
            eligibility="Test eligibility",
            deadline=date.today() + timedelta(days=200),  # 200 days from now
            hash_signature="test_hash"
        )
        
        score = calculate_deadline_score(opp)
        assert score == 10
    
    def test_calculate_award_score_phase_i(self):
        """Test award score for Phase I SBIR."""
        opp = Opportunity(
            source=Source.SBIR_GOV,
            program_name="SBIR Phase I",
            agency="NIH",
            opportunity_id="TEST008",
            url="https://example.com",
            summary="Phase I SBIR grant",
            eligibility="SBIR Phase I",
            estimated_award="$150,000",
            hash_signature="test_hash"
        )
        
        score = calculate_award_score(opp)
        assert score == 60
    
    def test_calculate_award_score_phase_ii(self):
        """Test award score for Phase II SBIR."""
        opp = Opportunity(
            source=Source.SBIR_GOV,
            program_name="SBIR Phase II",
            agency="NIH",
            opportunity_id="TEST009",
            url="https://example.com",
            summary="Phase II SBIR grant",
            eligibility="SBIR Phase II",
            estimated_award="$1,000,000",
            hash_signature="test_hash"
        )
        
        score = calculate_award_score(opp)
        assert score == 90
    
    def test_calculate_award_score_large(self):
        """Test award score for large award."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Large Grant",
            agency="NIH",
            opportunity_id="TEST010",
            url="https://example.com",
            summary="Large grant opportunity",
            eligibility="For-profit eligible",
            estimated_award="$5,000,000",
            hash_signature="test_hash"
        )
        
        score = calculate_award_score(opp)
        assert score == 100
    
    def test_calculate_award_score_unknown(self):
        """Test award score for unknown award amount."""
        opp = Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Unknown Award",
            agency="Test Agency",
            opportunity_id="TEST011",
            url="https://example.com",
            summary="Test summary",
            eligibility="Test eligibility",
            estimated_award=None,
            hash_signature="test_hash"
        )
        
        score = calculate_award_score(opp)
        assert score == 40
    
    def test_score_opportunity_complete(self):
        """Test complete opportunity scoring."""
        opp = Opportunity(
            source=Source.SBIR_GOV,
            program_name="Dental AI SBIR Phase I",
            agency="NIH",
            opportunity_id="TEST012",
            url="https://example.com",
            summary="Dental AI innovation with appointment scheduling",
            eligibility="SBIR Phase I",
            is_for_profit_eligible=True,
            deadline=date.today() + timedelta(days=30),
            estimated_award="$150,000",
            hash_signature="test_hash"
        )
        
        scored_opp = score_opportunity(opp)
        
        # Check that all scores are calculated
        assert scored_opp.fit_score > 0
        assert scored_opp.deadline_score > 0
        assert scored_opp.award_score > 0
        assert scored_opp.total_score > 0
        
        # Check that total score is weighted sum
        expected_total = int(0.5 * scored_opp.fit_score + 0.3 * scored_opp.deadline_score + 0.2 * scored_opp.award_score)
        assert scored_opp.total_score == expected_total
    
    def test_score_opportunity_scores_capped(self):
        """Test that individual scores are capped at 100."""
        opp = Opportunity(
            source=Source.SBIR_GOV,
            program_name="Perfect Match Grant",
            agency="NIH",
            opportunity_id="TEST013",
            url="https://example.com",
            summary="Dental AI with all keywords and perfect match",
            eligibility="SBIR Phase I",
            is_for_profit_eligible=True,
            deadline=date.today() + timedelta(days=1),
            estimated_award="$5,000,000",
            hash_signature="test_hash"
        )
        
        scored_opp = score_opportunity(opp)
        
        # All scores should be capped at 100
        assert scored_opp.fit_score <= 100
        assert scored_opp.deadline_score <= 100
        assert scored_opp.award_score <= 100
        assert scored_opp.total_score <= 100 