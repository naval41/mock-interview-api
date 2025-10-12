"""
Main ExcalidrawParser interface for parsing Excalidraw JSON data.
"""

import json
import logging
from typing import Union, Dict, Any, List, Optional

from .models import DiagramStructure
from .factory import ElementFactory
from .analyzer import RelationshipAnalyzer
from .description_generator import DescriptionGenerator
from .output_generator import (
    OutputGenerator, OutputFormat, OutputConfig, OutputGenerationError,
    get_output_factory, register_output_generator
)
from .mermaid_generator import MermaidGenerator
from .exceptions import JSONParseError, ValidationError, ElementProcessingError


class ExcalidrawParser:
    """
    Main entry point for parsing Excalidraw JSON data into text descriptions.
    
    This class orchestrates the entire parsing pipeline, from JSON input validation
    through element creation, relationship analysis, and natural language generation.
    
    The parser handles various Excalidraw element types including rectangles, text,
    and arrows, and can identify relationships between elements to generate coherent
    descriptions of diagram structure and flow.
    
    Example:
        Basic usage:
        
        >>> parser = ExcalidrawParser()
        >>> description = parser.parse(excalidraw_json)
        >>> print(description)
        'The diagram contains a rectangle labeled "Google" and a rectangle labeled "Facebook". 
         "Google" connects to "Facebook".'
        
        Advanced usage with logging:
        
        >>> import logging
        >>> logger = logging.getLogger('my_app')
        >>> parser = ExcalidrawParser(logger=logger, enable_warnings=True)
        >>> structure = parser.parse_to_structure(excalidraw_json)
        >>> print(f"Found {len(structure.components)} components")
    
    Attributes:
        element_factory (ElementFactory): Factory for creating element objects from JSON
        relationship_analyzer (RelationshipAnalyzer): Analyzer for detecting element relationships
        description_generator (DescriptionGenerator): Generator for natural language descriptions
        logger (logging.Logger): Logger instance for debugging and warnings
        enable_warnings (bool): Whether to log warnings for non-critical issues
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None, enable_warnings: bool = True,
                 format_style: str = "standard", include_positions: bool = False,
                 max_connections_detail: int = 10):
        """
        Initialize the parser with all required components and configuration options.
        
        Creates instances of ElementFactory, RelationshipAnalyzer, and DescriptionGenerator
        to handle the parsing pipeline. Sets up logging configuration for debugging and
        warning messages.
        
        Args:
            logger (Optional[logging.Logger]): Custom logger instance for debugging and warnings.
                If None, a default logger will be created with appropriate formatting.
            enable_warnings (bool): Whether to log warnings for non-critical issues such as
                missing optional fields, unknown element types, or potential data inconsistencies.
                Defaults to True.
            format_style (str): Output format style - "standard", "detailed", "concise", or "technical".
                Defaults to "standard".
            include_positions (bool): Whether to include position information in descriptions.
                Defaults to False.
            max_connections_detail (int): Maximum number of connections to describe in detail
                before summarizing. Defaults to 10.
        
        Note:
            If no logger is provided, a default StreamHandler will be configured with
            WARNING level when enable_warnings is True, or ERROR level otherwise.
        """
        self.element_factory = ElementFactory()
        self.relationship_analyzer = RelationshipAnalyzer()
        self.description_generator = DescriptionGenerator(
            format_style=format_style,
            include_positions=include_positions,
            max_connections_detail=max_connections_detail
        )
        
        # Set up logging
        self.logger = logger or logging.getLogger(__name__)
        self.enable_warnings = enable_warnings
        
        # Configure default logging if no logger provided
        if logger is None and not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.WARNING if enable_warnings else logging.ERROR)
        
        # Set up output generators
        self._setup_output_generators()
    
    def _setup_output_generators(self):
        """Set up and register output generators."""
        factory = get_output_factory()
        
        # Register built-in generators
        if not factory.is_format_supported(OutputFormat.DESCRIPTION):
            register_output_generator(OutputFormat.DESCRIPTION, DescriptionGenerator)
        
        if not factory.is_format_supported(OutputFormat.MERMAID):
            register_output_generator(OutputFormat.MERMAID, MermaidGenerator)
    
    def parse(self, json_data: Union[str, Dict[str, Any]]) -> str:
        """
        Parse Excalidraw JSON data and return a natural language description.
        
        This is the main entry point for converting Excalidraw diagrams into human-readable
        text. The method handles the complete parsing pipeline: JSON validation, element
        creation, relationship analysis, and description generation.
        
        Args:
            json_data (Union[str, Dict[str, Any]]): Excalidraw data as either:
                - JSON string: Raw JSON export from Excalidraw
                - Dictionary: Pre-parsed JSON data
        
        Returns:
            str: Natural language description of the diagram structure, including:
                - Labeled components (shapes with text)
                - Connections between components (arrows)
                - Standalone elements (unconnected items)
        
        Raises:
            JSONParseError: If the input JSON string cannot be parsed or is malformed.
                Contains details about the parsing error location when available.
            ValidationError: If required fields are missing or have invalid values.
                Includes context about which field and element caused the validation failure.
            ElementProcessingError: If element creation or processing fails.
                Provides details about the problematic element and the specific error.
        
        Example:
            >>> parser = ExcalidrawParser()
            >>> json_str = '{"elements": [{"id": "1", "type": "rectangle", ...}]}'
            >>> description = parser.parse(json_str)
            >>> print(description)
            'The diagram contains a rectangle labeled "Example".'
        """
        # Parse to structured format first
        structure = self.parse_to_structure(json_data)
        
        # Generate natural language description
        return self.description_generator.generate_description(structure)
    
    def parse_to_structure(self, json_data: Union[str, Dict[str, Any]]) -> DiagramStructure:
        """
        Parse Excalidraw JSON data and return structured diagram representation.
        
        This method performs the same parsing as parse() but returns the structured
        data before natural language generation. Useful for applications that need
        programmatic access to diagram components and relationships.
        
        Args:
            json_data (Union[str, Dict[str, Any]]): Excalidraw data as either:
                - JSON string: Raw JSON export from Excalidraw
                - Dictionary: Pre-parsed JSON data
        
        Returns:
            DiagramStructure: Structured representation containing:
                - components (List[Component]): Shapes with their text labels
                - connections (List[Connection]): Arrow relationships between components
                - standalone_elements (List[BaseElement]): Unconnected elements
        
        Raises:
            JSONParseError: If the input JSON string cannot be parsed or is malformed.
            ValidationError: If required fields are missing or have invalid values.
            ElementProcessingError: If element creation or processing fails.
        
        Example:
            >>> parser = ExcalidrawParser()
            >>> structure = parser.parse_to_structure(json_data)
            >>> print(f"Found {len(structure.components)} components")
            >>> print(f"Found {len(structure.connections)} connections")
            >>> for component in structure.components:
            ...     label = component.label.text if component.label else "unlabeled"
            ...     print(f"Component: {label}")
        """
        # Validate and parse input JSON
        parsed_data = self._validate_input(json_data)
        
        # Extract elements array
        elements_data = self._extract_elements(parsed_data)
        
        # Create element objects using factory
        elements = self._create_elements(elements_data)
        
        # Analyze relationships between elements
        structure = self.relationship_analyzer.analyze_relationships(elements)
        
        return structure
    
    def parse_with_format(self, json_data: Union[str, Dict[str, Any]], 
                         output_format: str = "description",
                         format_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Parse Excalidraw JSON data and return output in the specified format.
        
        This method extends the basic parse() functionality to support multiple
        output formats including natural language descriptions and Mermaid diagrams.
        
        Args:
            json_data (Union[str, Dict[str, Any]]): Excalidraw data as JSON string or dictionary.
            output_format (str): Output format identifier (e.g., "natural_language", "mermaid").
            format_config (Optional[Dict[str, Any]]): Configuration options for the output format.
        
        Returns:
            str: Generated output in the specified format.
        
        Raises:
            ValueError: If the output format is not supported.
            JSONParseError: If the input JSON string cannot be parsed.
            ValidationError: If required fields are missing or have invalid values.
            ElementProcessingError: If element creation or processing fails.
        
        Example:
            >>> parser = ExcalidrawParser()
            >>> # Generate natural language description
            >>> description = parser.parse_with_format(json_data, "natural_language")
            >>> # Generate Mermaid flowchart
            >>> mermaid = parser.parse_with_format(json_data, "mermaid_flowchart")
        """
        # Parse to structured format first
        structure = self.parse_to_structure(json_data)
        
        # Handle natural language format with existing generator (for backward compatibility)
        if output_format == "description":
            return self.description_generator.generate_description(structure)
        
        # Create appropriate generator for other formats
        try:
            factory = get_output_factory()
            
            # Map string format to OutputFormat enum
            if output_format == "mermaid":
                format_enum = OutputFormat.MERMAID
            else:
                # Try to find matching format
                format_enum = None
                for fmt in OutputFormat:
                    if fmt.value == output_format:
                        format_enum = fmt
                        break
                
                if format_enum is None:
                    raise ValueError(f"Unknown output format: {output_format}")
            
            generator = factory.create_generator(format_enum, format_config)
            return generator.generate(structure)
        except ValueError as e:
            # Provide helpful error message with available formats
            available_formats = [fmt.value for fmt in OutputFormat]
            raise ValueError(f"Unsupported output format '{output_format}'. Available formats: {available_formats}") from e
    
    def parse_to_mermaid(self, json_data: Union[str, Dict[str, Any]], 
                        diagram_type: Optional[str] = None,
                        config: Optional[Dict[str, Any]] = None) -> str:
        """
        Parse Excalidraw JSON data and return Mermaid diagram syntax.
        
        This is a convenience method for generating Mermaid diagrams. It automatically
        detects the appropriate Mermaid diagram type unless explicitly specified.
        
        Args:
            json_data (Union[str, Dict[str, Any]]): Excalidraw data as JSON string or dictionary.
            diagram_type (Optional[str]): Specific Mermaid diagram type to use.
                Supported types: 'flowchart', 'graph'. If None, the type will be automatically detected.
            config (Optional[Dict[str, Any]]): Configuration options for Mermaid generation.
                Available options:
                - direction: Diagram direction ('TD', 'LR', 'BT', 'RL')
                - format_style: Output format style ('compact', 'readable', 'verbose')
                - auto_detect_type: Auto-detect diagram type (bool, default True)
                - include_styling: Include styling information (bool, default False)
        
        Returns:
            str: Mermaid diagram syntax ready for rendering.
        
        Raises:
            ValueError: If the specified diagram type is not supported.
            JSONParseError: If the input JSON string cannot be parsed.
            ValidationError: If required fields are missing or have invalid values.
            ElementProcessingError: If element creation or processing fails.
            OutputGenerationError: If Mermaid generation fails.
        
        Example:
            Basic usage:
            >>> parser = ExcalidrawParser()
            >>> mermaid = parser.parse_to_mermaid(json_data)
            >>> print(mermaid)
            flowchart TD
                A[Start] --> B[Process]
                B --> C[End]
            
            With custom configuration:
            >>> mermaid = parser.parse_to_mermaid(
            ...     json_data,
            ...     diagram_type='flowchart',
            ...     config={'direction': 'LR', 'format_style': 'compact'}
            ... )
        """
        # Parse to structured format first
        structure = self.parse_to_structure(json_data)
        
        # Determine diagram type if not specified
        if diagram_type is None:
            diagram_type = self._detect_mermaid_type(structure)
        
        # Validate diagram type
        supported_types = ['flowchart', 'graph']
        if diagram_type not in supported_types:
            raise ValueError(
                f"Unsupported Mermaid diagram type '{diagram_type}'. "
                f"Supported types: {supported_types}"
            )
        
        # Create Mermaid configuration
        mermaid_config = OutputConfig(
            custom_options={
                'mermaid': {
                    'diagram_type': diagram_type,
                    **(config or {})
                }
            }
        )
        
        # Generate Mermaid diagram
        mermaid_output = self.parse_with_format(json_data, "mermaid", mermaid_config)
        
        # Validate if requested in config
        if config and config.get('validate_syntax', False):
            validation_result = self.validate_mermaid_syntax(mermaid_output)
            if not validation_result.is_valid:
                self.logger.warning(f"Generated Mermaid has validation issues: {validation_result.errors_count} errors, {validation_result.warnings_count} warnings")
                if self.enable_warnings:
                    for issue in validation_result.issues:
                        self.logger.warning(f"Line {issue.line_number}: {issue.message}")
        
        return mermaid_output
    
    def validate_mermaid_syntax(self, mermaid_syntax: str, strict_mode: bool = False):
        """
        Validate Mermaid diagram syntax.
        
        This method provides comprehensive validation of Mermaid syntax, checking for
        syntax errors, node ID conflicts, invalid characters, and best practice violations.
        
        Args:
            mermaid_syntax (str): Mermaid diagram syntax to validate.
            strict_mode (bool): Whether to use strict validation rules. Defaults to False.
        
        Returns:
            ValidationResult: Comprehensive validation result with issues and statistics.
        
        Example:
            >>> parser = ExcalidrawParser()
            >>> mermaid = parser.parse_to_mermaid(json_data)
            >>> result = parser.validate_mermaid_syntax(mermaid)
            >>> if result.is_valid:
            ...     print("✅ Valid Mermaid syntax")
            ... else:
            ...     print(f"❌ {result.errors_count} errors found")
        """
        from .mermaid_validator import MermaidValidator
        
        validator = MermaidValidator(strict_mode=strict_mode)
        return validator.validate(mermaid_syntax)
    
    def parse_to_mermaid_with_validation(self, json_data: Union[str, Dict[str, Any]], 
                                       diagram_type: Optional[str] = None,
                                       config: Optional[Dict[str, Any]] = None,
                                       strict_validation: bool = False) -> tuple[str, 'ValidationResult']:
        """
        Parse Excalidraw JSON data to Mermaid with automatic validation.
        
        This method combines Mermaid generation with validation, returning both
        the generated Mermaid syntax and validation results.
        
        Args:
            json_data (Union[str, Dict[str, Any]]): Excalidraw data as JSON string or dictionary.
            diagram_type (Optional[str]): Specific Mermaid diagram type to use.
            config (Optional[Dict[str, Any]]): Configuration options for Mermaid generation.
            strict_validation (bool): Whether to use strict validation rules.
        
        Returns:
            tuple[str, ValidationResult]: Generated Mermaid syntax and validation result.
        
        Example:
            >>> parser = ExcalidrawParser()
            >>> mermaid, validation = parser.parse_to_mermaid_with_validation(json_data)
            >>> print(mermaid)
            >>> if not validation.is_valid:
            ...     print(f"Validation issues: {validation.errors_count} errors")
        """
        # Generate Mermaid
        mermaid_output = self.parse_to_mermaid(json_data, diagram_type, config)
        
        # Validate the output
        validation_result = self.validate_mermaid_syntax(mermaid_output, strict_validation)
        
        return mermaid_output, validation_result
    
    def get_supported_output_formats(self) -> List[str]:
        """
        Get a list of all supported output formats.
        
        Returns:
            List[str]: List of supported output format identifiers.
        
        Example:
            >>> parser = ExcalidrawParser()
            >>> formats = parser.get_supported_output_formats()
            >>> print(formats)
            ['natural_language', 'mermaid_flowchart', 'mermaid_graph']
        """
        factory = get_output_factory()
        format_enums = factory.get_supported_formats()
        formats = [fmt.value for fmt in format_enums]
        
        # Always include natural language as it's built-in
        if "description" not in formats:
            formats.insert(0, "description")
        
        return formats
    
    def _detect_mermaid_type(self, structure: DiagramStructure) -> str:
        """
        Automatically detect the most appropriate Mermaid diagram type.
        
        This method analyzes the diagram structure to determine which Mermaid
        diagram type would best represent the content.
        
        Args:
            structure (DiagramStructure): Parsed diagram structure.
        
        Returns:
            str: Recommended Mermaid diagram type identifier ('flowchart' or 'graph').
        """
        # Simple heuristics for diagram type detection
        # Enhanced from Task 12 implementation
        
        num_components = len(structure.components)
        num_connections = len(structure.connections)
        
        if num_components == 0:
            # No components, default to flowchart
            return 'flowchart'
        
        if num_connections == 0:
            # No connections, could be a simple list or mind map
            if num_components <= 3:
                return 'flowchart'
            else:
                return 'graph'
        
        # Analyze connection patterns
        connection_ratio = num_connections / num_components if num_components > 0 else 0
        
        # Check for bidirectional connections (suggests graph)
        bidirectional_count = 0
        for connection in structure.connections:
            # Look for reverse connections
            for other_connection in structure.connections:
                if (connection.source_component == other_connection.target_component and
                    connection.target_component == other_connection.source_component):
                    bidirectional_count += 1
                    break
        
        bidirectional_ratio = bidirectional_count / num_connections if num_connections > 0 else 0
        
        # Decision logic
        if connection_ratio > 1.5 or bidirectional_ratio > 0.3:
            # High connectivity or many bidirectional connections suggests a graph/network
            return 'graph'
        else:
            # Lower connectivity suggests a flowchart
            return 'flowchart'
    
    def _validate_input(self, json_data: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate and parse input JSON data with comprehensive validation.
        
        Args:
            json_data: JSON string or dictionary
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            JSONParseError: If JSON parsing fails
            ValidationError: If input validation fails
        """
        self.logger.debug("Starting input validation")
        
        # Handle None input
        if json_data is None:
            raise ValidationError("Input cannot be None")
        
        # Handle string input by parsing JSON
        if isinstance(json_data, str):
            if not json_data.strip():
                raise ValidationError("Input JSON string cannot be empty")
            
            # Log large JSON strings
            if len(json_data) > 10000:
                self.logger.debug(f"Processing large JSON string ({len(json_data)} characters)")
            
            try:
                parsed_data = json.loads(json_data)
                self.logger.debug("Successfully parsed JSON string")
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON parsing failed at line {getattr(e, 'lineno', 'unknown')}: {str(e)}")
                raise JSONParseError(
                    f"Failed to parse JSON: {str(e)}",
                    json_content=json_data,
                    line_number=getattr(e, 'lineno', None)
                )
        elif isinstance(json_data, dict):
            parsed_data = json_data
            self.logger.debug("Input is already a dictionary")
        else:
            self.logger.error(f"Invalid input type: {type(json_data).__name__}")
            raise ValidationError(
                f"Input must be a JSON string or dictionary, got {type(json_data).__name__}",
                field_value=type(json_data).__name__
            )
        
        # Validate that it's a dictionary
        if not isinstance(parsed_data, dict):
            self.logger.error(f"Parsed JSON is not a dictionary: {type(parsed_data).__name__}")
            raise ValidationError(
                "Parsed JSON must be a dictionary/object",
                field_value=type(parsed_data).__name__
            )
        
        # Validate basic Excalidraw structure
        self._validate_excalidraw_structure(parsed_data)
        
        self.logger.debug("Input validation completed successfully")
        return parsed_data
    
    def _validate_excalidraw_structure(self, data: Dict[str, Any]) -> None:
        """
        Validate basic Excalidraw JSON structure and warn about potential issues.
        
        Args:
            data: Parsed Excalidraw JSON dictionary
            
        Raises:
            ValidationError: If critical structure issues are found
        """
        # Check for common Excalidraw fields and warn if missing
        expected_fields = ['elements', 'appState', 'files']
        missing_fields = [field for field in expected_fields if field not in data]
        
        if missing_fields and self.enable_warnings:
            self.logger.warning(f"Missing common Excalidraw fields: {missing_fields}")
        
        # Check version information
        if 'version' in data:
            version = data['version']
            if isinstance(version, (int, float)) and version < 2:
                if self.enable_warnings:
                    self.logger.warning(f"Old Excalidraw version detected: {version}")
        elif self.enable_warnings:
            self.logger.warning("No version information found in Excalidraw data")
        
        # Check for source information
        if 'source' in data and self.enable_warnings:
            source = data['source']
            if source != 'excalidraw':
                self.logger.warning(f"Unexpected source: {source}")
        
        # Validate elements array exists (this is critical)
        if 'elements' not in data:
            self.logger.error("Missing required 'elements' field")
            raise ValidationError(
                "Excalidraw JSON must contain an 'elements' array",
                field_name='elements'
            )
        
        elements = data['elements']
        if not isinstance(elements, list):
            self.logger.error(f"Elements field is not an array: {type(elements).__name__}")
            raise ValidationError(
                "Elements field must be an array",
                field_name='elements',
                field_value=type(elements).__name__
            )
        
        # Log statistics about elements
        if elements:
            element_types = {}
            for element in elements:
                if isinstance(element, dict) and 'type' in element:
                    element_type = element['type']
                    element_types[element_type] = element_types.get(element_type, 0) + 1
            
            self.logger.debug(f"Found {len(elements)} elements: {element_types}")
        else:
            if self.enable_warnings:
                self.logger.warning("Elements array is empty")
    
    def _extract_elements(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract elements array from Excalidraw JSON data.
        
        Args:
            data: Parsed Excalidraw JSON dictionary
            
        Returns:
            List of element dictionaries
            
        Raises:
            ValidationError: If elements array is missing or invalid
        """
        if 'elements' not in data:
            raise ValidationError(
                "Excalidraw JSON must contain an 'elements' array",
                field_name='elements'
            )
        
        elements = data['elements']
        
        if not isinstance(elements, list):
            raise ValidationError(
                "Elements field must be an array",
                field_name='elements',
                field_value=type(elements).__name__
            )
        
        return elements
    
    def _create_elements(self, elements_data: List[Dict[str, Any]]) -> List:
        """
        Create element objects from JSON data using the factory with comprehensive error handling.
        
        Args:
            elements_data: List of element dictionaries
            
        Returns:
            List of BaseElement objects
            
        Raises:
            ElementProcessingError: If element creation fails
        """
        elements = []
        skipped_elements = 0
        unknown_types = set()
        
        total_elements = len(elements_data)
        self.logger.debug(f"Processing {total_elements} elements")
        
        # Performance optimization: batch process elements for large diagrams
        if total_elements == 0:
            self.logger.debug("No elements to process")
            return elements
        
        batch_size = 1000 if total_elements > 5000 else total_elements
        
        for batch_start in range(0, total_elements, batch_size):
            batch_end = min(batch_start + batch_size, total_elements)
            batch_elements = elements_data[batch_start:batch_end]
            
            if total_elements > 1000:
                self.logger.debug(f"Processing batch {batch_start//batch_size + 1}/{(total_elements + batch_size - 1)//batch_size}")
            
            for i, element_data in enumerate(batch_elements):
                actual_index = batch_start + i
                # Initialize variables for error handling
                element_id = f'index_{actual_index}'
                element_type = 'unknown'
                
                try:
                    # Validate element data structure first
                    if not isinstance(element_data, dict):
                        self.logger.error(f"Element at index {actual_index} is not a dictionary: {type(element_data)}")
                        raise ElementProcessingError(
                            f"Element at index {actual_index} must be a dictionary, got {type(element_data).__name__}",
                            element_id=element_id,
                            element_type=element_type,
                            element_data=element_data
                        )
                    
                    element_id = element_data.get('id', f'index_{actual_index}')
                    element_type = element_data.get('type', 'unknown')
                    
                    # Check for required fields
                    if 'id' not in element_data:
                        if self.enable_warnings:
                            self.logger.warning(f"Element at index {actual_index} missing ID, using index as fallback")
                        element_data = dict(element_data)  # Create copy to avoid modifying original
                        element_data['id'] = f'element_{actual_index}'
                    
                    if 'type' not in element_data:
                        self.logger.error(f"Element at index {actual_index} missing required 'type' field")
                        raise ElementProcessingError(
                            f"Element at index {actual_index} missing required 'type' field",
                            element_id=element_id,
                            element_data=element_data
                        )
                    
                    # Create element using factory
                    element = self.element_factory.create_element(element_data)
                    elements.append(element)
                    
                    # Track unknown element types for logging (limit logging for performance)
                    if element_type not in ['rectangle', 'text', 'arrow'] and element_type not in unknown_types:
                        unknown_types.add(element_type)
                        if self.enable_warnings and len(unknown_types) <= 10:  # Limit warning spam
                            self.logger.warning(f"Processing unknown element type '{element_type}' as BaseElement")
                    
                    # Reduce debug logging for large diagrams
                    if total_elements <= 100:
                        self.logger.debug(f"Successfully processed {element_type} element: {element_id}")
                    
                except (ValidationError, ElementProcessingError) as e:
                    self.logger.error(f"Failed to process element at index {actual_index} (ID: {element_id}, Type: {element_type}): {e.message}")
                    # Re-raise with additional context about array position
                    raise ElementProcessingError(
                        f"Failed to process element at index {actual_index}: {e.message}",
                        element_id=element_id,
                        element_type=element_type,
                        element_data=element_data
                    )
                except Exception as e:
                    self.logger.error(f"Unexpected error processing element at index {actual_index} (ID: {element_id}, Type: {element_type}): {str(e)}")
                    # Catch any unexpected errors and wrap them
                    raise ElementProcessingError(
                        f"Unexpected error processing element at index {actual_index}: {str(e)}",
                        element_id=element_id,
                        element_type=element_type,
                        element_data=element_data
                    )
        
        # Log summary statistics
        if unknown_types and self.enable_warnings:
            if len(unknown_types) <= 10:
                self.logger.warning(f"Processed {len(unknown_types)} unknown element types: {sorted(unknown_types)}")
            else:
                self.logger.warning(f"Processed {len(unknown_types)} unknown element types (showing first 10): {sorted(list(unknown_types)[:10])}")
        
        self.logger.debug(f"Successfully processed {len(elements)} elements")
        return elements