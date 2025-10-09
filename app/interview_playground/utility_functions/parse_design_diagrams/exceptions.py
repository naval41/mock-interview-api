"""
Custom exceptions for the Excalidraw parser.
"""
from typing import Optional, Dict, Any


class ExcalidrawParserError(Exception):
    """Base exception for all parser errors.
    
    Provides context preservation and descriptive error messages.
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Initialize the exception with message and optional context.
        
        Args:
            message: Descriptive error message
            context: Optional dictionary containing error context information
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        """Return formatted error message with context."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class JSONParseError(ExcalidrawParserError):
    """Raised when JSON parsing fails.
    
    This exception is raised when the input JSON is malformed, 
    cannot be parsed, or doesn't contain the expected structure.
    """
    
    def __init__(self, message: str, json_content: Optional[str] = None, 
                 line_number: Optional[int] = None):
        """Initialize JSON parse error.
        
        Args:
            message: Descriptive error message
            json_content: The problematic JSON content (truncated if too long)
            line_number: Line number where parsing failed (if available)
        """
        context = {}
        if json_content is not None:
            # Truncate long JSON content for readability
            truncated_content = json_content[:200] + "..." if len(json_content) > 200 else json_content
            context["json_content"] = truncated_content
        if line_number is not None:
            context["line_number"] = line_number
            
        super().__init__(message, context)


class ValidationError(ExcalidrawParserError):
    """Raised when required fields are missing or invalid.
    
    This exception is raised when the JSON structure is valid but 
    required fields are missing or contain invalid values.
    """
    
    def __init__(self, message: str, field_name: Optional[str] = None, 
                 field_value: Any = ..., element_id: Optional[str] = None,
                 element_type: Optional[str] = None):
        """Initialize validation error.
        
        Args:
            message: Descriptive error message
            field_name: Name of the field that failed validation
            field_value: The invalid field value (use ... as sentinel for not provided)
            element_id: ID of the element being processed
            element_type: Type of the element being processed
        """
        context = {}
        if field_name is not None:
            context["field_name"] = field_name
        if field_value is not ...:  # Use ellipsis as sentinel value
            context["field_value"] = field_value
        if element_id is not None:
            context["element_id"] = element_id
        if element_type is not None:
            context["element_type"] = element_type
            
        super().__init__(message, context)


class ElementProcessingError(ExcalidrawParserError):
    """Raised when element processing fails.
    
    This exception is raised when an element cannot be processed
    due to unexpected data or processing errors.
    """
    
    def __init__(self, message: str, element_id: Optional[str] = None,
                 element_type: Optional[str] = None, element_data: Optional[Dict[str, Any]] = None):
        """Initialize element processing error.
        
        Args:
            message: Descriptive error message
            element_id: ID of the element that failed processing
            element_type: Type of the element that failed processing
            element_data: The element data that caused the error (truncated if too large)
        """
        context = {}
        if element_id is not None:
            context["element_id"] = element_id
        if element_type is not None:
            context["element_type"] = element_type
        if element_data is not None:
            # Truncate large element data for readability
            context["element_data"] = str(element_data)[:300] + "..." if len(str(element_data)) > 300 else element_data
            
        super().__init__(message, context)