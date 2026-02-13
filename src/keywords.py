"""Keywords and filters for dental AI grant opportunities."""

from typing import List, Set

# Positive keywords that indicate relevance to dental AI
POSITIVE_KEYWORDS: List[str] = [
    "dental",
    "oral health", 
    "dentistry",
    "appointment",
    "scheduling",
    "no-show",
    "patient engagement",
    "practice management",
    "telehealth",
    "call",
    "voice",
    "AI",
    "artificial intelligence",
    "automation",
    "machine learning",
    "natural language processing",
    "NLP",
    "chatbot",
    "virtual assistant",
    "patient communication",
    "reminder system",
    "follow-up",
    "patient portal",
    "electronic health record",
    "EHR",
    "clinical decision support",
    "diagnostic",
    "treatment planning",
    "orthodontics",
    "endodontics",
    "periodontics",
    "prosthodontics",
    "oral surgery",
    "dental imaging",
    "radiology",
    "cavity detection",
    "gum disease",
    "oral cancer",
    "dental hygiene",
    "preventive care"
]

# Keywords that indicate exclusion (not relevant)
EXCLUSION_KEYWORDS: List[str] = [
    "veterinary",
    "pure academic only",
    "nonprofit only",
    "educational institution only",
    "university only",
    "college only",
    "government only",
    "federal only",
    "state only",
    "local only",
    "international only",
    "foreign only",
    "overseas only",
    "animal",
    "livestock",
    "agriculture",
    "farming",
    "crop",
    "plant",
    "botanical",
    "marine",
    "ocean",
    "aquatic",
    "fishery",
    "forestry",
    "wildlife",
    "conservation",
    "environmental",
    "climate",
    "energy",
    "transportation",
    "infrastructure",
    "construction",
    "manufacturing",
    "defense",
    "military",
    "weapons",
    "aerospace",
    "space",
    "satellite"
]

# Preferred agencies (higher scoring)
PREFERRED_AGENCIES: Set[str] = {
    "NIH",
    "NIDCR", 
    "NIDDK",
    "NCI",
    "NHLBI",
    "NIA",
    "NIAID",
    "NICHD",
    "NIDA",
    "NIEHS",
    "NIGMS",
    "NIMH",
    "NINDS",
    "NLM",
    "HHS",
    "NSF",
    "DOE",
    "DOD",
    "DARPA",
    "SBIR",
    "STTR"
}

# SBIR/STTR specific keywords
SBIR_KEYWORDS: List[str] = [
    "SBIR",
    "STTR", 
    "Small Business Innovation Research",
    "Small Business Technology Transfer",
    "Phase I",
    "Phase II",
    "Phase III",
    "small business",
    "for-profit",
    "commercialization",
    "technology transfer",
    "innovation"
]


def get_all_positive_keywords() -> List[str]:
    """Get all positive keywords including SBIR keywords."""
    return POSITIVE_KEYWORDS + SBIR_KEYWORDS


def get_keyword_groups() -> dict:
    """Get keywords organized by category."""
    return {
        "dental": ["dental", "oral health", "dentistry", "orthodontics", 
                  "endodontics", "periodontics", "prosthodontics", 
                  "oral surgery", "dental imaging", "radiology", 
                  "cavity detection", "gum disease", "oral cancer", 
                  "dental hygiene", "preventive care"],
        "scheduling": ["appointment", "scheduling", "no-show", 
                      "reminder system", "follow-up", "patient portal"],
        "ai_tech": ["AI", "artificial intelligence", "automation", 
                   "machine learning", "natural language processing", 
                   "NLP", "chatbot", "virtual assistant", 
                   "clinical decision support", "diagnostic"],
        "engagement": ["patient engagement", "patient communication", 
                      "practice management", "telehealth", "call", "voice"],
        "sbir": SBIR_KEYWORDS
    }


def is_preferred_agency(agency: str) -> bool:
    """Check if agency is in preferred list."""
    if not agency:
        return False
    return any(pref.lower() in agency.lower() for pref in PREFERRED_AGENCIES)


def contains_exclusion_keywords(text: str) -> bool:
    """Check if text contains exclusion keywords."""
    if not text:
        return False
    text_lower = text.lower()
    return any(excl.lower() in text_lower for excl in EXCLUSION_KEYWORDS)


def calculate_keyword_matches(text: str) -> dict:
    """Calculate keyword matches by category."""
    if not text:
        return {}
    
    text_lower = text.lower()
    groups = get_keyword_groups()
    matches = {}
    
    for category, keywords in groups.items():
        category_matches = [
            kw for kw in keywords 
            if kw.lower() in text_lower
        ]
        if category_matches:
            matches[category] = category_matches
    
    return matches 