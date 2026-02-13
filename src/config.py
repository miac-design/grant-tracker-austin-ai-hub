"""Configuration management for the dental AI grant finder."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration."""
    
    # Required settings
    GOOGLE_SERVICE_ACCOUNT_JSON_PATH: str = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_JSON_PATH", "./creds/service_account.json"
    )
    GOOGLE_SHEET_NAME: str = os.getenv("GOOGLE_SHEET_NAME", "Dental AI Grants")
    GOOGLE_SHEET_TAB: str = os.getenv("GOOGLE_SHEET_TAB", "SBIR_Tracker")
    
    # Optional APIs
    GRANTSGOV_API_KEY: Optional[str] = os.getenv("GRANTSGOV_API_KEY")
    SBIR_API_BASE: str = os.getenv(
        "SBIR_API_BASE", "https://www.sbir.gov/api/solicitations.json"
    )
    
    # Notifications
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL")
    SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS")
    EMAIL_FROM: Optional[str] = os.getenv("EMAIL_FROM")
    EMAIL_TO: Optional[str] = os.getenv("EMAIL_TO")
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Chicago")
    
    # Scheduling
    ALERT_WINDOW_DAYS: int = int(os.getenv("ALERT_WINDOW_DAYS", "45"))
    
    # Optional LLM
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        required_paths = [
            ("Google Service Account JSON", cls.GOOGLE_SERVICE_ACCOUNT_JSON_PATH)
        ]
        
        for name, path in required_paths:
            if not Path(path).exists():
                raise FileNotFoundError(
                    f"{name} not found at {path}. "
                    "Please check your .env configuration."
                )
    
    @classmethod
    def get_notification_config(cls) -> dict:
        """Get notification configuration."""
        return {
            "slack_webhook": cls.SLACK_WEBHOOK_URL,
            "email": {
                "host": cls.SMTP_HOST,
                "port": cls.SMTP_PORT,
                "user": cls.SMTP_USER,
                "password": cls.SMTP_PASS,
                "from_email": cls.EMAIL_FROM,
                "to_email": cls.EMAIL_TO,
            } if cls.SMTP_HOST else None,
            "timezone": cls.TIMEZONE,
            "alert_window_days": cls.ALERT_WINDOW_DAYS,
        }


# Global config instance
config = Config() 