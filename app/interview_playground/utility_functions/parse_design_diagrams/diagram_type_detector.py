"""
Diagram type detection for Mermaid output generation.
"""

from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from .models import DiagramStructure, Component, Connection


class DiagramType(Enum):
    """Enumeration of supported Mermaid diagram types."""
    FLOWCHART = "flowchart"
    GRAPH = "graph"
    MINDMAP = "mindmap"
    UNKNOWN = "unknown"


class DiagramTypeDetector:
    """
    Detects the most appropriate Mermaid diagram type based on diagram structure.
    
    This class analyzes the structure of an Excalidraw diagram to determine which
    Mermaid diagram type would best represent the content. It uses heuristics based
    on connection patterns, node relationships, and structural characteristics.
    
    Supported diagram types:
    - Flowchart: Linear flows with decision points and sequential processes
    - Graph: Network topologies with bidirectional or complex connections
    - Mind map: Central node with hierarchical branching structure
    
    The detector can be configured to override automatic detection when needed.
    
    Example:
        >>> detector = DiagramTypeDetector()
        >>> diagram_type = detector.detect_diagram_type(diagram_structure)
        >>> print(f"Detected diagram type: {diagram_type.value}")
        
        >>> # Override automatic detection
        >>> detector = DiagramTypeDetector(override_type=DiagramType.FLOWCHART)
        >>> diagram_type = detector.detect_diagram_type(diagram_structure)
        >>> print(f"Using override: {diagram_type.value}")
    """
    
    def __init__(self, override_type: Optional[DiagramType] = None):
        """
        Initialize the diagram type detector.
        
        Args:
            override_type (Optional[DiagramType]): If provided, always return this
                type instead of performing automatic detection. Useful for forcing
                a specific output format.
        """
        self.override_type = override_type
    
    def detect_diagram_type(self, structure: DiagramStructure) -> DiagramType:
        """
        Detect the most appropriate Mermaid diagram type for the given structure.
        
        This method analyzes the diagram structure using various heuristics to
        determine which Mermaid diagram type would best represent the content.
        
        Detection priority:
        1. If override_type is set, return that type
        2. Check for mind map characteristics (central node with branches)
        3. Check for flowchart characteristics (linear flows, decision points)
        4. Check for graph characteristics (network topology, bidirectional connections)
        5. Default to flowchart for simple structures
        
        Args:
            structure (DiagramStructure): The analyzed diagram structure containing
                components, connections, and standalone elements.
        
        Returns:
            DiagramType: The detected diagram type enum value.
        
        Example:
            >>> structure = DiagramStructure(components=[...], connections=[...])
            >>> detector = DiagramTypeDetector()
            >>> diagram_type = detector.detect_diagram_type(structure)
            >>> if diagram_type == DiagramType.FLOWCHART:
            ...     print("This is a process flow diagram")
        """
        # Return override type if specified
        if self.override_type:
            return self.override_type
        
        # If no components, return unknown
        if not structure.components:
            return DiagramType.UNKNOWN
        
        # Calculate detection scores for each type
        mindmap_score = self._calculate_mindmap_score(structure)
        flowchart_score = self._calculate_flowchart_score(structure)
        graph_score = self._calculate_graph_score(structure)
        
        # Determine the best match based on scores
        scores = {
            DiagramType.MINDMAP: mindmap_score,
            DiagramType.FLOWCHART: flowchart_score,
            DiagramType.GRAPH: graph_score
        }
        
        # Find the type with the highest score
        best_type = max(scores.keys(), key=lambda k: scores[k])
        
        # If all scores are very low, default to flowchart
        if scores[best_type] < 0.2:
            return DiagramType.FLOWCHART
        
        return best_type
    
    def _calculate_mindmap_score(self, structure: DiagramStructure) -> float:
        """
        Calculate how well the structure matches a mind map pattern.
        
        Mind map characteristics:
        - One central node with multiple branches
        - Hierarchical structure (tree-like)
        - Mostly outward connections from center
        - Limited cross-connections between branches
        
        Args:
            structure: The diagram structure to analyze
            
        Returns:
            float: Score between 0.0 and 1.0 indicating mind map likelihood
        """
        if len(structure.components) < 3 or not structure.connections:
            return 0.0
        
        score = 0.0
        
        # Find potential central nodes (nodes with many connections)
        connection_counts = self._get_connection_counts(structure)
        
        if not connection_counts:
            return 0.0
        
        # Check for a dominant central node
        max_connections = max(connection_counts.values())
        central_candidate_ids = [comp_id for comp_id, count in connection_counts.items() 
                               if count == max_connections]
        
        # Mind maps typically have one clear central node
        if len(central_candidate_ids) == 1 and max_connections >= len(structure.components) * 0.3:
            score += 0.4
            
            central_node_id = central_candidate_ids[0]
            central_node = next(comp for comp in structure.components if comp.shape.id == central_node_id)
            
            # Check for hierarchical branching pattern
            if self._has_hierarchical_structure(structure, central_node):
                score += 0.3
            
            # Check for limited cross-connections (branches don't connect to each other much)
            cross_connection_ratio = self._calculate_cross_connection_ratio(structure, central_node)
            if cross_connection_ratio < 0.3:  # Less than 30% cross-connections
                score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_flowchart_score(self, structure: DiagramStructure) -> float:
        """
        Calculate how well the structure matches a flowchart pattern.
        
        Flowchart characteristics:
        - Linear or branching flow with clear start/end points
        - Sequential processes with decision points
        - Mostly unidirectional connections
        - Clear flow direction (top-to-bottom or left-to-right)
        
        Args:
            structure: The diagram structure to analyze
            
        Returns:
            float: Score between 0.0 and 1.0 indicating flowchart likelihood
        """
        if not structure.connections:
            return 0.0
        
        score = 0.0
        
        # Check for clear start and end nodes
        start_end_score = self._calculate_start_end_score(structure)
        score += start_end_score * 0.3
        
        # Check for linear flow characteristics
        linear_flow_score = self._calculate_linear_flow_score(structure)
        score += linear_flow_score * 0.3
        
        # Check for consistent flow direction
        direction_consistency_score = self._calculate_direction_consistency_score(structure)
        score += direction_consistency_score * 0.2
        
        # Check for decision point patterns (nodes with multiple outgoing connections)
        decision_point_score = self._calculate_decision_point_score(structure)
        score += decision_point_score * 0.2
        
        return min(score, 1.0)
    
    def _calculate_graph_score(self, structure: DiagramStructure) -> float:
        """
        Calculate how well the structure matches a graph/network pattern.
        
        Graph characteristics:
        - Network topology with interconnected nodes
        - Bidirectional or complex connection patterns
        - No clear hierarchical structure
        - Multiple connection paths between nodes
        
        Args:
            structure: The diagram structure to analyze
            
        Returns:
            float: Score between 0.0 and 1.0 indicating graph likelihood
        """
        if not structure.connections:
            return 0.0
        
        score = 0.0
        
        # Check for bidirectional connections
        bidirectional_score = self._calculate_bidirectional_score(structure)
        score += bidirectional_score * 0.3
        
        # Check for network density (how interconnected the nodes are)
        density_score = self._calculate_network_density_score(structure)
        score += density_score * 0.3
        
        # Check for multiple paths between nodes
        multiple_paths_score = self._calculate_multiple_paths_score(structure)
        score += multiple_paths_score * 0.2
        
        # Check for lack of clear hierarchy (more distributed structure)
        non_hierarchical_score = self._calculate_non_hierarchical_score(structure)
        score += non_hierarchical_score * 0.2
        
        return min(score, 1.0)
    
    def _get_connection_counts(self, structure: DiagramStructure) -> Dict[str, int]:
        """Get the number of connections for each component."""
        counts = {comp.shape.id: 0 for comp in structure.components}
        
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            if source_id in counts:
                counts[source_id] += 1
            if target_id in counts:
                counts[target_id] += 1
        
        return counts
    
    def _has_hierarchical_structure(self, structure: DiagramStructure, central_node: Component) -> bool:
        """Check if the structure has a hierarchical branching pattern from the central node."""
        # Build adjacency list using component IDs
        adjacency = {comp.shape.id: [] for comp in structure.components}
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            adjacency[source_id].append(target_id)
            adjacency[target_id].append(source_id)
        
        # Check if we can traverse the structure in a tree-like manner from central node
        visited = set()
        
        def dfs(node_id: str, parent_id: Optional[str] = None) -> bool:
            if node_id in visited:
                return False  # Cycle detected, not hierarchical
            
            visited.add(node_id)
            
            for neighbor_id in adjacency[node_id]:
                if neighbor_id != parent_id:  # Don't go back to parent
                    if not dfs(neighbor_id, node_id):
                        return False
            
            return True
        
        # Start DFS from central node
        is_hierarchical = dfs(central_node.shape.id)
        
        # Check if we visited all connected components
        connected_components = len([comp_id for comp_id in adjacency.keys() 
                                  if len(adjacency[comp_id]) > 0])
        
        return is_hierarchical and len(visited) >= connected_components * 0.8
    
    def _calculate_cross_connection_ratio(self, structure: DiagramStructure, central_node: Component) -> float:
        """Calculate the ratio of connections that don't involve the central node."""
        if not structure.connections:
            return 0.0
        
        cross_connections = 0
        for connection in structure.connections:
            if (connection.source_component != central_node and 
                connection.target_component != central_node):
                cross_connections += 1
        
        return cross_connections / len(structure.connections)
    
    def _calculate_start_end_score(self, structure: DiagramStructure) -> float:
        """Calculate score based on presence of clear start and end nodes."""
        if not structure.connections:
            return 0.0
        
        # Count incoming and outgoing connections for each component
        incoming = {comp.shape.id: 0 for comp in structure.components}
        outgoing = {comp.shape.id: 0 for comp in structure.components}
        
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            outgoing[source_id] += 1
            incoming[target_id] += 1
        
        # Find start nodes (no incoming connections) and end nodes (no outgoing connections)
        start_nodes = [comp_id for comp_id in incoming.keys() if incoming[comp_id] == 0 and outgoing[comp_id] > 0]
        end_nodes = [comp_id for comp_id in outgoing.keys() if outgoing[comp_id] == 0 and incoming[comp_id] > 0]
        
        # Score based on having clear start and end points
        score = 0.0
        if start_nodes:
            score += 0.5
        if end_nodes:
            score += 0.5
        
        return score
    
    def _calculate_linear_flow_score(self, structure: DiagramStructure) -> float:
        """Calculate score based on linear flow characteristics."""
        if not structure.connections:
            return 0.0
        
        # Count components with exactly one incoming and one outgoing connection
        incoming = {comp.shape.id: 0 for comp in structure.components}
        outgoing = {comp.shape.id: 0 for comp in structure.components}
        
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            outgoing[source_id] += 1
            incoming[target_id] += 1
        
        # Count truly linear nodes (exactly 1 in + 1 out) and start/end nodes
        linear_nodes = 0
        start_end_nodes = 0
        
        for comp in structure.components:
            comp_id = comp.shape.id
            in_count = incoming[comp_id]
            out_count = outgoing[comp_id]
            
            # Truly linear nodes have exactly 1 in and 1 out
            if in_count == 1 and out_count == 1:
                linear_nodes += 1
            # Start/end nodes have either only incoming or only outgoing
            elif (in_count == 0 and out_count > 0) or (out_count == 0 and in_count > 0):
                start_end_nodes += 1
        
        # Penalize structures with too many branching nodes (high out-degree)
        branching_penalty = 0
        for comp_id in outgoing:
            if outgoing[comp_id] > 2:  # More than 2 outgoing connections
                branching_penalty += 0.1
        
        total_score = (linear_nodes + start_end_nodes * 0.5) / len(structure.components)
        return max(0.0, total_score - branching_penalty)
    
    def _calculate_direction_consistency_score(self, structure: DiagramStructure) -> float:
        """Calculate score based on consistent flow direction."""
        if not structure.connections:
            return 0.0
        
        # Count connections by direction
        direction_counts = {}
        for connection in structure.connections:
            direction = connection.direction
            direction_counts[direction] = direction_counts.get(direction, 0) + 1
        
        if not direction_counts:
            return 0.0
        
        # Calculate consistency (dominant direction ratio)
        total_connections = sum(direction_counts.values())
        max_direction_count = max(direction_counts.values())
        
        return max_direction_count / total_connections
    
    def _calculate_decision_point_score(self, structure: DiagramStructure) -> float:
        """Calculate score based on decision point patterns."""
        if not structure.connections:
            return 0.0
        
        # Count outgoing connections for each component
        outgoing = {comp.shape.id: 0 for comp in structure.components}
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            outgoing[source_id] += 1
        
        # Count decision points (nodes with multiple outgoing connections)
        decision_points = sum(1 for count in outgoing.values() if count > 1)
        high_branching_nodes = sum(1 for count in outgoing.values() if count > 3)
        
        # Score based on reasonable number of decision points for flowcharts
        if len(structure.components) > 0:
            decision_ratio = decision_points / len(structure.components)
            # Optimal ratio is around 0.1-0.3 for flowcharts
            if 0.1 <= decision_ratio <= 0.3:
                score = 1.0
            elif decision_ratio < 0.1:
                score = decision_ratio / 0.1
            else:
                score = max(0.0, 1.0 - (decision_ratio - 0.3) / 0.3)
            
            # Heavy penalty for nodes with too many outgoing connections (like mind map centers)
            if high_branching_nodes > 0:
                score *= 0.1  # Severe penalty
            
            return score
        
        return 0.0
    
    def _calculate_bidirectional_score(self, structure: DiagramStructure) -> float:
        """Calculate score based on bidirectional connections."""
        if not structure.connections:
            return 0.0
        
        # Look for pairs of connections that go both ways between the same components
        connection_pairs = set()
        for connection in structure.connections:
            pair = tuple(sorted([connection.source_component.shape.id, 
                               connection.target_component.shape.id]))
            connection_pairs.add(pair)
        
        # Count actual connections vs unique pairs
        unique_pairs = len(connection_pairs)
        total_connections = len(structure.connections)
        
        if unique_pairs == 0:
            return 0.0
        
        # Higher score if there are more connections than unique pairs (bidirectional)
        bidirectional_ratio = (total_connections - unique_pairs) / unique_pairs
        return min(bidirectional_ratio, 1.0)
    
    def _calculate_network_density_score(self, structure: DiagramStructure) -> float:
        """Calculate network density score."""
        if len(structure.components) < 2:
            return 0.0
        
        # Calculate actual vs maximum possible connections
        num_components = len(structure.components)
        max_connections = num_components * (num_components - 1) / 2  # Undirected graph
        actual_connections = len(structure.connections)
        
        density = actual_connections / max_connections if max_connections > 0 else 0.0
        
        # Optimal density for graphs is moderate (0.2-0.6)
        if 0.2 <= density <= 0.6:
            return 1.0
        elif density < 0.2:
            return density / 0.2
        else:
            return max(0.0, 1.0 - (density - 0.6) / 0.4)
    
    def _calculate_multiple_paths_score(self, structure: DiagramStructure) -> float:
        """Calculate score based on multiple paths between nodes."""
        if len(structure.components) < 3:
            return 0.0
        
        # Build adjacency list using component IDs
        adjacency = {comp.shape.id: [] for comp in structure.components}
        for connection in structure.connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            adjacency[source_id].append(target_id)
            adjacency[target_id].append(source_id)
        
        # Count component pairs with multiple paths
        multiple_path_pairs = 0
        total_pairs = 0
        
        component_ids = [comp.shape.id for comp in structure.components]
        for i in range(len(component_ids)):
            for j in range(i + 1, len(component_ids)):
                total_pairs += 1
                if self._has_multiple_paths(adjacency, component_ids[i], component_ids[j]):
                    multiple_path_pairs += 1
        
        return multiple_path_pairs / total_pairs if total_pairs > 0 else 0.0
    
    def _has_multiple_paths(self, adjacency: Dict[str, List[str]], 
                           start: str, end: str) -> bool:
        """Check if there are multiple paths between two components."""
        # Simple check: if removing any intermediate node still leaves a path
        # This is a simplified heuristic for multiple paths
        
        def has_path(adj: Dict[str, List[str]], 
                    source: str, target: str, 
                    excluded: Set[str] = None) -> bool:
            if excluded is None:
                excluded = set()
            
            if source == target:
                return True
            
            visited = set()
            stack = [source]
            
            while stack:
                current = stack.pop()
                if current in visited or current in excluded:
                    continue
                
                visited.add(current)
                
                for neighbor in adj.get(current, []):
                    if neighbor == target:
                        return True
                    if neighbor not in visited and neighbor not in excluded:
                        stack.append(neighbor)
            
            return False
        
        # Check if there's at least one path
        if not has_path(adjacency, start, end):
            return False
        
        # Check if removing intermediate nodes still leaves paths
        intermediate_nodes = [comp_id for comp_id in adjacency.keys() 
                            if comp_id != start and comp_id != end]
        
        # If there are intermediate nodes and we can still reach the target
        # after removing some intermediate nodes, then there are multiple paths
        for node in intermediate_nodes:
            if has_path(adjacency, start, end, {node}):
                return True  # Found alternative path
        
        return False
    
    def _calculate_non_hierarchical_score(self, structure: DiagramStructure) -> float:
        """Calculate score based on lack of clear hierarchy."""
        if not structure.connections:
            return 0.0
        
        # Calculate the variance in connection counts (more uniform = less hierarchical)
        connection_counts = list(self._get_connection_counts(structure).values())
        
        if not connection_counts:
            return 0.0
        
        mean_connections = sum(connection_counts) / len(connection_counts)
        variance = sum((count - mean_connections) ** 2 for count in connection_counts) / len(connection_counts)
        
        # Lower variance indicates more uniform distribution (less hierarchical)
        # Normalize by mean to get coefficient of variation
        if mean_connections > 0:
            cv = (variance ** 0.5) / mean_connections
            # Lower coefficient of variation = higher non-hierarchical score
            return max(0.0, 1.0 - cv)
        
        return 0.0