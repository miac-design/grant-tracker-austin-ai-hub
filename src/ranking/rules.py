"""Scoring rules for ranking opportunities."""

from datetime import date
from typing import List

from ..models import Opportunity
from ..keywords import calculate_keyword_matches, is_preferred_agency


def score_opportunity(opportunity: Opportunity) -> Opportunity:
    """
    Score an opportunity using all scoring rules.
    
    Args:
        opportunity: The opportunity to score
        
    Returns:
        Updated opportunity with scores
    """
    # Calculate individual scores
    fit_score = calculate_fit_score(opportunity)
    deadline_score = calculate_deadline_score(opportunity)
    award_score = calculate_award_score(opportunity)
    
    # Calculate total score (weighted sum)
    total_score = int(0.5 * fit_score + 0.3 * deadline_score + 0.2 * award_score)
    
    # Update opportunity with scores
    opportunity.fit_score = fit_score
    opportunity.deadline_score = deadline_score
    opportunity.award_score = award_score
    opportunity.total_score = total_score
    
    return opportunity


def calculate_fit_score(opportunity: Opportunity) -> int:
    """
    Calculate fit score based on relevance to dental AI.
    
    Scoring rules:
    - +30 if contains "dental/oral"
    - +15 if "appointment/scheduling/no-show/practice management"
    - +15 if "AI/artificial intelligence/automation/machine learning"
    - +10 if agency in preferred list (NIH, NIDCR, HHS, NSF)
    - Cap at 100
    """
    score = 0
    text = f"{opportunity.program_name} {opportunity.summary}".lower()
    
    # Dental/Oral Health keywords (increased weight)
    dental_keywords = ["dental", "oral health", "dentistry", "orthodontics", 
                      "endodontics", "periodontics", "prosthodontics"]
    if any(kw in text for kw in dental_keywords):
        score += 30
    
    # Appointment/Scheduling/Practice Management keywords
    scheduling_keywords = ["appointment", "scheduling", "no-show", "reminder", 
                          "follow-up", "patient portal", "practice management"]
    if any(kw in text for kw in scheduling_keywords):
        score += 15
    
    # AI/Automation keywords
    ai_keywords = ["ai", "artificial intelligence", "automation", "machine learning", 
                  "nlp", "natural language processing", "chatbot", "virtual assistant"]
    if any(kw in text for kw in ai_keywords):
        score += 15
    
    # Preferred agency bonus (NIH, NIDCR, HHS, NSF)
    preferred_agencies = ["nih", "nidcr", "hhs", "nsf"]
    if opportunity.agency.lower() in preferred_agencies:
        score += 10
    
    # For-profit eligibility bonus
    if opportunity.is_for_profit_eligible:
        score += 5
    
    # SBIR/STTR specific bonus
    if "sbir" in text or "sttr" in text or "small business innovation" in text:
        score += 10
    
    # Cap at 100
    return min(score, 100)


def calculate_deadline_score(opportunity: Opportunity) -> int:
    """
    Calculate deadline score based on proximity to deadline.
    
    Scoring:
    - 0 if deadline passed
    - 100 if in 1-7 days
    - 80 if 8-30 days
    - 60 if 31-60 days
    - 30 if 61-120 days
    - 10 if beyond 120 days
    """
    if not opportunity.deadline:
        return 0
    
    days_to_deadline = opportunity.get_days_to_deadline()
    
    if days_to_deadline is None:
        return 0
    
    if days_to_deadline < 0:
        return 0  # Deadline passed
    elif days_to_deadline <= 7:
        return 100
    elif days_to_deadline <= 30:
        return 80
    elif days_to_deadline <= 60:
        return 60
    elif days_to_deadline <= 120:
        return 30
    else:
        return 10


def calculate_award_score(opportunity: Opportunity) -> int:
    """
    Calculate award score based on estimated award amount.
    
    Scoring:
    - Phase I typical: 60
    - Phase II typical: 90
    - Unknown: 40
    """
    if not opportunity.estimated_award:
        return 40
    
    award_text = opportunity.estimated_award.lower()
    
    # Check for Phase I/II indicators first
    if "phase i" in award_text or "phase 1" in award_text:
        return 60
    elif "phase ii" in award_text or "phase 2" in award_text:
        return 90
    
    # Extract numeric values
    import re
    numbers = re.findall(r'\d+(?:,\d+)*(?:\.\d+)?', award_text)
    
    if not numbers:
        return 40
    
    # Convert to numeric values
    try:
        # Take the highest number found
        max_amount = max(float(num.replace(',', '')) for num in numbers)
        
        # Apply multipliers for K/M
        if "k" in award_text or "thousand" in award_text:
            max_amount *= 1000
        elif "m" in award_text or "million" in award_text:
            max_amount *= 1000000
        
        # Score based on amount ranges
        if max_amount >= 750000:  # Phase II range
            return 90
        elif max_amount >= 50000:  # Phase I range
            return 60
        else:
            return 40
            
    except (ValueError, TypeError):
        return 40


def get_scoring_weights() -> dict:
    """Get the current scoring weights."""
    return {
        "fit": 0.5,
        "deadline": 0.3,
        "award": 0.2
    }


def update_scoring_weights(fit: float = 0.5, deadline: float = 0.3, award: float = 0.2) -> None:
    """
    Update scoring weights (for future use).
    
    Args:
        fit: Weight for fit score (0-1)
        deadline: Weight for deadline score (0-1)
        award: Weight for award score (0-1)
    """
    # Validate weights sum to 1
    total = fit + deadline + award
    if abs(total - 1.0) > 0.01:
        raise ValueError(f"Weights must sum to 1.0, got {total}")
    
    # In a real implementation, this would update a configuration
    # For now, we'll just validate
    pass 