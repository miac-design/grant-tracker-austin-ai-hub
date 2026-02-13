"""Google Sheets manager for writing opportunities."""

import logging
from typing import List, Optional

import gspread
from google.oauth2.service_account import Credentials

from ..models import Opportunity
from ..config import config

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    """Manages Google Sheets operations for opportunities."""
    
    def __init__(self):
        self.client = None
        self.sheet = None
        self.worksheet = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Google Sheets API."""
        try:
            # Define the scope
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            # Load credentials
            creds = Credentials.from_service_account_file(
                config.GOOGLE_SERVICE_ACCOUNT_JSON_PATH,
                scopes=scope
            )
            
            # Create client
            self.client = gspread.authorize(creds)
            
            # Open or create sheet
            try:
                self.sheet = self.client.open(config.GOOGLE_SHEET_NAME)
            except gspread.SpreadsheetNotFound:
                # Create new sheet
                self.sheet = self.client.create(config.GOOGLE_SHEET_NAME)
                logger.info(f"Created new Google Sheet: {config.GOOGLE_SHEET_NAME}")
            
            # Get or create worksheet
            try:
                self.worksheet = self.sheet.worksheet(config.GOOGLE_SHEET_TAB)
            except gspread.WorksheetNotFound:
                # Create new worksheet
                self.worksheet = self.sheet.add_worksheet(
                    title=config.GOOGLE_SHEET_TAB,
                    rows=1000,
                    cols=20
                )
                logger.info(f"Created new worksheet: {config.GOOGLE_SHEET_TAB}")
            
            logger.info("Successfully authenticated with Google Sheets")
            
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            raise
    
    def write_opportunities(self, opportunities: List[Opportunity]) -> bool:
        """
        Write opportunities to Google Sheets.
        
        Args:
            opportunities: List of opportunities to write
            
        Returns:
            True if successful, False otherwise
        """
        if not self.worksheet:
            logger.error("Google Sheets not initialized")
            return False
        
        try:
            # Prepare headers
            headers = [
                "Program", "Agency", "ID", "Source", "For-profit?", 
                "Award", "Deadline", "Total Score", "Why it fits", 
                "URL", "Last Seen"
            ]
            
            # Prepare data rows
            rows = [headers]
            for opp in opportunities:
                row = [
                    opp.program_name,
                    opp.agency,
                    opp.opportunity_id,
                    opp.source.value,
                    "Yes" if opp.is_for_profit_eligible else "No",
                    opp.estimated_award or "N/A",
                    opp.deadline.isoformat() if opp.deadline else "N/A",
                    str(opp.total_score),
                    opp.get_why_it_fits(),
                    opp.url,
                    opp.last_seen_at.strftime("%Y-%m-%d %H:%M")
                ]
                rows.append(row)
            
            # Clear existing content
            self.worksheet.clear()
            
            # Write new data
            self.worksheet.update(rows)
            
            # Format headers
            self._format_headers()
            
            logger.info(f"Successfully wrote {len(opportunities)} opportunities to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write to Google Sheets: {e}")
            return False
    
    def _format_headers(self):
        """Format the header row."""
        try:
            # Make headers bold
            self.worksheet.format('A1:K1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
            })
            
            # Auto-resize columns
            self.worksheet.columns_auto_resize(0, 10)
            
        except Exception as e:
            logger.warning(f"Failed to format headers: {e}")
    
    def append_opportunity(self, opportunity: Opportunity) -> bool:
        """
        Append a single opportunity to the sheet.
        
        Args:
            opportunity: Opportunity to append
            
        Returns:
            True if successful, False otherwise
        """
        if not self.worksheet:
            logger.error("Google Sheets not initialized")
            return False
        
        try:
            row = [
                opportunity.program_name,
                opportunity.agency,
                opportunity.opportunity_id,
                opportunity.source.value,
                "Yes" if opportunity.is_for_profit_eligible else "No",
                opportunity.estimated_award or "N/A",
                opportunity.deadline.isoformat() if opportunity.deadline else "N/A",
                str(opportunity.total_score),
                opportunity.get_why_it_fits(),
                opportunity.url,
                opportunity.last_seen_at.strftime("%Y-%m-%d %H:%M")
            ]
            
            self.worksheet.append_row(row)
            logger.info(f"Appended opportunity {opportunity.opportunity_id} to Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to append opportunity: {e}")
            return False
    
    def update_opportunity(self, opportunity: Opportunity) -> bool:
        """
        Update an existing opportunity in the sheet.
        
        Args:
            opportunity: Updated opportunity
            
        Returns:
            True if successful, False otherwise
        """
        if not self.worksheet:
            logger.error("Google Sheets not initialized")
            return False
        
        try:
            # Find the row with this opportunity ID
            cell = self.worksheet.find(opportunity.opportunity_id)
            if not cell:
                logger.warning(f"Opportunity {opportunity.opportunity_id} not found in sheet")
                return False
            
            # Update the row
            row_data = [
                opportunity.program_name,
                opportunity.agency,
                opportunity.opportunity_id,
                opportunity.source.value,
                "Yes" if opportunity.is_for_profit_eligible else "No",
                opportunity.estimated_award or "N/A",
                opportunity.deadline.isoformat() if opportunity.deadline else "N/A",
                str(opportunity.total_score),
                opportunity.get_why_it_fits(),
                opportunity.url,
                opportunity.last_seen_at.strftime("%Y-%m-%d %H:%M")
            ]
            
            # Update the row (skip the ID column since we found it)
            range_name = f"A{cell.row}:K{cell.row}"
            self.worksheet.update(range_name, [row_data])
            
            logger.info(f"Updated opportunity {opportunity.opportunity_id} in Google Sheets")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update opportunity: {e}")
            return False
    
    def get_sheet_url(self) -> Optional[str]:
        """Get the URL of the Google Sheet."""
        if self.sheet:
            return self.sheet.url
        return None
    
    def test_connection(self) -> bool:
        """Test the Google Sheets connection."""
        try:
            if not self.worksheet:
                return False
            
            # Try to read the first cell
            self.worksheet.acell('A1')
            return True
            
        except Exception as e:
            logger.error(f"Google Sheets connection test failed: {e}")
            return False 