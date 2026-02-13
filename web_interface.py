#!/usr/bin/env python3
"""
Simple web interface for Dental AI Grant Finder.
Run this script to start a localhost web server.
"""

import uvicorn
import webbrowser
import time
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api import app
from src.utils import print_banner, setup_logging

def create_mock_data():
    """Create some mock data for demonstration."""
    from src.models import Opportunity, Source
    from datetime import datetime, timedelta, date
    
    mock_opportunities = [
        Opportunity(
            source=Source.GRANTS_GOV,
            program_name="AI-Powered Dental Appointment Scheduling System",
            agency="NIH",
            opportunity_id="DEMO001",
            url="https://example.com/demo1",
            summary="Innovative AI system for dental appointment scheduling and patient engagement",
            eligibility="For-profit eligible",
            is_for_profit_eligible=True,
            topic_tags=["AI", "Dental", "Scheduling"],
            deadline=date.today() + timedelta(days=30),
            estimated_award="$500,000",
            contact="Dr. Smith, smith@nih.gov",
            hash_signature="demo_hash_1",
            fit_score=85,
            deadline_score=80,
            award_score=70,
            total_score=80
        ),
        Opportunity(
            source=Source.SBIR_GOV,
            program_name="SBIR Phase I: Dental Patient Engagement Platform",
            agency="NSF",
            opportunity_id="DEMO002",
            url="https://example.com/demo2",
            summary="Machine learning platform for dental patient engagement and appointment management",
            eligibility="SBIR Phase I - Small Business",
            is_for_profit_eligible=True,
            topic_tags=["SBIR", "Phase I", "ML", "Dental"],
            deadline=date.today() + timedelta(days=45),
            estimated_award="$225,000",
            contact="Jane Doe, jane@nsf.gov",
            hash_signature="demo_hash_2",
            fit_score=90,
            deadline_score=60,
            award_score=50,
            total_score=70
        ),
        Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Digital Health Solutions for Oral Care",
            agency="HHS",
            opportunity_id="DEMO003",
            url="https://example.com/demo3",
            summary="Digital health technologies for improving oral care and patient outcomes",
            eligibility="For-profit and nonprofit eligible",
            is_for_profit_eligible=True,
            topic_tags=["Digital Health", "Oral Care", "Patient Outcomes"],
            deadline=date.today() + timedelta(days=60),
            estimated_award="$750,000",
            contact="Bob Johnson, bob@hhs.gov",
            hash_signature="demo_hash_3",
            fit_score=75,
            deadline_score=40,
            award_score=80,
            total_score=65
        )
    ]
    
    return mock_opportunities

def main():
    """Start the web server with mock data."""
    print_banner()
    print("\n🚀 Starting Dental AI Grant Finder Web Interface...")
    
    # Setup logging
    setup_logging("INFO")
    
    # Create mock data and add to app state
    mock_data = create_mock_data()
    app.state.mock_opportunities = mock_data
    
    # Add a simple endpoint to serve mock data
    @app.get("/")
    async def home():
        """Home page with basic info."""
        return {
            "message": "Dental AI Grant Finder API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/healthz",
                "latest_opportunities": "/latest",
                "filtered_opportunities": "/opportunities",
                "mock_data": "/mock",
                "run_pipeline": "/run-pipeline"
            },
            "docs": "/docs"
        }
    
    @app.get("/mock")
    async def get_mock_opportunities():
        """Get mock opportunities for demonstration."""
        return {
            "opportunities": [opp.dict() for opp in mock_data],
            "count": len(mock_data),
            "note": "This is mock data for demonstration purposes"
        }
    
    @app.post("/run-pipeline")
    async def run_pipeline_demo():
        """Run a demo pipeline."""
        return {
            "status": "success",
            "message": "Pipeline would run here (dry-run mode)",
            "mock_opportunities": len(mock_data),
            "note": "In production, this would fetch real data from Grants.gov and SBIR.gov"
        }
    
    # Start the server
    host = "127.0.0.1"
    port = 8000
    
    print(f"\n🌐 Web Interface will be available at:")
    print(f"   📱 Main API: http://{host}:{port}")
    print(f"   📖 API Docs: http://{host}:{port}/docs")
    print(f"   🎯 Mock Data: http://{host}:{port}/mock")
    print(f"   🏠 Home: http://{host}:{port}/")
    
    print(f"\n⏳ Starting server on {host}:{port}...")
    print("   Press Ctrl+C to stop the server")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        try:
            webbrowser.open(f"http://{host}:{port}/docs")
        except:
            pass
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False
    )

if __name__ == "__main__":
    main() 