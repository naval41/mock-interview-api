"""
Simple interview pipeline implementation.
"""

from typing import List, Any, Dict
import structlog

logger = structlog.get_logger()


class InterviewPipeline:
    """Simple interview pipeline for managing interview flow."""
    
    def __init__(self, components: List[Any] = None):
        self.components = components or []
        self.is_running = False
        self.current_phase = "initialization"
        
    def add_component(self, component: Any):
        """Add a component to the pipeline."""
        self.components.append(component)
        logger.info(f"Added component: {component.__class__.__name__}")
        
    def remove_component(self, component: Any) -> bool:
        """Remove a component from the pipeline.
        
        Args:
            component: Component to remove
            
        Returns:
            True if component was removed, False if not found
        """
        try:
            # Find component by type and name if possible
            for i, comp in enumerate(self.components):
                if (comp is component or 
                    (hasattr(comp, 'name') and hasattr(component, 'name') and 
                     comp.name == component.name and comp.__class__ == component.__class__)):
                    removed = self.components.pop(i)
                    logger.info(f"Removed component: {removed.__class__.__name__}")
                    return True
            
            logger.warning(f"Component not found in pipeline: {component.__class__.__name__}")
            return False
        except Exception as e:
            logger.error(f"Failed to remove component: {e}")
            return False
            
    def replace_component(self, old_component: Any, new_component: Any) -> bool:
        """Replace an old component with a new one.
        
        Args:
            old_component: Component to replace
            new_component: New component to add
            
        Returns:
            True if replacement successful, False otherwise
        """
        try:
            if self.remove_component(old_component):
                self.add_component(new_component)
                logger.info(f"Replaced component: {old_component.__class__.__name__} with {new_component.__class__.__name__}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to replace component: {e}")
            return False
        
    def start(self):
        """Start the pipeline."""
        self.is_running = True
        self.current_phase = "running"
        logger.info("Pipeline started")
        
    def stop(self):
        """Stop the pipeline."""
        self.is_running = False
        self.current_phase = "stopped"
        logger.info("Pipeline stopped")
        
    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        return {
            "running": self.is_running,
            "phase": self.current_phase,
            "components": len(self.components),
            "component_types": [comp.__class__.__name__ for comp in self.components]
        }
