"""Grants.gov data source for fetching opportunities."""

import hashlib
import json
import logging
from datetime import date, datetime
from typing import List, Optional
from urllib.parse import urlencode

import requests
import dateparser

from ..models import Opportunity, Source
from ..keywords import get_all_positive_keywords, contains_exclusion_keywords
from ..utils import parse_date, is_deadline_valid, CENTRAL

logger = logging.getLogger(__name__)


def fetch_grants_gov(keywords: List[str], api_key: Optional[str] = None, 
                    days: int = 180, only_open: bool = True, 
                    query: Optional[str] = None) -> List[Opportunity]:
    """
    Fetch opportunities from Grants.gov API.
    
    Args:
        keywords: List of keywords to search for
        api_key: Optional API key for Grants.gov
        days: Lookback window in days for posted date
        only_open: Exclude past-deadline items if True
        query: Optional specific query string
        
    Returns:
        List of Opportunity objects
    """
    opportunities = []
    
    # Use broader keyword set if no specific query provided
    if not query and not keywords:
        keywords = [
            "dental", "oral health", "appointment", "scheduling", "AI", 
            "artificial intelligence", "machine learning", "automation", 
            "practice management", "telehealth", "call", "voice", 
            "SBIR", "STTR", "healthcare"
        ]
    
    # Grants.gov API endpoint
    base_url = "https://www.grants.gov/api/opportunities"
    
    # Search parameters
    search_params = {
        "keyword": query if query else " OR ".join(keywords),
        "eligibility": "Small Business",  # Focus on for-profit eligibility
        "fundingInstrumentType": "Grant,Cooperative Agreement",
        "sortBy": "openDate",
        "sortOrder": "desc",
        "rows": 100,  # Max results per request
        "startRecordNum": 0
    }
    
    if api_key:
        search_params["apiKey"] = api_key
    
    try:
        # Make API request
        url = f"{base_url}?{urlencode(search_params)}"
        logger.info(f"Fetching from Grants.gov: {url}")
        
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if "opportunities" not in data:
            logger.warning("No opportunities found in Grants.gov response")
            return opportunities
        
        for opp_data in data["opportunities"]:
            try:
                opportunity = _parse_grants_gov_opportunity(opp_data, only_open, days)
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                logger.error(f"Error parsing opportunity {opp_data.get('opportunityId', 'unknown')}: {e}")
                continue
        
        logger.info(f"Fetched {len(opportunities)} opportunities from Grants.gov")
        
    except requests.RequestException as e:
        logger.error(f"Error fetching from Grants.gov: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing Grants.gov response: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching from Grants.gov: {e}")
    
    return opportunities


def _parse_grants_gov_opportunity(data: dict, only_open: bool = True, days: int = 180) -> Optional[Opportunity]:
    """Parse a single Grants.gov opportunity."""
    
    # Extract basic fields
    opportunity_id = data.get("opportunityId", "")
    if not opportunity_id:
        return None
    
    # Check for exclusion keywords
    summary = data.get("synopsis", "")
    title = data.get("title", "")
    full_text = f"{title} {summary}".lower()
    
    if contains_exclusion_keywords(full_text):
        return None
    
    # Parse and validate deadline
    deadline = parse_date(data.get("closeDate") or data.get("responseDate"))
    if only_open and not is_deadline_valid(deadline):
        logger.debug(f"Skipping expired opportunity {opportunity_id}: deadline {deadline}")
        return None
    
    # Check posted date within lookback window
    posted_date = parse_date(data.get("openDate") or data.get("postedDate"))
    if posted_date:
        from datetime import datetime, timedelta
        cutoff_date = datetime.now(CENTRAL) - timedelta(days=days)
        if posted_date < cutoff_date:
            logger.debug(f"Skipping old opportunity {opportunity_id}: posted {posted_date}")
            return None
    
    # Determine for-profit eligibility
    eligibility_text = data.get("eligibilityInfo", "")
    is_for_profit = _check_for_profit_eligibility(eligibility_text)
    
    # Build opportunity
    opportunity = Opportunity(
        source=Source.GRANTS_GOV,
        program_name=data.get("title", ""),
        agency=data.get("agencyName", ""),
        opportunity_id=opportunity_id,
        url=f"https://www.grants.gov/web/grants/view-opportunity.html?oppId={opportunity_id}",
        summary=summary,
        eligibility=eligibility_text,
        is_for_profit_eligible=is_for_profit,
        topic_tags=_extract_topic_tags(data),
        deadline=deadline,
        estimated_award=data.get("awardCeiling"),
        contact=_extract_contact_info(data),
        hash_signature=_generate_hash_signature(data)
    )
    
    return opportunity


def _check_for_profit_eligibility(eligibility_text: str) -> bool:
    """Check if opportunity is for-profit eligible."""
    if not eligibility_text:
        return False
    
    text_lower = eligibility_text.lower()
    
    # Positive indicators
    for_profit_indicators = [
        "small business",
        "for-profit",
        "commercial",
        "private sector",
        "sbir",
        "sttr",
        "small business innovation research",
        "small business technology transfer"
    ]
    
    # Negative indicators
    nonprofit_only_indicators = [
        "nonprofit only",
        "educational institution only",
        "university only",
        "college only",
        "government only",
        "federal only",
        "state only",
        "local only"
    ]
    
    # Check for negative indicators first
    for indicator in nonprofit_only_indicators:
        if indicator in text_lower:
            return False
    
    # Check for positive indicators
    for indicator in for_profit_indicators:
        if indicator in text_lower:
            return True
    
    return False


def _extract_topic_tags(data: dict) -> List[str]:
    """Extract topic tags from opportunity data."""
    tags = []
    
    # Add category if available
    if data.get("categoryOfFundingActivity"):
        tags.append(data["categoryOfFundingActivity"])
    
    # Add funding instrument type
    if data.get("fundingInstrumentType"):
        tags.append(data["fundingInstrumentType"])
    
    # Add agency
    if data.get("agencyName"):
        tags.append(data["agencyName"])
    
    return tags


def _extract_contact_info(data: dict) -> Optional[str]:
    """Extract contact information."""
    contacts = []
    
    if data.get("contactName"):
        contacts.append(data["contactName"])
    
    if data.get("contactEmail"):
        contacts.append(data["contactEmail"])
    
    if data.get("contactPhone"):
        contacts.append(data["contactPhone"])
    
    return "; ".join(contacts) if contacts else None


def _generate_hash_signature(data: dict) -> str:
    """Generate a deterministic hash signature for change detection."""
    # Key fields that indicate a change
    key_fields = [
        data.get("opportunityId", ""),
        data.get("closeDate", ""),
        data.get("awardCeiling", ""),
        data.get("synopsis", "")[:500],  # First 500 chars of summary
        data.get("title", "")
    ]
    
    # Create hash
    content = "|".join(str(field) for field in key_fields)
    return hashlib.sha256(content.encode()).hexdigest() 