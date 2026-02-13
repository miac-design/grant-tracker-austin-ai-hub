#!/usr/bin/env python3
"""
Test script for the new /opportunities endpoint functionality.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models import Opportunity, Source
from src.ranking import score_opportunity
from datetime import date, timedelta

def test_scoring():
    """Test the updated scoring system."""
    print("🧪 Testing Updated Scoring System...")
    
    # Create test opportunities
    test_opps = [
        Opportunity(
            source=Source.GRANTS_GOV,
            program_name="AI-Powered Dental Appointment Scheduling System",
            agency="NIH",
            opportunity_id="TEST001",
            url="https://example.com/test1",
            summary="Innovative AI system for dental appointment scheduling and patient engagement",
            eligibility="For-profit eligible",
            is_for_profit_eligible=True,
            topic_tags=["AI", "Dental", "Scheduling"],
            deadline=date.today() + timedelta(days=30),
            estimated_award="$500,000",
            contact="Dr. Smith, smith@nih.gov",
            hash_signature="test_hash_1"
        ),
        Opportunity(
            source=Source.SBIR_GOV,
            program_name="SBIR Phase I: Dental Patient Engagement Platform",
            agency="NSF",
            opportunity_id="TEST002",
            url="https://example.com/test2",
            summary="Machine learning platform for dental patient engagement and appointment management",
            eligibility="SBIR Phase I - Small Business",
            is_for_profit_eligible=True,
            topic_tags=["SBIR", "Phase I", "ML", "Dental"],
            deadline=date.today() + timedelta(days=45),
            estimated_award="$225,000",
            contact="Jane Doe, jane@nsf.gov",
            hash_signature="test_hash_2"
        ),
        Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Digital Health Solutions for Oral Care",
            agency="HHS",
            opportunity_id="TEST003",
            url="https://example.com/test3",
            summary="Digital health technologies for improving oral care and patient outcomes",
            eligibility="For-profit and nonprofit eligible",
            is_for_profit_eligible=True,
            topic_tags=["Digital Health", "Oral Care", "Patient Outcomes"],
            deadline=date.today() + timedelta(days=60),
            estimated_award="$750,000",
            contact="Bob Johnson, bob@hhs.gov",
            hash_signature="test_hash_3"
        )
    ]
    
    # Score each opportunity
    for i, opp in enumerate(test_opps, 1):
        scored_opp = score_opportunity(opp)
        print(f"\n📋 Opportunity {i}: {scored_opp.program_name[:50]}...")
        print(f"   Agency: {scored_opp.agency}")
        print(f"   Fit Score: {scored_opp.fit_score}")
        print(f"   Deadline Score: {scored_opp.deadline_score}")
        print(f"   Award Score: {scored_opp.award_score}")
        print(f"   Total Score: {scored_opp.total_score}")
        print(f"   Deadline: {scored_opp.deadline}")
        print(f"   Award: {scored_opp.estimated_award}")
    
    # Test filtering
    print(f"\n🔍 Testing Filtering...")
    
    # Filter by minimum score
    high_score_opps = [opp for opp in test_opps if opp.total_score >= 70]
    print(f"   Opportunities with score >= 70: {len(high_score_opps)}")
    
    # Filter by agency
    nih_opps = [opp for opp in test_opps if "NIH" in opp.agency]
    print(f"   NIH opportunities: {len(nih_opps)}")
    
    # Filter by source
    grants_opps = [opp for opp in test_opps if opp.source == Source.GRANTS_GOV]
    print(f"   Grants.gov opportunities: {len(grants_opps)}")
    
    print("\n✅ Scoring and filtering tests completed!")

def test_api_endpoint():
    """Test the API endpoint structure."""
    print("\n🌐 Testing API Endpoint Structure...")
    
    try:
        from src.api import app
        print("   ✅ API app imports successfully")
        
        # Check if the opportunities endpoint exists
        routes = [route.path for route in app.routes]
        if "/opportunities" in routes:
            print("   ✅ /opportunities endpoint exists")
        else:
            print("   ❌ /opportunities endpoint not found")
            
        print(f"   📋 Available routes: {routes}")
        
    except Exception as e:
        print(f"   ❌ API test failed: {e}")

if __name__ == "__main__":
    print("🚀 Testing Dental AI Grant Finder Updates...")
    test_scoring()
    test_api_endpoint()
    print("\n🎉 All tests completed!") 