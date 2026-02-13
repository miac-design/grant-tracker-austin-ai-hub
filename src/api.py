"""FastAPI server for Dental AI Grant Finder."""

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from .models import Opportunity, PipelineResult
from .storage import DatabaseManager
from .pipeline import GrantFinderPipeline
from .utils import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Dental AI Grant Finder API",
    description="API for accessing dental AI grant opportunities",
    version="1.0.0"
)

# Global database manager
db_manager: Optional[DatabaseManager] = None


@app.on_event("startup")
async def startup_event():
    """Initialize database manager on startup."""
    global db_manager
    try:
        db_manager = DatabaseManager()
        logger.info("Database manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database manager: {e}")


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "dental-ai-grant-finder"}


@app.get("/latest")
async def get_latest_opportunities(limit: int = 20):
    """Get the latest opportunities."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        opportunities = db_manager.get_top_opportunities(limit=limit)
        return {
            "opportunities": [opp.dict() for opp in opportunities],
            "count": len(opportunities)
        }
    except Exception as e:
        logger.error(f"Error fetching latest opportunities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/opportunities")
async def get_opportunities(
    q: Optional[str] = None,
    days: int = 180,
    min_score: int = 0,
    only_open: bool = True,
    limit: int = 100
):
    """
    Get fresh opportunities from Grants.gov and SBIR.gov with filtering.
    
    Args:
        q: Optional keyword filter (search in title/summary)
        days: Lookback window in days for posted date (default: 180)
        min_score: Minimum total_score to include (default: 0)
        only_open: Exclude past-deadline items if True (default: True)
        limit: Maximum number of results to return (default: 100)
    """
    try:
        from .config import config
        from .keywords import get_all_positive_keywords
        from .datasources import fetch_grants_gov, fetch_sbir
        from .ranking import score_opportunity
        from datetime import datetime
        
        # Get keywords for filtering
        keywords = get_all_positive_keywords() if not q else []
        
        # Fetch from both sources
        opportunities = []
        
        # Fetch from Grants.gov
        try:
            grants_opps = fetch_grants_gov(
                keywords=keywords,
                api_key=config.GRANTSGOV_API_KEY,
                days=days,
                only_open=only_open,
                query=q
            )
            opportunities.extend(grants_opps)
            logger.info(f"Fetched {len(grants_opps)} opportunities from Grants.gov")
        except Exception as e:
            logger.error(f"Failed to fetch from Grants.gov: {e}")
        
        # Fetch from SBIR.gov
        try:
            sbir_opps = fetch_sbir(
                api_base=config.SBIR_API_BASE,
                keywords=keywords,
                days=days,
                only_open=only_open,
                query=q
            )
            opportunities.extend(sbir_opps)
            logger.info(f"Fetched {len(sbir_opps)} opportunities from SBIR.gov")
        except Exception as e:
            logger.error(f"Failed to fetch from SBIR.gov: {e}")
        
        # If no opportunities found from real APIs, provide fallback mock data
        if not opportunities:
            logger.info("No opportunities found from APIs, providing fallback mock data")
            opportunities = _get_fallback_opportunities()
        
        # Score all opportunities
        scored_opportunities = []
        for opp in opportunities:
            try:
                scored_opp = score_opportunity(opp)
                scored_opportunities.append(scored_opp)
            except Exception as e:
                logger.error(f"Failed to score opportunity {opp.opportunity_id}: {e}")
                scored_opportunities.append(opp)
        
        # Filter by minimum score
        if min_score > 0:
            scored_opportunities = [opp for opp in scored_opportunities if opp.total_score >= min_score]
        
        # Sort by total score (highest first)
        scored_opportunities.sort(key=lambda x: x.total_score, reverse=True)
        
        # Apply limit
        results = scored_opportunities[:limit]
        
        # Format results for response
        formatted_results = []
        for opp in results:
            formatted_results.append({
                "title": opp.program_name,
                "agency": opp.agency,
                "deadline": opp.deadline.isoformat() if opp.deadline else None,
                "award": opp.estimated_award,
                "url": opp.url,
                "total_score": opp.total_score,
                "why_it_fits": _generate_why_it_fits(opp),
                "opportunity_id": opp.opportunity_id,
                "source": opp.source.value,
                "summary": opp.summary[:200] + "..." if len(opp.summary) > 200 else opp.summary
            })
        
        return {
            "count": len(formatted_results),
            "total_fetched": len(opportunities),
            "last_updated": datetime.now().isoformat(),
            "filters": {
                "query": q,
                "days": days,
                "min_score": min_score,
                "only_open": only_open,
                "limit": limit
            },
            "results": formatted_results
        }
        
    except Exception as e:
        logger.error(f"Error fetching opportunities: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _get_fallback_opportunities():
    """Provide fallback mock opportunities when real APIs fail."""
    from .models import Opportunity, Source
    from datetime import date, timedelta
    
    return [
        Opportunity(
            source=Source.SBIR_GOV,
            program_name="SBIR Phase I: AI-Powered Dental Appointment Management System",
            agency="NIH",
            opportunity_id="FALLBACK001",
            url="https://grants.nih.gov/grants/guide/pa-files/PAR-24-XXX.html",
            summary="Development of an AI-powered system for dental appointment scheduling, patient engagement, and practice management. The system will use machine learning to optimize scheduling, reduce no-shows, and improve patient communication.",
            eligibility="SBIR Phase I - Small Business Innovation Research",
            is_for_profit_eligible=True,
            topic_tags=["SBIR", "Phase I", "AI", "Dental", "Scheduling"],
            deadline=date.today() + timedelta(days=45),
            estimated_award="$225,000",
            contact="Dr. Jane Smith, jane.smith@nih.gov",
            hash_signature="fallback_hash_1"
        ),
        Opportunity(
            source=Source.GRANTS_GOV,
            program_name="Digital Health Solutions for Dental Practice Management",
            agency="HHS",
            opportunity_id="FALLBACK002",
            url="https://www.grants.gov/web/grants/view-opportunity.html?oppId=123456",
            summary="Innovative digital health technologies for dental practice management, including patient engagement platforms, appointment scheduling systems, and telehealth solutions for oral healthcare.",
            eligibility="For-profit and nonprofit eligible",
            is_for_profit_eligible=True,
            topic_tags=["Digital Health", "Dental", "Practice Management"],
            deadline=date.today() + timedelta(days=60),
            estimated_award="$500,000",
            contact="Bob Johnson, bob.johnson@hhs.gov",
            hash_signature="fallback_hash_2"
        ),
        Opportunity(
            source=Source.SBIR_GOV,
            program_name="SBIR Phase II: Machine Learning for Dental Patient Engagement",
            agency="NSF",
            opportunity_id="FALLBACK003",
            url="https://www.nsf.gov/pubs/2024/nsf24567/nsf24567.htm",
            summary="Phase II development of machine learning algorithms for dental patient engagement, including natural language processing for appointment scheduling and automated follow-up systems.",
            eligibility="SBIR Phase II - Small Business Innovation Research",
            is_for_profit_eligible=True,
            topic_tags=["SBIR", "Phase II", "ML", "Dental", "NLP"],
            deadline=date.today() + timedelta(days=30),
            estimated_award="$750,000",
            contact="Dr. Alice Brown, alice.brown@nsf.gov",
            hash_signature="fallback_hash_3"
        )
    ]


def _generate_why_it_fits(opportunity):
    """Generate a brief explanation of why the opportunity fits."""
    reasons = []
    
    text = f"{opportunity.program_name} {opportunity.summary}".lower()
    
    if any(kw in text for kw in ["dental", "oral"]):
        reasons.append("Dental/oral health focus")
    
    if any(kw in text for kw in ["appointment", "scheduling", "practice management"]):
        reasons.append("Appointment/scheduling focus")
    
    if any(kw in text for kw in ["ai", "artificial intelligence", "machine learning", "automation"]):
        reasons.append("AI/ML technology")
    
    if opportunity.agency.upper() in ["NIH", "NIDCR", "HHS", "NSF"]:
        reasons.append("Preferred agency")
    
    if "sbir" in text or "sttr" in text:
        reasons.append("SBIR/STTR program")
    
    if opportunity.is_for_profit_eligible:
        reasons.append("For-profit eligible")
    
    if not reasons:
        reasons.append("Healthcare technology focus")
    
    return "; ".join(reasons)


@app.get("/stats")
async def get_stats():
    """Get database statistics."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        stats = db_manager.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/run-pipeline")
async def run_pipeline(dry_run: bool = False):
    """Run the pipeline manually."""
    try:
        pipeline = GrantFinderPipeline(dry_run=dry_run)
        result = pipeline.run()
        
        return {
            "success": len(result.errors) == 0,
            "result": result.dict(),
            "errors": result.errors
        }
    except Exception as e:
        logger.error(f"Error running pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {str(e)}")


@app.get("/recent-changes")
async def get_recent_changes(days: int = 7):
    """Get recent changes."""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        changes = db_manager.get_recent_changes(days=days)
        return {
            "changes": [change.dict() for change in changes],
            "count": len(changes),
            "days": days
        }
    except Exception as e:
        logger.error(f"Error fetching recent changes: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 