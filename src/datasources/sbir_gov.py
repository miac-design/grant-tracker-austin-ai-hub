"""SBIR.gov data source for fetching opportunities."""

import hashlib
import json
import logging
from datetime import date
from typing import List, Optional

import requests
import dateparser

from ..models import Opportunity, Source
from ..keywords import contains_exclusion_keywords
from ..utils import parse_date, is_deadline_valid, CENTRAL

logger = logging.getLogger(__name__)


def fetch_sbir(api_base: str, keywords: List[str], days: int = 180, 
               only_open: bool = True, query: Optional[str] = None) -> List[Opportunity]:
    """
    Fetch opportunities from SBIR.gov API.
    
    Args:
        api_base: Base URL for SBIR.gov API
        keywords: List of keywords to search for
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
    
    try:
        # Make API request
        logger.info(f"Fetching from SBIR.gov: {api_base}")
        
        response = requests.get(api_base, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if not isinstance(data, list):
            logger.warning("SBIR.gov response is not a list")
            return opportunities
        
        for opp_data in data:
            try:
                opportunity = _parse_sbir_opportunity(opp_data, keywords, only_open, days, query)
                if opportunity:
                    opportunities.append(opportunity)
            except Exception as e:
                logger.error(f"Error parsing SBIR opportunity {opp_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"Fetched {len(opportunities)} opportunities from SBIR.gov")
        
    except requests.RequestException as e:
        logger.error(f"Error fetching from SBIR.gov: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing SBIR.gov response: {e}")
    except Exception as e:
        logger.error(f"Unexpected error fetching from SBIR.gov: {e}")
    
    return opportunities


def _parse_sbir_opportunity(data: dict, keywords: List[str], only_open: bool = True, 
                           days: int = 180, query: Optional[str] = None) -> Optional[Opportunity]:
    """Parse a single SBIR.gov opportunity."""
    
    # Extract basic fields
    opportunity_id = data.get("id", "")
    if not opportunity_id:
        return None
    
    # Check for exclusion keywords
    title = data.get("title", "")
    description = data.get("description", "")
    full_text = f"{title} {description}".lower()
    
    if contains_exclusion_keywords(full_text):
        return None
    
    # Check if any keywords match (skip if specific query provided)
    # If no keywords match but this is a healthcare SBIR, still include it
    if not query and keywords:
        keyword_match = any(keyword.lower() in full_text for keyword in keywords)
        healthcare_match = any(kw in full_text for kw in ["health", "medical", "clinical", "patient", "care"])
        
        if not keyword_match and not healthcare_match:
            return None
    
    # Parse and validate deadline
    deadline = parse_date(data.get("dueDate") or data.get("closeDate") or data.get("endDate"))
    if only_open and not is_deadline_valid(deadline):
        logger.debug(f"Skipping expired SBIR opportunity {opportunity_id}: deadline {deadline}")
        return None
    
    # Check posted date within lookback window
    posted_date = parse_date(data.get("postedDate") or data.get("openDate"))
    if posted_date:
        from datetime import datetime, timedelta
        cutoff_date = datetime.now(CENTRAL) - timedelta(days=days)
        if posted_date < cutoff_date:
            logger.debug(f"Skipping old SBIR opportunity {opportunity_id}: posted {posted_date}")
            return None
    
    # Determine for-profit eligibility (SBIR/STTR are inherently for-profit)
    is_for_profit = True  # SBIR/STTR are for small businesses
    
    # Build opportunity
    opportunity = Opportunity(
        source=Source.SBIR_GOV,
        program_name=title,
        agency=data.get("agency", ""),
        opportunity_id=opportunity_id,
        url=data.get("url", ""),
        summary=description,
        eligibility="SBIR/STTR - Small Business Innovation Research/Small Business Technology Transfer",
        is_for_profit_eligible=is_for_profit,
        topic_tags=_extract_sbir_tags(data),
        deadline=deadline,
        estimated_award=_extract_award_amount(data),
        contact=_extract_sbir_contact(data),
        hash_signature=_generate_sbir_hash_signature(data)
    )
    
    return opportunity


def _extract_sbir_tags(data: dict) -> List[str]:
    """Extract topic tags from SBIR opportunity data."""
    tags = []
    
    # Add phase if available
    if data.get("phase"):
        tags.append(f"Phase {data['phase']}")
    
    # Add agency
    if data.get("agency"):
        tags.append(data["agency"])
    
    # Add program type
    if data.get("program"):
        tags.append(data["program"])
    
    # Add topic area if available
    if data.get("topic"):
        tags.append(data["topic"])
    
    return tags


def _extract_award_amount(data: dict) -> Optional[str]:
    """Extract award amount from SBIR data."""
    if data.get("awardAmount"):
        return str(data["awardAmount"])
    
    # Try to estimate based on phase
    phase = data.get("phase", "").lower()
    if "phase i" in phase:
        return "$50,000 - $300,000"
    elif "phase ii" in phase:
        return "$750,000 - $2,000,000"
    
    return None


def _extract_sbir_contact(data: dict) -> Optional[str]:
    """Extract contact information from SBIR data."""
    contacts = []
    
    if data.get("contactName"):
        contacts.append(data["contactName"])
    
    if data.get("contactEmail"):
        contacts.append(data["contactEmail"])
    
    if data.get("contactPhone"):
        contacts.append(data["contactPhone"])
    
    return "; ".join(contacts) if contacts else None


def _generate_sbir_hash_signature(data: dict) -> str:
    """Generate a deterministic hash signature for SBIR change detection."""
    # Key fields that indicate a change
    key_fields = [
        data.get("id", ""),
        data.get("dueDate", ""),
        data.get("awardAmount", ""),
        data.get("description", "")[:500],  # First 500 chars of description
        data.get("title", ""),
        data.get("phase", ""),
        data.get("agency", "")
    ]
    
    # Create hash
    content = "|".join(str(field) for field in key_fields)
    return hashlib.sha256(content.encode()).hexdigest() 