"""LLM-powered summaries for opportunities (optional feature)."""

import logging
from typing import Optional

from ..models import Opportunity
from ..config import config

logger = logging.getLogger(__name__)


def generate_llm_summary(opportunity: Opportunity) -> str:
    """
    Generate an AI-powered summary of why an opportunity fits.
    
    Falls back to rule-based summary if OpenAI API key is not available.
    
    Args:
        opportunity: The opportunity to summarize
        
    Returns:
        One-line explanation of why it fits
    """
    if not config.OPENAI_API_KEY:
        return opportunity.get_why_it_fits()
    
    try:
        return _call_openai_api(opportunity)
    except Exception as e:
        logger.warning(f"LLM summary failed, falling back to rule-based: {e}")
        return opportunity.get_why_it_fits()


def _call_openai_api(opportunity: Opportunity) -> str:
    """
    Call OpenAI API to generate summary.
    
    This is a stub implementation. In a real implementation, you would:
    1. Import openai
    2. Set up the API client
    3. Make a completion request
    4. Parse and return the response
    """
    # Stub implementation - replace with actual OpenAI API call
    prompt = f"""
    Explain in one sentence why this grant opportunity is relevant for a dental AI company:
    
    Title: {opportunity.program_name}
    Agency: {opportunity.agency}
    Summary: {opportunity.summary[:200]}...
    For-profit eligible: {opportunity.is_for_profit_eligible}
    Score: {opportunity.total_score}/100
    """
    
    # Placeholder response - replace with actual API call
    return f"AI-generated summary for {opportunity.opportunity_id} (OpenAI API not configured)"


def is_llm_available() -> bool:
    """Check if LLM features are available."""
    return bool(config.OPENAI_API_KEY) 