"""Base processor class for all data sources"""
from abc import ABC, abstractmethod
from typing import Tuple, List
from decimal import Decimal


class BaseProcessor(ABC):
    """Abstract base class for data source processors"""
    
    SOURCE_TYPE: str  # Must be overridden by subclasses
    
    @abstractmethod
    def process(self, file_content: str, organization_id: str, user) -> Tuple[list, list, list]:
        """
        Process data from a file or text content
        
        Args:
            file_content: Raw file content as string
            organization_id: Organization UUID
            user: Django User object
        
        Returns:
            Tuple of (created_records, errors, warnings)
            - created_records: List of RawEmission objects (not saved)
            - errors: List of error messages (critical issues)
            - warnings: List of warning messages (non-critical issues)
        """
        pass
