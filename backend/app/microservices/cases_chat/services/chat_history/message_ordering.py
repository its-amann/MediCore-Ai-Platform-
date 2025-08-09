"""
Message Ordering Service
Handles message sequencing and ordering for chat history
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from neo4j import AsyncDriver

logger = logging.getLogger(__name__)

class MessageOrderingService:
    """Service for managing message ordering and sequencing"""
    
    def __init__(self, driver: AsyncDriver):
        self.driver = driver
    
    async def ensure_message_ordering(self, case_id: str) -> Dict[str, Any]:
        """Ensure all messages in a case have proper sequence numbers"""
        
        # Get all messages for the case
        query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_MESSAGE]->(m:Message)
        RETURN m
        ORDER BY m.timestamp, m.id
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {"case_id": case_id})
            messages = []
            async for record in result:
                messages.append(dict(record["m"]))
        
        # Update sequence numbers
        updates = 0
        for idx, message in enumerate(messages, 1):
            if message.get('sequence_number') != idx:
                update_query = """
                MATCH (m:Message {id: $message_id})
                SET m.sequence_number = $sequence
                """
                
                async with self.driver.session() as session:
                    await session.run(update_query, {
                        "message_id": message['id'],
                        "sequence": idx
                    })
                updates += 1
        
        return {
            "case_id": case_id,
            "total_messages": len(messages),
            "sequence_updates": updates
        }
    
    async def get_next_sequence_number(self, case_id: str) -> int:
        """Get the next sequence number for a new message"""
        
        query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_MESSAGE]->(m:Message)
        RETURN MAX(m.sequence_number) as max_sequence
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            max_sequence = record["max_sequence"] if record and record["max_sequence"] else 0
            return max_sequence + 1
    
    async def reorder_messages_after_deletion(self, case_id: str, deleted_sequence: int) -> int:
        """Reorder message sequences after a deletion"""
        
        query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_MESSAGE]->(m:Message)
        WHERE m.sequence_number > $deleted_sequence
        SET m.sequence_number = m.sequence_number - 1
        RETURN COUNT(m) as updated_count
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "case_id": case_id,
                "deleted_sequence": deleted_sequence
            })
            record = await result.single()
            
            return record["updated_count"] if record else 0
    
    async def insert_message_at_position(
        self, 
        case_id: str, 
        message_id: str,
        position: int
    ) -> Dict[str, Any]:
        """Insert a message at a specific position, shifting others"""
        
        # First, shift existing messages
        shift_query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_MESSAGE]->(m:Message)
        WHERE m.sequence_number >= $position
        SET m.sequence_number = m.sequence_number + 1
        RETURN COUNT(m) as shifted_count
        """
        
        async with self.driver.session() as session:
            result = await session.run(shift_query, {
                "case_id": case_id,
                "position": position
            })
            shifted = await result.single()
        
        # Then set the message's sequence number
        update_query = """
        MATCH (m:Message {id: $message_id})
        SET m.sequence_number = $position
        """
        
        async with self.driver.session() as session:
            await session.run(update_query, {
                "message_id": message_id,
                "position": position
            })
        
        return {
            "message_id": message_id,
            "position": position,
            "shifted_messages": shifted["shifted_count"] if shifted else 0
        }
    
    async def validate_message_ordering(self, case_id: str) -> Dict[str, Any]:
        """Validate that message ordering is consistent"""
        
        query = """
        MATCH (c:Case {case_id: $case_id})-[:HAS_MESSAGE]->(m:Message)
        WITH m ORDER BY m.timestamp
        WITH COLLECT(m) as messages
        UNWIND RANGE(0, SIZE(messages)-1) as idx
        WITH messages[idx] as msg, idx + 1 as expected_seq
        WHERE msg.sequence_number <> expected_seq
        RETURN COUNT(msg) as inconsistent_count
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {"case_id": case_id})
            record = await result.single()
            
            inconsistent = record["inconsistent_count"] if record else 0
            
            if inconsistent > 0:
                # Fix the inconsistencies
                await self.ensure_message_ordering(case_id)
                
            return {
                "case_id": case_id,
                "inconsistent_messages": inconsistent,
                "fixed": inconsistent > 0
            }