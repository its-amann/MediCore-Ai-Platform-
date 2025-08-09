"""
Abstract base class for storage implementations
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from ...models.case_models import CaseResponse, CaseCreate, CaseUpdate
from ...models.chat_models import ChatMessage, MessageCreate


class BaseStorage(ABC):
    """Abstract base class for storage implementations"""
    
    @abstractmethod
    async def create_case(self, case_data: CaseCreate) -> CaseResponse:
        """
        Create a new case
        
        Args:
            case_data: Case creation data
            
        Returns:
            Created case object
        """
        pass
    
    @abstractmethod
    async def get_case(self, case_id: str) -> Optional[CaseResponse]:
        """
        Get a case by ID
        
        Args:
            case_id: The case ID
            
        Returns:
            Case object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update_case(self, case_id: str, update_data: CaseUpdate) -> Optional[CaseResponse]:
        """
        Update a case
        
        Args:
            case_id: The case ID
            update_data: Case update data
            
        Returns:
            Updated case object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete_case(self, case_id: str) -> bool:
        """
        Delete a case
        
        Args:
            case_id: The case ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def list_cases(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[CaseResponse], int]:
        """
        List cases with pagination and filtering
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            
        Returns:
            Tuple of (cases list, total count)
        """
        pass
    
    @abstractmethod
    async def store_message(self, message_data: MessageCreate) -> ChatMessage:
        """
        Store a chat message
        
        Args:
            message_data: Message creation data
            
        Returns:
            Created message object
        """
        pass
    
    @abstractmethod
    async def get_message(self, message_id: str) -> Optional[ChatMessage]:
        """
        Get a message by ID
        
        Args:
            message_id: The message ID
            
        Returns:
            Message object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_case_messages(
        self, 
        case_id: str, 
        limit: int = 100, 
        offset: int = 0,
        include_system: bool = True
    ) -> List[ChatMessage]:
        """
        Get messages for a case in chronological order
        
        Args:
            case_id: The case ID
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            include_system: Whether to include system messages
            
        Returns:
            List of messages in chronological order
        """
        pass
    
    @abstractmethod
    async def search_messages(
        self, 
        case_id: str, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> List[ChatMessage]:
        """
        Search messages in a case
        
        Args:
            case_id: The case ID
            query: Search query
            filters: Optional additional filters
            limit: Maximum number of results
            
        Returns:
            List of matching messages
        """
        pass
    
    @abstractmethod
    async def get_next_case_number(self) -> str:
        """
        Get the next available case number
        
        Returns:
            Next case number in sequence
        """
        pass
    
    @abstractmethod
    async def check_case_number_exists(self, case_number: str) -> bool:
        """
        Check if a case number already exists
        
        Args:
            case_number: The case number to check
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_case_by_number(self, case_number: str) -> Optional[CaseResponse]:
        """
        Get a case by its case number
        
        Args:
            case_number: The case number
            
        Returns:
            Case object if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_message_count(self, case_id: str) -> int:
        """
        Get total message count for a case
        
        Args:
            case_id: The case ID
            
        Returns:
            Total number of messages
        """
        pass
    
    @abstractmethod
    async def get_latest_message(self, case_id: str) -> Optional[ChatMessage]:
        """
        Get the latest message in a case
        
        Args:
            case_id: The case ID
            
        Returns:
            Latest message if exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete_message(self, message_id: str) -> bool:
        """
        Delete a message
        
        Args:
            message_id: The message ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def update_message(self, message_id: str, content: str) -> Optional[ChatMessage]:
        """
        Update message content
        
        Args:
            message_id: The message ID
            content: New content
            
        Returns:
            Updated message if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def add_message_metadata(self, message_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Add metadata to a message
        
        Args:
            message_id: The message ID
            metadata: Metadata to add
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_doctor_messages(self, case_id: str, doctor_id: str) -> List[ChatMessage]:
        """
        Get all messages from a specific doctor in a case
        
        Args:
            case_id: The case ID
            doctor_id: The doctor ID
            
        Returns:
            List of doctor messages
        """
        pass
    
    @abstractmethod
    async def get_user_cases(self, user_id: str, skip: int = 0, limit: int = 100) -> Tuple[List[CaseResponse], int]:
        """
        Get cases for a specific user
        
        Args:
            user_id: The user ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (cases list, total count)
        """
        pass
    
    @abstractmethod
    async def search_cases(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[CaseResponse], int]:
        """
        Search cases by title, description, or case number
        
        Args:
            query: Search query
            filters: Optional additional filters
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            Tuple of (matching cases, total count)
        """
        pass
    
    @abstractmethod
    async def get_case_statistics(self, case_id: str) -> Dict[str, Any]:
        """
        Get statistics for a case
        
        Args:
            case_id: The case ID
            
        Returns:
            Dictionary with case statistics
        """
        pass
    
    @abstractmethod
    async def archive_case(self, case_id: str) -> bool:
        """
        Archive a case
        
        Args:
            case_id: The case ID
            
        Returns:
            True if archived, False if not found
        """
        pass
    
    @abstractmethod
    async def restore_case(self, case_id: str) -> bool:
        """
        Restore an archived case
        
        Args:
            case_id: The case ID
            
        Returns:
            True if restored, False if not found
        """
        pass
    
    @abstractmethod
    async def add_case_attachment(self, case_id: str, attachment_data: Dict[str, Any]) -> str:
        """
        Add an attachment to a case
        
        Args:
            case_id: The case ID
            attachment_data: Attachment information
            
        Returns:
            Attachment ID
        """
        pass
    
    @abstractmethod
    async def get_case_attachments(self, case_id: str) -> List[Dict[str, Any]]:
        """
        Get all attachments for a case
        
        Args:
            case_id: The case ID
            
        Returns:
            List of attachment information
        """
        pass
    
    @abstractmethod
    async def delete_attachment(self, case_id: str, attachment_id: str) -> bool:
        """
        Delete a case attachment
        
        Args:
            case_id: The case ID
            attachment_id: The attachment ID
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    # Health check and maintenance methods
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on storage system
        
        Returns:
            Health status information
        """
        pass
    
    @abstractmethod
    async def cleanup_old_data(self, days: int = 90) -> Dict[str, int]:
        """
        Clean up old data
        
        Args:
            days: Number of days to keep data
            
        Returns:
            Dictionary with counts of cleaned items
        """
        pass
    
    @abstractmethod
    async def optimize_storage(self) -> Dict[str, Any]:
        """
        Optimize storage (e.g., rebuild indexes)
        
        Returns:
            Optimization results
        """
        pass