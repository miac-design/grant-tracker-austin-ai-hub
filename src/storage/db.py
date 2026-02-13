"""SQLite database manager for opportunities and change detection."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from ..models import Opportunity, ChangeEvent, ChangeType, Source

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages SQLite database for opportunities and change detection."""
    
    def __init__(self, db_path: str = "opportunities.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS opportunities (
                    opportunity_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    program_name TEXT NOT NULL,
                    agency TEXT NOT NULL,
                    url TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    eligibility TEXT NOT NULL,
                    is_for_profit_eligible BOOLEAN NOT NULL,
                    topic_tags TEXT NOT NULL,
                    deadline TEXT,
                    estimated_award TEXT,
                    contact TEXT,
                    last_seen_at TEXT NOT NULL,
                    fit_score INTEGER NOT NULL,
                    deadline_score INTEGER NOT NULL,
                    award_score INTEGER NOT NULL,
                    total_score INTEGER NOT NULL,
                    hash_signature TEXT NOT NULL,
                    PRIMARY KEY (opportunity_id, source)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_hashes (
                    opportunity_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    hash_signature TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    PRIMARY KEY (opportunity_id, source)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS change_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    change_type TEXT NOT NULL,
                    opportunity_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    what_changed TEXT NOT NULL,
                    url TEXT NOT NULL,
                    detected_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(total_score DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_deadline ON opportunities(deadline)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_source ON opportunities(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_change_events_detected_at ON change_events(detected_at DESC)")
    
    def upsert_opportunities(self, opportunities: List[Opportunity]) -> List[ChangeEvent]:
        """
        Upsert opportunities and detect changes.
        
        Args:
            opportunities: List of opportunities to upsert
            
        Returns:
            List of change events detected
        """
        changes = []
        
        with sqlite3.connect(self.db_path) as conn:
            for opportunity in opportunities:
                change = self._upsert_single_opportunity(conn, opportunity)
                if change:
                    changes.append(change)
        
        logger.info(f"Upserted {len(opportunities)} opportunities, detected {len(changes)} changes")
        return changes
    
    def _upsert_single_opportunity(self, conn: sqlite3.Connection, opportunity: Opportunity) -> Optional[ChangeEvent]:
        """Upsert a single opportunity and detect changes."""
        
        # Check if opportunity exists
        cursor = conn.execute("""
            SELECT hash_signature, program_name, deadline, estimated_award, total_score
            FROM opportunities 
            WHERE opportunity_id = ? AND source = ?
        """, (opportunity.opportunity_id, opportunity.source.value))
        
        existing = cursor.fetchone()
        
        if not existing:
            # New opportunity
            self._insert_opportunity(conn, opportunity)
            return ChangeEvent(
                change_type=ChangeType.ADDED,
                opportunity_id=opportunity.opportunity_id,
                source=opportunity.source,
                what_changed=["new opportunity"],
                url=opportunity.url,
                opportunity=opportunity
            )
        
        # Check if hash changed
        old_hash = existing[0]
        if old_hash != opportunity.hash_signature:
            # Opportunity updated
            what_changed = self._detect_field_changes(existing, opportunity)
            self._update_opportunity(conn, opportunity)
            return ChangeEvent(
                change_type=ChangeType.UPDATED,
                opportunity_id=opportunity.opportunity_id,
                source=opportunity.source,
                what_changed=what_changed,
                url=opportunity.url,
                opportunity=opportunity
            )
        
        # No change, just update last_seen_at
        self._update_last_seen(conn, opportunity)
        return None
    
    def _insert_opportunity(self, conn: sqlite3.Connection, opportunity: Opportunity):
        """Insert a new opportunity."""
        conn.execute("""
            INSERT INTO opportunities (
                opportunity_id, source, program_name, agency, url, summary, eligibility,
                is_for_profit_eligible, topic_tags, deadline, estimated_award, contact,
                last_seen_at, fit_score, deadline_score, award_score, total_score, hash_signature
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            opportunity.opportunity_id,
            opportunity.source.value,
            opportunity.program_name,
            opportunity.agency,
            opportunity.url,
            opportunity.summary,
            opportunity.eligibility,
            opportunity.is_for_profit_eligible,
            json.dumps(opportunity.topic_tags),
            opportunity.deadline.isoformat() if opportunity.deadline else None,
            opportunity.estimated_award,
            opportunity.contact,
            opportunity.last_seen_at.isoformat(),
            opportunity.fit_score,
            opportunity.deadline_score,
            opportunity.award_score,
            opportunity.total_score,
            opportunity.hash_signature
        ))
        
        # Update seen_hashes
        conn.execute("""
            INSERT OR REPLACE INTO seen_hashes (opportunity_id, source, hash_signature, last_updated)
            VALUES (?, ?, ?, ?)
        """, (
            opportunity.opportunity_id,
            opportunity.source.value,
            opportunity.hash_signature,
            opportunity.last_seen_at.isoformat()
        ))
    
    def _update_opportunity(self, conn: sqlite3.Connection, opportunity: Opportunity):
        """Update an existing opportunity."""
        conn.execute("""
            UPDATE opportunities SET
                program_name = ?, agency = ?, url = ?, summary = ?, eligibility = ?,
                is_for_profit_eligible = ?, topic_tags = ?, deadline = ?, estimated_award = ?,
                contact = ?, last_seen_at = ?, fit_score = ?, deadline_score = ?,
                award_score = ?, total_score = ?, hash_signature = ?
            WHERE opportunity_id = ? AND source = ?
        """, (
            opportunity.program_name,
            opportunity.agency,
            opportunity.url,
            opportunity.summary,
            opportunity.eligibility,
            opportunity.is_for_profit_eligible,
            json.dumps(opportunity.topic_tags),
            opportunity.deadline.isoformat() if opportunity.deadline else None,
            opportunity.estimated_award,
            opportunity.contact,
            opportunity.last_seen_at.isoformat(),
            opportunity.fit_score,
            opportunity.deadline_score,
            opportunity.award_score,
            opportunity.total_score,
            opportunity.hash_signature,
            opportunity.opportunity_id,
            opportunity.source.value
        ))
        
        # Update seen_hashes
        conn.execute("""
            UPDATE seen_hashes SET hash_signature = ?, last_updated = ?
            WHERE opportunity_id = ? AND source = ?
        """, (
            opportunity.hash_signature,
            opportunity.last_seen_at.isoformat(),
            opportunity.opportunity_id,
            opportunity.source.value
        ))
    
    def _update_last_seen(self, conn: sqlite3.Connection, opportunity: Opportunity):
        """Update last_seen_at for an unchanged opportunity."""
        conn.execute("""
            UPDATE opportunities SET last_seen_at = ?
            WHERE opportunity_id = ? AND source = ?
        """, (
            opportunity.last_seen_at.isoformat(),
            opportunity.opportunity_id,
            opportunity.source.value
        ))
    
    def _detect_field_changes(self, existing: Tuple, opportunity: Opportunity) -> List[str]:
        """Detect which fields changed between existing and new opportunity."""
        changes = []
        
        if existing[1] != opportunity.program_name:
            changes.append("program_name")
        
        if existing[2] != (opportunity.deadline.isoformat() if opportunity.deadline else None):
            changes.append("deadline")
        
        if existing[3] != opportunity.estimated_award:
            changes.append("estimated_award")
        
        if existing[4] != opportunity.total_score:
            changes.append("total_score")
        
        return changes
    
    def get_top_opportunities(self, limit: int = 200) -> List[Opportunity]:
        """Get top opportunities by total score."""
        opportunities = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM opportunities 
                ORDER BY total_score DESC, deadline ASC
                LIMIT ?
            """, (limit,))
            
            for row in cursor.fetchall():
                opportunity = self._row_to_opportunity(row)
                opportunities.append(opportunity)
        
        return opportunities
    
    def get_recent_changes(self, days: int = 14) -> List[ChangeEvent]:
        """Get recent change events."""
        changes = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM change_events 
                WHERE detected_at >= datetime('now', '-{} days')
                ORDER BY detected_at DESC
            """.format(days))
            
            for row in cursor.fetchall():
                change = ChangeEvent(
                    change_type=ChangeType(row[1]),
                    opportunity_id=row[2],
                    source=Source(row[3]),
                    what_changed=json.loads(row[4]),
                    url=row[5],
                    detected_at=datetime.fromisoformat(row[6])
                )
                changes.append(change)
        
        return changes
    
    def _row_to_opportunity(self, row: Tuple) -> Opportunity:
        """Convert database row to Opportunity object."""
        return Opportunity(
            opportunity_id=row[0],
            source=Source(row[1]),
            program_name=row[2],
            agency=row[3],
            url=row[4],
            summary=row[5],
            eligibility=row[6],
            is_for_profit_eligible=bool(row[7]),
            topic_tags=json.loads(row[8]),
            deadline=datetime.fromisoformat(row[9]).date() if row[9] else None,
            estimated_award=row[10],
            contact=row[11],
            last_seen_at=datetime.fromisoformat(row[12]),
            fit_score=row[13],
            deadline_score=row[14],
            award_score=row[15],
            total_score=row[16],
            hash_signature=row[17]
        )
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total_opps = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
            total_changes = conn.execute("SELECT COUNT(*) FROM change_events").fetchone()[0]
            recent_changes = conn.execute("""
                SELECT COUNT(*) FROM change_events 
                WHERE detected_at >= datetime('now', '-7 days')
            """).fetchone()[0]
            
            return {
                "total_opportunities": total_opps,
                "total_changes": total_changes,
                "recent_changes_7d": recent_changes
            } 