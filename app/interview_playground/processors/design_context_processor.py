"""
Design Context Processor implementation that extends BaseProcessor.
"""

from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.processors.frameworks.rtvi import RTVIClientMessageFrame
from app.interview_playground.processors.base_processor import BaseProcessor
from app.interview_playground.utility_functions import parse_design_diagrams
from app.models.enums import ToolEvent
import structlog

logger = structlog.get_logger()

class DesignContextProcessor(BaseProcessor):
    """Design Context Processor for handling design-related messages and context."""
    
    def __init__(self, max_design_elements: int = 15, design_patterns: bool = True):
        """Initialize Design Context Processor.
        
        Args:
            max_design_elements: Maximum number of design elements to keep in context
            design_patterns: Whether to detect design patterns
        """
        super().__init__(name="design_context_processor")
        self.max_design_elements = max_design_elements
        self.design_patterns = design_patterns
        self.design_elements = []
        self.design_context = {}
        
    # Remove the setup_processor method - it's no longer needed
    
    async def process_custom_frame(self, frame: Frame, direction: FrameDirection):
        """Process frames after StartFrame validation."""
        if isinstance(frame, RTVIClientMessageFrame) and frame.type == ToolEvent.DESIGN_CONTENT:
            logger.info("RTVI Design frame Content", frame=frame)
            self._process_design_content(frame)
        else:
            # Continue processing the frame
            await self.push_frame(frame, direction)

    
    def _process_design_content(self, frame: RTVIClientMessageFrame):
        """Process design content using the parse_design_diagrams utility."""
        logger.info("Processing design content", frame=frame)
        data = frame.data or {}
        content = data.get("content", "")
        logger.info("Design content", content=content)
        
        # Parse the design diagram using utility function
        try:
            parsed_result = parse_design_diagrams(content, validate=True)
            
            if parsed_result["is_valid"]:
                logger.info("Design diagram parsed successfully",
                           diagram_type=parsed_result["diagram_type"],
                           element_count=parsed_result["element_count"])
                
                # Process the extracted elements
                for element in parsed_result["elements"]:
                    self._add_design_element(
                        [element["name"]], 
                        parsed_result["diagram_type"]
                    )
                
                # Store parsed diagram info
                self.design_context[frame.id if hasattr(frame, 'id') else 'unknown'] = {
                    "diagram_type": parsed_result["diagram_type"],
                    "element_count": parsed_result["element_count"],
                    "elements": parsed_result["elements"]
                }
            else:
                logger.warning("Design diagram validation failed",
                             issues=parsed_result["issues"])
                
        except Exception as e:
            logger.error("Failed to parse design diagram", error=str(e))
        
        
    def _extract_design_elements(self, message: str) -> list:
        """Extract design elements from a message.
        
        Args:
            message: Message to extract design elements from
            
        Returns:
            List of design elements found
        """
        # Simple design element detection - look for common patterns
        design_patterns = [
            "UI/UX", "user interface", "user experience", "wireframe", "mockup",
            "prototype", "design system", "component", "layout", "typography",
            "color scheme", "visual hierarchy", "information architecture",
            "user flow", "interaction design", "responsive design", "accessibility",
            "usability", "user research", "persona", "user journey", "storyboard"
        ]
        
        design_elements = []
        message_lower = message.lower()
        
        for pattern in design_patterns:
            if pattern in message_lower:
                design_elements.append(pattern)
                
        return design_elements
        
    def _detect_design_type(self, message: str) -> str:
        """Detect design type from message.
        
        Args:
            message: Message to analyze
            
        Returns:
            Detected design type
        """
        # Simple design type detection based on keywords
        design_types = {
            "ui_ux": ["ui", "ux", "user interface", "user experience", "wireframe", "mockup"],
            "interaction": ["interaction", "user flow", "user journey", "storyboard", "prototype"],
            "visual": ["visual", "typography", "color", "layout", "hierarchy", "design system"],
            "research": ["research", "persona", "usability", "user research", "testing"],
            "accessibility": ["accessibility", "a11y", "inclusive", "universal design"],
            "responsive": ["responsive", "mobile", "adaptive", "flexible layout"]
        }
        
        message_lower = message.lower()
        
        for design_type, keywords in design_types.items():
            if any(keyword in message_lower for keyword in keywords):
                return design_type
                
        return "general"
        
    def _add_design_element(self, design_elements: list, design_type: str):
        """Add design elements to context.
        
        Args:
            design_elements: List of design elements to add
            design_type: Type of design elements
        """
        for element in design_elements:
            self.design_elements.append({
                "element": element,
                "type": design_type,
                "timestamp": "now"  # In real implementation, use actual timestamp
            })
            
        # Keep only the last max_design_elements
        if len(self.design_elements) > self.max_design_elements:
            self.design_elements = self.design_elements[-self.max_design_elements:]
            
    def get_design_context(self) -> list:
        """Get the current design context.
        
        Returns:
            List of design elements in context
        """
        return self.design_elements.copy()
        
    def clear_design_context(self):
        """Clear all design elements from context."""
        self.design_elements.clear()
        
    def get_design_patterns(self) -> dict:
        """Get detected design patterns.
        
        Returns:
            Dictionary of design patterns by type
        """
        patterns = {}
        for element in self.design_elements:
            design_type = element["type"]
            if design_type not in patterns:
                patterns[design_type] = []
            patterns[design_type].append(element["element"])
            
        return patterns
        
    def get_status(self) -> dict:
        """Get the current status of the design context processor.
        
        Returns:
            Dictionary containing design context processor status
        """
        return {
            "type": "design_context",
            "design_elements_count": len(self.design_elements),
            "max_design_elements": self.max_design_elements,
            "design_patterns": self.design_patterns,
            "design_types_found": list(set(element["type"] for element in self.design_elements))
        }
