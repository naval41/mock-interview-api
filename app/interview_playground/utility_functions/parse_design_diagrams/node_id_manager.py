"""Node ID management for Mermaid diagrams.

This module provides node ID generation and sanitization functionality
for Mermaid diagrams, ensuring valid identifiers and handling conflicts.
"""

import re
from typing import Dict, Set, Optional
from enum import Enum


class NodeIdManager:
    """Manages node ID generation and sanitization for Mermaid diagrams.
    
    This class ensures that all node IDs are valid Mermaid identifiers
    and handles conflicts, special characters, and empty labels. It provides
    comprehensive ID generation with fallback mechanisms and validation
    for Mermaid syntax compliance.
    
    Features:
    - Meaningful ID generation from text labels
    - Conflict resolution with automatic suffixing
    - Special character escaping for node labels
    - Fallback ID generation for unlabeled elements
    - Mermaid syntax validation and compliance checking
    """
    
    # Mermaid reserved keywords that cannot be used as node IDs
    RESERVED_KEYWORDS = {
        'graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 'stateDiagram',
        'journey', 'gantt', 'pie', 'gitgraph', 'mindmap', 'timeline', 'sankey',
        'subgraph', 'end', 'click', 'class', 'classDef', 'style', 'linkStyle',
        'fill', 'stroke', 'color', 'TD', 'TB', 'BT', 'RL', 'LR'
    }
    
    def __init__(self):
        """Initialize the node ID manager."""
        self._used_ids: Set[str] = set()
        self._id_counter = 0
        self._element_to_id: Dict[str, str] = {}  # element_id -> mermaid_id
        self._id_to_element: Dict[str, str] = {}  # mermaid_id -> element_id
        self._conflict_counters: Dict[str, int] = {}  # base_id -> counter
    
    def get_node_id(self, element_id: str, label: str = "") -> str:
        """Get or generate a Mermaid-compatible node ID.
        
        This method implements a comprehensive ID generation strategy:
        1. Return cached ID if already generated for this element
        2. Try to create meaningful ID from label text
        3. Try to use sanitized element ID
        4. Generate unique fallback ID with counter
        
        Args:
            element_id: Original element ID from Excalidraw
            label: Text label for the element (used for meaningful IDs)
            
        Returns:
            Valid Mermaid node ID
            
        Raises:
            ValueError: If element_id is empty or invalid
        """
        if not element_id or not isinstance(element_id, str):
            raise ValueError("Element ID must be a non-empty string")
        
        # Return cached ID if already generated
        if element_id in self._element_to_id:
            return self._element_to_id[element_id]
        
        # Try to create meaningful ID from label
        if label and label.strip():
            candidate_id = self._generate_meaningful_id(label.strip())
            if candidate_id:
                final_id = self._resolve_conflicts(candidate_id)
                self._register_id(element_id, final_id)
                return final_id
        
        # Try to use sanitized element ID
        candidate_id = self._sanitize_id(element_id)
        if candidate_id and self._is_valid_mermaid_id(candidate_id):
            final_id = self._resolve_conflicts(candidate_id)
            self._register_id(element_id, final_id)
            return final_id
        
        # Generate unique fallback ID
        fallback_id = self._generate_fallback_id()
        self._register_id(element_id, fallback_id)
        return fallback_id
    
    def _generate_meaningful_id(self, label: str) -> str:
        """Generate a meaningful ID from a text label.
        
        Args:
            label: Text label to convert to ID
            
        Returns:
            Sanitized ID string, or empty string if not possible
        """
        if not label:
            return ""
        
        # Extract meaningful words from label
        words = re.findall(r'\b\w+\b', label.lower())
        if not words:
            return self._sanitize_id(label)
        
        # Create camelCase or snake_case ID from words
        if len(words) == 1:
            base_id = words[0]
        elif len(words) == 2:
            # Use camelCase for two words
            base_id = words[0] + words[1].capitalize()
        else:
            # Use camelCase for multiple words, take first 3 words
            base_id = words[0] + ''.join(word.capitalize() for word in words[1:3])
        
        return self._sanitize_id(base_id)
    
    def _sanitize_id(self, text: str) -> str:
        """Sanitize text to create a valid Mermaid ID.
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized ID string, or empty string if not possible
        """
        if not text:
            return ""
        
        # Convert to string and strip whitespace
        text = str(text).strip()
        if not text:
            return ""
        
        # Replace spaces and special characters with underscores
        # Keep alphanumeric, underscore, and hyphen
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', text)
        
        # Remove multiple consecutive underscores
        sanitized = re.sub(r'_+', '_', sanitized)
        
        # Ensure it starts with a letter or underscore
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == '_'):
            sanitized = f"_{sanitized}"
        
        # Limit length to reasonable size
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        # Remove trailing underscores and hyphens
        sanitized = sanitized.rstrip('_-')
        
        # Ensure we have something left
        if not sanitized:
            return ""
        
        return sanitized
    
    def _resolve_conflicts(self, base_id: str) -> str:
        """Resolve ID conflicts by adding numeric suffixes.
        
        Args:
            base_id: Base ID that might conflict
            
        Returns:
            Unique ID with suffix if needed
        """
        if not base_id:
            return self._generate_fallback_id()
        
        # Check if base ID is available
        if base_id not in self._used_ids and not self._is_reserved_keyword(base_id):
            return base_id
        
        # Generate suffixed versions until we find an available one
        if base_id not in self._conflict_counters:
            self._conflict_counters[base_id] = 1
        
        while True:
            candidate_id = f"{base_id}_{self._conflict_counters[base_id]}"
            self._conflict_counters[base_id] += 1
            
            if (candidate_id not in self._used_ids and 
                not self._is_reserved_keyword(candidate_id) and
                self._is_valid_mermaid_id(candidate_id)):
                return candidate_id
            
            # Safety check to prevent infinite loops
            if self._conflict_counters[base_id] > 1000:
                return self._generate_fallback_id()
    
    def _generate_fallback_id(self) -> str:
        """Generate a unique fallback ID for unlabeled elements.
        
        Returns:
            Unique fallback ID
        """
        while True:
            fallback_id = f"node_{self._id_counter}"
            self._id_counter += 1
            
            if (fallback_id not in self._used_ids and 
                self._is_valid_mermaid_id(fallback_id)):
                return fallback_id
            
            # Safety check
            if self._id_counter > 10000:
                # This should never happen in practice
                import uuid
                return f"node_{uuid.uuid4().hex[:8]}"
    
    def _register_id(self, element_id: str, mermaid_id: str) -> None:
        """Register a mapping between element ID and Mermaid ID.
        
        Args:
            element_id: Original element ID
            mermaid_id: Generated Mermaid ID
        """
        self._used_ids.add(mermaid_id)
        self._element_to_id[element_id] = mermaid_id
        self._id_to_element[mermaid_id] = element_id
    
    def _is_reserved_keyword(self, id_candidate: str) -> bool:
        """Check if an ID candidate is a Mermaid reserved keyword.
        
        Args:
            id_candidate: ID to check
            
        Returns:
            True if the ID is reserved
        """
        return id_candidate.lower() in self.RESERVED_KEYWORDS
    
    def _is_valid_mermaid_id(self, id_candidate: str) -> bool:
        """Validate that an ID is compatible with Mermaid syntax.
        
        Args:
            id_candidate: ID to validate
            
        Returns:
            True if the ID is valid for Mermaid
        """
        if not id_candidate:
            return False
        
        # Must start with letter or underscore
        if not (id_candidate[0].isalpha() or id_candidate[0] == '_'):
            return False
        
        # Must contain only valid characters
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', id_candidate):
            return False
        
        # Must not be a reserved keyword
        if self._is_reserved_keyword(id_candidate):
            return False
        
        # Must not be too long
        if len(id_candidate) > 50:
            return False
        
        return True
    
    def sanitize_label(self, text: str) -> str:
        """Sanitize text for use as a node label in Mermaid.
        
        This method handles comprehensive escaping of special characters
        that have meaning in Mermaid syntax, ensuring labels display correctly.
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized label text safe for Mermaid
        """
        if not text:
            return ""
        
        # Convert to string and normalize whitespace
        text = str(text).strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        
        if not text:
            return ""
        
        # Escape special Mermaid characters using a character-by-character approach
        # to avoid double-escaping issues
        result = []
        for char in text:
            if char == '&':
                result.append('&amp;')
            elif char == '"':
                result.append('&quot;')
            elif char == "'":
                result.append('&#39;')
            elif char == '[':
                result.append('&#91;')
            elif char == ']':
                result.append('&#93;')
            elif char == '(':
                result.append('&#40;')
            elif char == ')':
                result.append('&#41;')
            elif char == '{':
                result.append('&#123;')
            elif char == '}':
                result.append('&#125;')
            elif char == '<':
                result.append('&lt;')
            elif char == '>':
                result.append('&gt;')
            elif char == '|':
                result.append('&#124;')
            elif char == '\\':
                result.append('&#92;')
            elif char == '/':
                result.append('&#47;')
            elif char == '#':
                result.append('&#35;')
            elif char == '%':
                result.append('&#37;')
            elif char == '`':
                result.append('&#96;')
            elif char == '~':
                result.append('&#126;')
            elif char == '^':
                result.append('&#94;')
            elif char == '*':
                result.append('&#42;')
            elif char == '+':
                result.append('&#43;')
            elif char == '=':
                result.append('&#61;')
            elif char == '?':
                result.append('&#63;')
            elif char == '!':
                result.append('&#33;')
            elif char == '@':
                result.append('&#64;')
            elif char == '$':
                result.append('&#36;')
            else:
                result.append(char)
        
        text = ''.join(result)
        
        # Handle newlines and tabs
        text = text.replace('\n', ' ')
        text = text.replace('\t', ' ')
        text = text.replace('\r', ' ')
        
        # Normalize multiple spaces again after escaping
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Limit length for readability
        if len(text) > 100:
            text = text[:97] + "..."
        
        return text
    
    def validate_mermaid_syntax(self, mermaid_id: str) -> bool:
        """Validate that a Mermaid ID complies with syntax requirements.
        
        This method provides comprehensive validation to ensure generated
        IDs will work correctly in Mermaid diagrams.
        
        Args:
            mermaid_id: ID to validate
            
        Returns:
            True if the ID is valid, False otherwise
        """
        return self._is_valid_mermaid_id(mermaid_id)
    
    def get_element_id(self, mermaid_id: str) -> Optional[str]:
        """Get the original element ID for a Mermaid ID.
        
        Args:
            mermaid_id: Mermaid node ID
            
        Returns:
            Original element ID, or None if not found
        """
        return self._id_to_element.get(mermaid_id)
    
    def get_all_ids(self) -> Set[str]:
        """Get all currently used Mermaid IDs.
        
        Returns:
            Set of all used Mermaid IDs
        """
        return self._used_ids.copy()
    
    def reset(self) -> None:
        """Reset the manager state, clearing all cached IDs.
        
        This is useful when processing multiple diagrams or when
        you need to start fresh with ID generation.
        """
        self._used_ids.clear()
        self._element_to_id.clear()
        self._id_to_element.clear()
        self._conflict_counters.clear()
        self._id_counter = 0