#!/usr/bin/env python3
"""
Command-line interface for the Excalidraw Parser library.

This module provides a simple CLI for parsing Excalidraw JSON files
and generating text descriptions from the command line.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from .parser import ExcalidrawParser
from .exceptions import ExcalidrawParserError


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Parse Excalidraw JSON files into text descriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  excalidraw-parser diagram.json
  excalidraw-parser diagram.json --output description.txt
  excalidraw-parser diagram.json --structured
  excalidraw-parser diagram.json --verbose
        """
    )
    
    parser.add_argument(
        "input_file",
        type=Path,
        help="Path to Excalidraw JSON file"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (default: stdout)"
    )
    
    parser.add_argument(
        "-s", "--structured",
        action="store_true",
        help="Output structured data instead of natural language description"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    return parser.parse_args()


def load_json_file(file_path: Path) -> dict:
    """Load and parse JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)


def format_structured_output(structure) -> str:
    """Format structured diagram data for output."""
    lines = []
    
    lines.append("=== Diagram Structure ===")
    lines.append("")
    
    # Components
    lines.append(f"Components ({len(structure.components)}):")
    if structure.components:
        for i, component in enumerate(structure.components, 1):
            label = component.label.text if component.label else "unlabeled"
            lines.append(f"  {i}. {component.shape.type} '{label}' at {component.position}")
    else:
        lines.append("  None")
    lines.append("")
    
    # Connections
    lines.append(f"Connections ({len(structure.connections)}):")
    if structure.connections:
        for i, connection in enumerate(structure.connections, 1):
            source_label = connection.source_component.label.text if connection.source_component.label else "unlabeled"
            target_label = connection.target_component.label.text if connection.target_component.label else "unlabeled"
            lines.append(f"  {i}. {source_label} -> {target_label} ({connection.direction})")
    else:
        lines.append("  None")
    lines.append("")
    
    # Standalone elements
    lines.append(f"Standalone Elements ({len(structure.standalone_elements)}):")
    if structure.standalone_elements:
        for i, element in enumerate(structure.standalone_elements, 1):
            element_info = f"{element.type} at ({element.x}, {element.y})"
            if hasattr(element, 'text') and element.text:
                element_info += f" - '{element.text}'"
            lines.append(f"  {i}. {element_info}")
    else:
        lines.append("  None")
    
    return "\n".join(lines)


def write_output(content: str, output_path: Optional[Path]) -> None:
    """Write content to file or stdout."""
    if output_path:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Output written to '{output_path}'")
        except Exception as e:
            print(f"Error writing to '{output_path}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(content)


def main() -> None:
    """Main CLI entry point."""
    args = parse_args()
    
    # Load input file
    json_data = load_json_file(args.input_file)
    
    # Create parser
    parser = ExcalidrawParser(enable_warnings=args.verbose)
    
    try:
        if args.structured:
            # Generate structured output
            structure = parser.parse_to_structure(json_data)
            output = format_structured_output(structure)
        else:
            # Generate natural language description
            output = parser.parse(json_data)
        
        # Write output
        write_output(output, args.output)
        
    except ExcalidrawParserError as e:
        print(f"Parser error: {e.message}", file=sys.stderr)
        if args.verbose and e.context:
            print(f"Context: {e.context}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()