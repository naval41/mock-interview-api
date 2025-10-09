"""Mermaid syntax validation utilities.

This module provides comprehensive validation for Mermaid diagram syntax,
ensuring generated diagrams are syntactically correct and will render properly.
"""

import re
from typing import List, Dict, Set, Optional, Tuple, Any
from enum import Enum
from dataclasses import dataclass

from .mermaid_generator import MermaidDiagramType, MermaidDirection


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""
    ERROR = "error"      # Syntax errors that prevent rendering
    WARNING = "warning"  # Issues that may cause problems
    INFO = "info"        # Style or best practice suggestions


@dataclass
class ValidationIssue:
    """Represents a validation issue found in Mermaid syntax.
    
    Attributes:
        severity: Severity level of the issue
        message: Human-readable description of the issue
        line_number: Line number where the issue occurs (1-based)
        column: Column position where the issue occurs (1-based)
        suggestion: Optional suggestion for fixing the issue
        rule_id: Identifier for the validation rule that triggered
    """
    severity: ValidationSeverity
    message: str
    line_number: int
    column: int = 0
    suggestion: Optional[str] = None
    rule_id: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of Mermaid syntax validation.
    
    Attributes:
        is_valid: Whether the syntax is valid
        issues: List of validation issues found
        diagram_type: Detected diagram type
        node_count: Number of nodes found
        edge_count: Number of edges found
        warnings_count: Number of warnings
        errors_count: Number of errors
    """
    is_valid: bool
    issues: List[ValidationIssue]
    diagram_type: Optional[MermaidDiagramType] = None
    node_count: int = 0
    edge_count: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    
    def __post_init__(self):
        """Calculate counts from issues."""
        self.warnings_count = sum(1 for issue in self.issues 
                                 if issue.severity == ValidationSeverity.WARNING)
        self.errors_count = sum(1 for issue in self.issues 
                               if issue.severity == ValidationSeverity.ERROR)


class MermaidValidator:
    """Comprehensive Mermaid syntax validator.
    
    This class provides validation for Mermaid diagram syntax, checking for:
    - Syntax errors that prevent rendering
    - Node ID conflicts and invalid characters
    - Edge syntax and connection validity
    - Diagram type consistency
    - Best practice violations
    - Performance considerations for large diagrams
    """
    
    # Mermaid reserved keywords
    RESERVED_KEYWORDS = {
        'graph', 'flowchart', 'sequenceDiagram', 'classDiagram', 'stateDiagram',
        'journey', 'gantt', 'pie', 'gitgraph', 'mindmap', 'timeline', 'sankey',
        'subgraph', 'end', 'click', 'class', 'classDef', 'style', 'linkStyle',
        'fill', 'stroke', 'color', 'TD', 'TB', 'BT', 'RL', 'LR'
    }
    
    # Valid diagram directions
    VALID_DIRECTIONS = {'TD', 'TB', 'BT', 'RL', 'LR'}
    
    # Valid node shapes patterns
    NODE_SHAPE_PATTERNS = {
        r'\[.*?\]': 'rectangle',
        r'\(.*?\)': 'rounded',
        r'\(\(.*?\)\)': 'circle',
        r'\{.*?\}': 'diamond',
        r'\[\[.*?\]\]': 'subroutine',
        r'\[\(.*?\)\]': 'cylinder',
        r'\>\[.*?\]\]': 'asymmetric',
        r'\[\[.*?\<\]': 'asymmetric_alt'
    }
    
    # Valid edge patterns
    EDGE_PATTERNS = {
        r'-->': 'solid_arrow',
        r'---': 'solid_line',
        r'-\.->': 'dotted_arrow',
        r'-\.-': 'dotted_line',
        r'==>': 'thick_arrow',
        r'===': 'thick_line',
        r'~~>': 'invisible_arrow',
        r'~~~': 'invisible_line'
    }
    
    def __init__(self, strict_mode: bool = False):
        """Initialize the validator.
        
        Args:
            strict_mode: Whether to use strict validation rules
        """
        self.strict_mode = strict_mode
        self._node_ids: Set[str] = set()
        self._subgraph_ids: Set[str] = set()
        self._current_line = 0
        
    def validate(self, mermaid_syntax: str) -> ValidationResult:
        """Validate Mermaid diagram syntax.
        
        Args:
            mermaid_syntax: Mermaid diagram syntax to validate
            
        Returns:
            ValidationResult with validation status and issues
        """
        if not mermaid_syntax or not mermaid_syntax.strip():
            return ValidationResult(
                is_valid=False,
                issues=[ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message="Empty Mermaid syntax provided",
                    line_number=1,
                    rule_id="EMPTY_SYNTAX"
                )]
            )
        
        # Reset state
        self._node_ids.clear()
        self._subgraph_ids.clear()
        self._current_line = 0
        
        issues = []
        lines = mermaid_syntax.strip().split('\n')
        
        # Validate diagram header
        diagram_type = self._validate_diagram_header(lines, issues)
        
        # Validate syntax line by line
        node_count = 0
        edge_count = 0
        
        for i, line in enumerate(lines):
            self._current_line = i + 1
            line = line.strip()
            
            if not line or line.startswith('%%'):  # Skip empty lines and comments
                continue
                
            if i == 0:  # Skip header line
                continue
                
            # Validate individual line
            line_issues, nodes, edges = self._validate_line(line, i + 1)
            issues.extend(line_issues)
            node_count += nodes
            edge_count += edges
        
        # Post-validation checks
        self._validate_consistency(issues)
        
        # Determine if valid (no errors)
        has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
        
        return ValidationResult(
            is_valid=not has_errors,
            issues=issues,
            diagram_type=diagram_type,
            node_count=node_count,
            edge_count=edge_count
        )
    
    def _validate_diagram_header(self, lines: List[str], issues: List[ValidationIssue]) -> Optional[MermaidDiagramType]:
        """Validate the diagram header line.
        
        Args:
            lines: All lines of the diagram
            issues: List to append validation issues to
            
        Returns:
            Detected diagram type or None if invalid
        """
        if not lines:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="No diagram header found",
                line_number=1,
                rule_id="MISSING_HEADER"
            ))
            return None
        
        header = lines[0].strip()
        
        # Check for valid diagram type
        if header.startswith('flowchart '):
            direction = header.split()[1] if len(header.split()) > 1 else 'TD'
            if direction not in self.VALID_DIRECTIONS:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid flowchart direction: {direction}",
                    line_number=1,
                    suggestion=f"Use one of: {', '.join(self.VALID_DIRECTIONS)}",
                    rule_id="INVALID_DIRECTION"
                ))
            return MermaidDiagramType.FLOWCHART
            
        elif header.startswith('graph '):
            direction = header.split()[1] if len(header.split()) > 1 else 'TD'
            if direction not in self.VALID_DIRECTIONS:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid graph direction: {direction}",
                    line_number=1,
                    suggestion=f"Use one of: {', '.join(self.VALID_DIRECTIONS)}",
                    rule_id="INVALID_DIRECTION"
                ))
            return MermaidDiagramType.GRAPH
            
        elif header == 'mindmap':
            return MermaidDiagramType.MINDMAP
            
        else:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Unknown diagram type: {header}",
                line_number=1,
                suggestion="Use 'flowchart TD', 'graph TD', or 'mindmap'",
                rule_id="UNKNOWN_DIAGRAM_TYPE"
            ))
            return None
    
    def _validate_line(self, line: str, line_number: int) -> Tuple[List[ValidationIssue], int, int]:
        """Validate a single line of Mermaid syntax.
        
        Args:
            line: Line to validate
            line_number: Line number for error reporting
            
        Returns:
            Tuple of (issues, node_count, edge_count)
        """
        issues = []
        node_count = 0
        edge_count = 0
        
        # Skip subgraph declarations for now
        if line.startswith('subgraph ') or line == 'end':
            return issues, node_count, edge_count
        
        # Check for node definitions and connections
        # Look for any arrow-like patterns (including invalid ones)
        has_arrow_pattern = any(arrow in line for arrow in ['-->', '---', '-.->', '==>', '->', '<-', '-.->'])
        
        if has_arrow_pattern:
            # This is a connection line
            connection_issues, nodes, edges = self._validate_connection(line, line_number)
            issues.extend(connection_issues)
            node_count += nodes
            edge_count += edges
        else:
            # This might be a standalone node definition
            node_issues, nodes = self._validate_node_definition(line, line_number)
            issues.extend(node_issues)
            node_count += nodes
        
        return issues, node_count, edge_count
    
    def _validate_connection(self, line: str, line_number: int) -> Tuple[List[ValidationIssue], int, int]:
        """Validate a connection line.
        
        Args:
            line: Connection line to validate
            line_number: Line number for error reporting
            
        Returns:
            Tuple of (issues, node_count, edge_count)
        """
        issues = []
        node_count = 0
        edge_count = 0
        
        # Find edge pattern
        edge_pattern = None
        for pattern in self.EDGE_PATTERNS:
            if re.search(pattern, line):
                edge_pattern = pattern
                break
        
        if not edge_pattern:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Invalid connection syntax",
                line_number=line_number,
                suggestion="Use valid connection syntax like '-->', '---', etc.",
                rule_id="INVALID_CONNECTION"
            ))
            return issues, node_count, edge_count
        
        # Split by the edge pattern to get source and target
        parts = re.split(edge_pattern, line)
        if len(parts) != 2:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Invalid connection format",
                line_number=line_number,
                rule_id="INVALID_CONNECTION_FORMAT"
            ))
            return issues, node_count, edge_count
        
        source_part = parts[0].strip()
        target_part = parts[1].strip()
        
        # Validate source node
        source_issues, source_nodes = self._validate_node_reference(source_part, line_number, "source")
        issues.extend(source_issues)
        node_count += source_nodes
        
        # Validate target node
        target_issues, target_nodes = self._validate_node_reference(target_part, line_number, "target")
        issues.extend(target_issues)
        node_count += target_nodes
        
        edge_count = 1
        
        return issues, node_count, edge_count
    
    def _validate_node_reference(self, node_part: str, line_number: int, context: str) -> Tuple[List[ValidationIssue], int]:
        """Validate a node reference in a connection.
        
        Args:
            node_part: Node part to validate
            line_number: Line number for error reporting
            context: Context (source/target) for error messages
            
        Returns:
            Tuple of (issues, node_count)
        """
        issues = []
        node_count = 0
        
        if not node_part:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Empty {context} node reference",
                line_number=line_number,
                rule_id="EMPTY_NODE_REFERENCE"
            ))
            return issues, node_count
        
        # Extract node ID and shape/label
        node_id = None
        
        # Check for node with shape
        for pattern in self.NODE_SHAPE_PATTERNS:
            match = re.search(f'(\\w+){pattern}', node_part)
            if match:
                node_id = match.group(1)
                break
        
        # If no shape pattern, might be just an ID
        if not node_id:
            # Simple ID reference
            if re.match(r'^\w+$', node_part):
                node_id = node_part
            else:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid {context} node format: {node_part}",
                    line_number=line_number,
                    rule_id="INVALID_NODE_FORMAT"
                ))
                return issues, node_count
        
        # For connections, we need to check if this is a node definition or just a reference
        is_node_definition = any(re.search(pattern, node_part) for pattern in self.NODE_SHAPE_PATTERNS)
        
        if is_node_definition:
            # This is a node definition in a connection - validate for duplicates
            id_issues = self._validate_node_id(node_id, line_number)
            issues.extend(id_issues)
            
            if node_id:
                self._node_ids.add(node_id)
                node_count = 1
        else:
            # This is just a node reference - validate syntax only
            id_issues = self._validate_node_id_syntax_only(node_id, line_number)
            issues.extend(id_issues)
            
            # Count as a node if we haven't seen it before
            if node_id and node_id not in self._node_ids:
                self._node_ids.add(node_id)
                node_count = 1
        
        return issues, node_count
    
    def _validate_node_definition(self, line: str, line_number: int) -> Tuple[List[ValidationIssue], int]:
        """Validate a standalone node definition.
        
        Args:
            line: Node definition line
            line_number: Line number for error reporting
            
        Returns:
            Tuple of (issues, node_count)
        """
        issues = []
        node_count = 0
        
        # Check if this looks like a node definition
        has_shape = any(re.search(pattern, line) for pattern in self.NODE_SHAPE_PATTERNS)
        
        if has_shape:
            # Extract node ID
            for pattern in self.NODE_SHAPE_PATTERNS:
                match = re.search(f'(\\w+){pattern}', line)
                if match:
                    node_id = match.group(1)
                    id_issues = self._validate_node_id(node_id, line_number)
                    issues.extend(id_issues)
                    
                    if node_id:
                        self._node_ids.add(node_id)
                        node_count = 1
                    break
        
        return issues, node_count
    
    def _validate_node_id(self, node_id: str, line_number: int) -> List[ValidationIssue]:
        """Validate a node ID.
        
        Args:
            node_id: Node ID to validate
            line_number: Line number for error reporting
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if not node_id:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Empty node ID",
                line_number=line_number,
                rule_id="EMPTY_NODE_ID"
            ))
            return issues
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', node_id):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Invalid node ID format: {node_id}",
                line_number=line_number,
                suggestion="Node IDs must start with letter/underscore and contain only alphanumeric, underscore, or hyphen",
                rule_id="INVALID_NODE_ID_FORMAT"
            ))
        
        # Check for reserved keywords
        if node_id.lower() in self.RESERVED_KEYWORDS:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Node ID '{node_id}' is a reserved keyword",
                line_number=line_number,
                suggestion="Use a different node ID",
                rule_id="RESERVED_KEYWORD"
            ))
        
        # Check for duplicate IDs
        if node_id in self._node_ids:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Duplicate node ID: {node_id}",
                line_number=line_number,
                suggestion="Each node ID must be unique",
                rule_id="DUPLICATE_NODE_ID"
            ))
        
        # Check length
        if len(node_id) > 50:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Node ID '{node_id}' is very long ({len(node_id)} characters)",
                line_number=line_number,
                suggestion="Consider using shorter node IDs for better readability",
                rule_id="LONG_NODE_ID"
            ))
        
        return issues
    
    def _validate_node_id_syntax_only(self, node_id: str, line_number: int) -> List[ValidationIssue]:
        """Validate node ID syntax without checking for duplicates."""
        issues = []
        
        if not node_id:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message="Empty node ID",
                line_number=line_number,
                rule_id="EMPTY_NODE_ID"
            ))
            return issues
        
        # Check for valid characters
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', node_id):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Invalid node ID format: {node_id}",
                line_number=line_number,
                suggestion="Node IDs must start with letter/underscore and contain only alphanumeric, underscore, or hyphen",
                rule_id="INVALID_NODE_ID_FORMAT"
            ))
        
        # Check for reserved keywords
        if node_id.lower() in self.RESERVED_KEYWORDS:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                message=f"Node ID '{node_id}' is a reserved keyword",
                line_number=line_number,
                suggestion="Use a different node ID",
                rule_id="RESERVED_KEYWORD"
            ))
        
        # Check length
        if len(node_id) > 50:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Node ID '{node_id}' is very long ({len(node_id)} characters)",
                line_number=line_number,
                suggestion="Consider using shorter node IDs for better readability",
                rule_id="LONG_NODE_ID"
            ))
        
        return issues
    
    def _validate_consistency(self, issues: List[ValidationIssue]) -> None:
        """Perform consistency checks after parsing all lines.
        
        Args:
            issues: List to append validation issues to
        """
        # Check for reasonable diagram size
        if len(self._node_ids) > 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message=f"Large diagram with {len(self._node_ids)} nodes may have performance issues",
                line_number=1,
                suggestion="Consider breaking into smaller diagrams or using subgraphs",
                rule_id="LARGE_DIAGRAM"
            ))
        
        # Check for isolated nodes (this would require more complex analysis)
        # For now, just add a placeholder for future enhancement
        pass
    
    def validate_node_id_syntax(self, node_id: str) -> bool:
        """Validate that a node ID follows Mermaid syntax rules.
        
        Args:
            node_id: Node ID to validate
            
        Returns:
            True if the node ID is valid
        """
        if not node_id:
            return False
        
        # Must start with letter or underscore
        if not (node_id[0].isalpha() or node_id[0] == '_'):
            return False
        
        # Must contain only valid characters
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', node_id):
            return False
        
        # Must not be a reserved keyword
        if node_id.lower() in self.RESERVED_KEYWORDS:
            return False
        
        # Must not be too long
        if len(node_id) > 50:
            return False
        
        return True
    
    def validate_label_syntax(self, label: str) -> bool:
        """Validate that a label is properly escaped for Mermaid.
        
        Args:
            label: Label text to validate
            
        Returns:
            True if the label is properly formatted
        """
        if not label:
            return True  # Empty labels are valid
        
        # Check for unescaped special characters that could break syntax
        dangerous_chars = ['[', ']', '(', ')', '{', '}', '"', "'"]
        
        for char in dangerous_chars:
            if char in label and f'&#{ord(char)};' not in label and f'&{char};' not in label:
                # Character is present but not escaped
                return False
        
        return True
    
    def get_validation_summary(self, result: ValidationResult) -> str:
        """Generate a human-readable validation summary.
        
        Args:
            result: Validation result to summarize
            
        Returns:
            Formatted summary string
        """
        if result.is_valid:
            summary = f"✅ Valid Mermaid syntax\n"
        else:
            summary = f"❌ Invalid Mermaid syntax ({result.errors_count} errors)\n"
        
        summary += f"📊 Statistics:\n"
        summary += f"  - Nodes: {result.node_count}\n"
        summary += f"  - Edges: {result.edge_count}\n"
        summary += f"  - Errors: {result.errors_count}\n"
        summary += f"  - Warnings: {result.warnings_count}\n"
        
        if result.diagram_type:
            summary += f"  - Type: {result.diagram_type.value}\n"
        
        if result.issues:
            summary += f"\n🔍 Issues:\n"
            for issue in result.issues:
                icon = "❌" if issue.severity == ValidationSeverity.ERROR else "⚠️" if issue.severity == ValidationSeverity.WARNING else "ℹ️"
                summary += f"  {icon} Line {issue.line_number}: {issue.message}\n"
                if issue.suggestion:
                    summary += f"     💡 {issue.suggestion}\n"
        
        return summary