"""
Case Number Generator Service
Generates unique, sequential case numbers with support for high concurrency
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError
import threading

logger = logging.getLogger(__name__)


class CaseNumberGenerator:
    """
    Generates unique case numbers with format: MED-YYYYMMDD-XXXX
    Where:
    - MED: Medical case prefix
    - YYYYMMDD: Current date
    - XXXX: Sequential number for the day (padded with zeros)
    
    Example: MED-20240726-0001
    """
    
    def __init__(self, driver):
        """
        Initialize the case number generator
        
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver
        self._lock = threading.Lock()
        self.prefix = "MED"
        self.number_padding = 4  # 0001, 0002, etc.
        
    def _get_next_sequence_number(self, date_str: str, session) -> int:
        """
        Get the next sequence number for a given date.
        Uses Neo4j's atomic operations to ensure thread safety.
        
        Args:
            date_str: Date string in YYYYMMDD format
            session: Neo4j session
            
        Returns:
            Next sequence number for the date
        """
        # Create or update a CaseNumberSequence node for the date
        query = """
        MERGE (seq:CaseNumberSequence {date: $date})
        ON CREATE SET seq.current_number = 0, seq.created_at = datetime()
        WITH seq
        SET seq.current_number = seq.current_number + 1
        RETURN seq.current_number as next_number
        """
        
        result = session.run(query, {"date": date_str})
        record = result.single()
        
        if record:
            return record["next_number"]
        else:
            raise Exception("Failed to generate sequence number")
    
    def generate_case_number(self, custom_prefix: Optional[str] = None) -> str:
        """
        Generate a new unique case number
        
        Args:
            custom_prefix: Optional custom prefix (default: MED)
            
        Returns:
            Generated case number (e.g., MED-20240726-0001)
        """
        prefix = custom_prefix or self.prefix
        
        # Get current date in YYYYMMDD format
        now = datetime.utcnow()
        date_str = now.strftime("%Y%m%d")
        
        try:
            with self.driver.session() as session:
                # Get next sequence number atomically
                next_number = self._get_next_sequence_number(date_str, session)
                
                # Format the case number
                case_number = f"{prefix}-{date_str}-{str(next_number).zfill(self.number_padding)}"
                
                logger.info(f"Generated case number: {case_number}")
                return case_number
                
        except Exception as e:
            logger.error(f"Error generating case number: {e}")
            raise
    
    def validate_case_number(self, case_number: str) -> bool:
        """
        Validate if a case number follows the correct format
        
        Args:
            case_number: Case number to validate
            
        Returns:
            True if valid, False otherwise
        """
        import re
        
        # Pattern: PREFIX-YYYYMMDD-XXXX
        pattern = r'^[A-Z]{3}-\d{8}-\d{4}$'
        
        return bool(re.match(pattern, case_number))
    
    def parse_case_number(self, case_number: str) -> Optional[Dict[str, Any]]:
        """
        Parse a case number into its components
        
        Args:
            case_number: Case number to parse
            
        Returns:
            Dictionary with prefix, date, and sequence number, or None if invalid
        """
        if not self.validate_case_number(case_number):
            return None
        
        parts = case_number.split('-')
        
        return {
            'prefix': parts[0],
            'date': parts[1],
            'date_formatted': f"{parts[1][:4]}-{parts[1][4:6]}-{parts[1][6:8]}",
            'sequence_number': int(parts[2]),
            'full_number': case_number
        }
    
    def get_current_sequence_number(self, date: Optional[datetime] = None) -> int:
        """
        Get the current sequence number for a given date without incrementing
        
        Args:
            date: Date to check (default: today)
            
        Returns:
            Current sequence number for the date
        """
        if date is None:
            date = datetime.utcnow()
        
        date_str = date.strftime("%Y%m%d")
        
        try:
            with self.driver.session() as session:
                query = """
                MATCH (seq:CaseNumberSequence {date: $date})
                RETURN seq.current_number as current_number
                """
                
                result = session.run(query, {"date": date_str})
                record = result.single()
                
                if record:
                    return record["current_number"]
                else:
                    return 0
                    
        except Exception as e:
            logger.error(f"Error getting current sequence number: {e}")
            return 0
    
    def reset_daily_sequence(self, date: datetime, force: bool = False) -> bool:
        """
        Reset the sequence number for a specific date.
        Use with caution - only for administrative purposes.
        
        Args:
            date: Date to reset
            force: Force reset even if cases exist for that date
            
        Returns:
            True if reset successful, False otherwise
        """
        date_str = date.strftime("%Y%m%d")
        
        try:
            with self.driver.session() as session:
                # Check if cases exist for this date
                if not force:
                    check_query = """
                    MATCH (c:Case)
                    WHERE c.case_number CONTAINS $date_str
                    RETURN count(c) as case_count
                    """
                    
                    result = session.run(check_query, {"date_str": date_str})
                    record = result.single()
                    
                    if record and record["case_count"] > 0:
                        logger.warning(f"Cannot reset sequence - {record['case_count']} cases exist for date {date_str}")
                        return False
                
                # Reset the sequence
                reset_query = """
                MATCH (seq:CaseNumberSequence {date: $date})
                SET seq.current_number = 0, seq.reset_at = datetime()
                RETURN seq
                """
                
                result = session.run(reset_query, {"date": date_str})
                
                if result.single():
                    logger.info(f"Reset sequence for date {date_str}")
                    return True
                else:
                    logger.warning(f"No sequence found for date {date_str}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error resetting sequence: {e}")
            return False
    
    def get_sequence_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about case number sequences
        
        Returns:
            Dictionary with sequence statistics
        """
        try:
            with self.driver.session() as session:
                query = """
                MATCH (seq:CaseNumberSequence)
                RETURN 
                    count(seq) as total_days,
                    sum(seq.current_number) as total_cases,
                    max(seq.current_number) as max_daily_cases,
                    avg(seq.current_number) as avg_daily_cases,
                    collect({date: seq.date, count: seq.current_number}) as daily_counts
                ORDER BY seq.date DESC
                """
                
                result = session.run(query)
                record = result.single()
                
                if record:
                    return {
                        'total_days': record['total_days'],
                        'total_cases': record['total_cases'],
                        'max_daily_cases': record['max_daily_cases'],
                        'avg_daily_cases': round(record['avg_daily_cases'], 2),
                        'recent_days': record['daily_counts'][:7]  # Last 7 days
                    }
                else:
                    return {
                        'total_days': 0,
                        'total_cases': 0,
                        'max_daily_cases': 0,
                        'avg_daily_cases': 0,
                        'recent_days': []
                    }
                    
        except Exception as e:
            logger.error(f"Error getting sequence statistics: {e}")
            return {}