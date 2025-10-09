"""Performance optimization utilities for Mermaid generation.

This module provides performance optimization features including:
- Optimized node ID generation with caching
- Efficient connection processing algorithms
- Performance profiling and benchmarking
- Configuration options for performance vs. quality trade-offs
"""

import time
import functools
from typing import Dict, List, Set, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import re

from .models import DiagramStructure, Component, Connection, BaseElement
from .node_id_manager import NodeIdManager


@dataclass
class PerformanceMetrics:
    """Performance metrics for Mermaid generation operations."""
    operation_name: str
    execution_time: float
    memory_usage_mb: float = 0.0
    input_size: int = 0
    output_size: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    
    def __post_init__(self):
        """Calculate derived metrics."""
        if self.input_size > 0:
            self.throughput = self.input_size / max(self.execution_time, 0.001)
        else:
            self.throughput = 0.0
        
        total_cache_operations = self.cache_hits + self.cache_misses
        if total_cache_operations > 0:
            self.cache_hit_rate = self.cache_hits / total_cache_operations
        else:
            self.cache_hit_rate = 0.0


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization features."""
    # Caching options
    enable_id_caching: bool = True
    enable_label_caching: bool = True
    enable_connection_caching: bool = True
    max_cache_size: int = 10000
    
    # Processing options
    batch_size: int = 100
    parallel_processing: bool = False
    lazy_evaluation: bool = True
    
    # Quality vs. performance trade-offs
    fast_id_generation: bool = False  # Use simpler ID generation
    skip_validation: bool = False     # Skip expensive validation
    minimal_sanitization: bool = False  # Reduce text sanitization
    
    # Memory optimization
    enable_memory_optimization: bool = True
    gc_threshold: int = 1000  # Trigger garbage collection after N operations
    
    # Profiling options
    enable_profiling: bool = False
    profile_detail_level: str = "basic"  # basic, detailed, verbose


class OptimizedNodeIdManager(NodeIdManager):
    """Performance-optimized version of NodeIdManager with caching and batching."""
    
    def __init__(self, performance_config: Optional[PerformanceConfig] = None):
        """Initialize the optimized node ID manager.
        
        Args:
            performance_config: Performance optimization configuration
        """
        super().__init__()
        self.perf_config = performance_config or PerformanceConfig()
        
        # Performance caches
        self._label_to_id_cache: Dict[str, str] = {}
        self._sanitization_cache: Dict[str, str] = {}
        self._validation_cache: Dict[str, bool] = {}
        
        # Performance metrics
        self._cache_hits = 0
        self._cache_misses = 0
        self._operations_count = 0
        
        # Pre-compiled regex patterns for better performance
        self._word_pattern = re.compile(r'\b\w+\b')
        self._sanitize_pattern = re.compile(r'[^a-zA-Z0-9_-]')
        self._underscore_pattern = re.compile(r'_+')
        self._validation_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_-]*$')
    
    def get_node_id(self, element_id: str, label: str = "") -> str:
        """Get or generate a Mermaid-compatible node ID with optimizations.
        
        Args:
            element_id: Original element ID from Excalidraw
            label: Text label for the element
            
        Returns:
            Valid Mermaid node ID
        """
        self._operations_count += 1
        
        # Check element cache first
        if element_id in self._element_to_id:
            self._cache_hits += 1
            return self._element_to_id[element_id]
        
        self._cache_misses += 1
        
        # Use fast ID generation if enabled
        if self.perf_config.fast_id_generation:
            return self._fast_generate_id(element_id, label)
        
        # Use cached label-to-ID mapping if available
        if (self.perf_config.enable_id_caching and 
            label and label.strip() in self._label_to_id_cache):
            cached_base_id = self._label_to_id_cache[label.strip()]
            final_id = self._resolve_conflicts_optimized(cached_base_id)
            self._register_id(element_id, final_id)
            return final_id
        
        # Generate ID using parent logic but with optimizations
        return super().get_node_id(element_id, label)
    
    def _fast_generate_id(self, element_id: str, label: str = "") -> str:
        """Fast ID generation with minimal processing.
        
        Args:
            element_id: Original element ID
            label: Text label
            
        Returns:
            Generated ID
        """
        # Try simple label-based ID first
        if label and label.strip():
            # Simple sanitization - just take alphanumeric chars
            simple_id = ''.join(c for c in label.strip()[:20] if c.isalnum())
            if simple_id and simple_id[0].isalpha():
                final_id = self._resolve_conflicts_fast(simple_id)
                self._register_id(element_id, final_id)
                return final_id
        
        # Fallback to element ID
        simple_element_id = ''.join(c for c in element_id[:20] if c.isalnum())
        if simple_element_id and simple_element_id[0].isalpha():
            final_id = self._resolve_conflicts_fast(simple_element_id)
            self._register_id(element_id, final_id)
            return final_id
        
        # Final fallback
        fallback_id = f"n{self._id_counter}"
        self._id_counter += 1
        self._register_id(element_id, fallback_id)
        return fallback_id
    
    def _resolve_conflicts_fast(self, base_id: str) -> str:
        """Fast conflict resolution with minimal checks.
        
        Args:
            base_id: Base ID to check
            
        Returns:
            Unique ID
        """
        if base_id not in self._used_ids:
            return base_id
        
        # Simple numeric suffix
        counter = 1
        while f"{base_id}{counter}" in self._used_ids:
            counter += 1
            if counter > 100:  # Safety limit
                return f"n{self._id_counter}"
        
        return f"{base_id}{counter}"
    
    def _resolve_conflicts_optimized(self, base_id: str) -> str:
        """Optimized conflict resolution with caching.
        
        Args:
            base_id: Base ID to resolve
            
        Returns:
            Unique ID
        """
        # Use parent logic but with optimized checks
        if not base_id:
            return self._generate_fallback_id()
        
        # Quick check for availability
        if (base_id not in self._used_ids and 
            not self._is_reserved_keyword_cached(base_id)):
            return base_id
        
        # Use cached conflict counter if available
        if base_id not in self._conflict_counters:
            self._conflict_counters[base_id] = 1
        
        # Try a few quick attempts before falling back
        for _ in range(10):
            candidate_id = f"{base_id}_{self._conflict_counters[base_id]}"
            self._conflict_counters[base_id] += 1
            
            if (candidate_id not in self._used_ids and 
                not self._is_reserved_keyword_cached(candidate_id)):
                return candidate_id
        
        # Fallback to guaranteed unique ID
        return self._generate_fallback_id()
    
    def _is_reserved_keyword_cached(self, id_candidate: str) -> bool:
        """Check reserved keywords with caching.
        
        Args:
            id_candidate: ID to check
            
        Returns:
            True if reserved
        """
        if not self.perf_config.enable_id_caching:
            return super()._is_reserved_keyword(id_candidate)
        
        # Use validation cache
        cache_key = f"reserved_{id_candidate.lower()}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]
        
        result = super()._is_reserved_keyword(id_candidate)
        
        # Cache result if cache isn't full
        if len(self._validation_cache) < self.perf_config.max_cache_size:
            self._validation_cache[cache_key] = result
        
        return result
    
    def sanitize_label(self, text: str) -> str:
        """Optimized label sanitization with caching.
        
        Args:
            text: Input text to sanitize
            
        Returns:
            Sanitized label text
        """
        if not text:
            return ""
        
        # Check cache first
        if (self.perf_config.enable_label_caching and 
            text in self._sanitization_cache):
            self._cache_hits += 1
            return self._sanitization_cache[text]
        
        self._cache_misses += 1
        
        # Use minimal sanitization if enabled
        if self.perf_config.minimal_sanitization:
            result = self._minimal_sanitize(text)
        else:
            result = super().sanitize_label(text)
        
        # Cache result if cache isn't full
        if (self.perf_config.enable_label_caching and 
            len(self._sanitization_cache) < self.perf_config.max_cache_size):
            self._sanitization_cache[text] = result
        
        return result
    
    def _minimal_sanitize(self, text: str) -> str:
        """Minimal sanitization for better performance.
        
        Args:
            text: Input text
            
        Returns:
            Minimally sanitized text
        """
        if not text:
            return ""
        
        # Basic cleanup
        text = str(text).strip()[:100]  # Limit length early
        
        # Replace only the most problematic characters
        replacements = {
            '"': '&quot;',
            "'": '&#39;',
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '\n': ' ',
            '\t': ' ',
            '\r': ' '
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the ID manager.
        
        Returns:
            Dictionary of performance metrics
        """
        total_operations = self._cache_hits + self._cache_misses
        hit_rate = self._cache_hits / max(total_operations, 1)
        
        return {
            "total_operations": self._operations_count,
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_hit_rate": hit_rate,
            "cache_sizes": {
                "label_to_id": len(self._label_to_id_cache),
                "sanitization": len(self._sanitization_cache),
                "validation": len(self._validation_cache)
            },
            "total_ids_generated": len(self._element_to_id),
            "conflict_counters": len(self._conflict_counters)
        }
    
    def clear_caches(self) -> None:
        """Clear all performance caches."""
        self._label_to_id_cache.clear()
        self._sanitization_cache.clear()
        self._validation_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0


class ConnectionProcessor:
    """Optimized connection processing for large diagrams."""
    
    def __init__(self, performance_config: Optional[PerformanceConfig] = None):
        """Initialize the connection processor.
        
        Args:
            performance_config: Performance configuration
        """
        self.perf_config = performance_config or PerformanceConfig()
        self._connection_cache: Dict[str, str] = {}
        self._adjacency_cache: Dict[str, Set[str]] = {}
    
    def process_connections_batch(self, connections: List[Connection], 
                                node_id_manager: OptimizedNodeIdManager) -> List[str]:
        """Process connections in batches for better performance.
        
        Args:
            connections: List of connections to process
            node_id_manager: Node ID manager for ID resolution
            
        Returns:
            List of Mermaid connection strings
        """
        if not connections:
            return []
        
        # Process in batches
        batch_size = self.perf_config.batch_size
        results = []
        
        for i in range(0, len(connections), batch_size):
            batch = connections[i:i + batch_size]
            batch_results = self._process_connection_batch(batch, node_id_manager)
            results.extend(batch_results)
        
        return results
    
    def _process_connection_batch(self, connections: List[Connection], 
                                node_id_manager: OptimizedNodeIdManager) -> List[str]:
        """Process a single batch of connections.
        
        Args:
            connections: Batch of connections
            node_id_manager: Node ID manager
            
        Returns:
            List of connection strings
        """
        results = []
        
        for connection in connections:
            # Get node IDs
            source_id = node_id_manager.get_node_id(
                connection.source_component.shape.id,
                getattr(connection.source_component.label, 'text', '') if connection.source_component.label else ''
            )
            target_id = node_id_manager.get_node_id(
                connection.target_component.shape.id,
                getattr(connection.target_component.label, 'text', '') if connection.target_component.label else ''
            )
            
            # Generate connection string
            connection_str = f"{source_id} --> {target_id}"
            results.append(connection_str)
        
        return results
    
    def build_adjacency_map(self, connections: List[Connection]) -> Dict[str, Set[str]]:
        """Build an adjacency map for efficient graph operations.
        
        Args:
            connections: List of connections
            
        Returns:
            Adjacency map (node_id -> set of connected node_ids)
        """
        adjacency_map = defaultdict(set)
        
        for connection in connections:
            source_id = connection.source_component.shape.id
            target_id = connection.target_component.shape.id
            
            adjacency_map[source_id].add(target_id)
            adjacency_map[target_id].add(source_id)  # Bidirectional for analysis
        
        return dict(adjacency_map)
    
    def detect_cycles_fast(self, connections: List[Connection]) -> List[List[str]]:
        """Fast cycle detection in the connection graph.
        
        Args:
            connections: List of connections
            
        Returns:
            List of cycles (each cycle is a list of node IDs)
        """
        adjacency_map = self.build_adjacency_map(connections)
        visited = set()
        cycles = []
        
        def dfs(node: str, path: List[str], path_set: Set[str]) -> None:
            if node in path_set:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            path_set.add(node)
            
            for neighbor in adjacency_map.get(node, []):
                dfs(neighbor, path, path_set)
            
            path.pop()
            path_set.remove(node)
        
        for node in adjacency_map:
            if node not in visited:
                dfs(node, [], set())
        
        return cycles


def performance_profiler(func: Callable) -> Callable:
    """Decorator for profiling function performance.
    
    Args:
        func: Function to profile
        
    Returns:
        Wrapped function with profiling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Store metrics (could be enhanced to use a proper metrics store)
            if hasattr(wrapper, '_performance_metrics'):
                wrapper._performance_metrics.append({
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'success': True
                })
            else:
                wrapper._performance_metrics = [{
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'success': True
                }]
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            if hasattr(wrapper, '_performance_metrics'):
                wrapper._performance_metrics.append({
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'success': False,
                    'error': str(e)
                })
            else:
                wrapper._performance_metrics = [{
                    'function': func.__name__,
                    'execution_time': execution_time,
                    'success': False,
                    'error': str(e)
                }]
            
            raise
    
    return wrapper


class PerformanceBenchmark:
    """Performance benchmarking utilities for Mermaid generation."""
    
    def __init__(self):
        """Initialize the benchmark suite."""
        self.results: List[PerformanceMetrics] = []
    
    def benchmark_node_id_generation(self, element_count: int, 
                                   performance_config: Optional[PerformanceConfig] = None) -> PerformanceMetrics:
        """Benchmark node ID generation performance.
        
        Args:
            element_count: Number of elements to generate IDs for
            performance_config: Performance configuration to test
            
        Returns:
            Performance metrics
        """
        config = performance_config or PerformanceConfig()
        manager = OptimizedNodeIdManager(config)
        
        # Generate test data
        elements = [
            (f"element_{i}", f"Label {i}" if i % 2 == 0 else "")
            for i in range(element_count)
        ]
        
        start_time = time.time()
        
        # Generate IDs
        for element_id, label in elements:
            manager.get_node_id(element_id, label)
        
        execution_time = time.time() - start_time
        
        # Get manager metrics
        manager_metrics = manager.get_performance_metrics()
        
        metrics = PerformanceMetrics(
            operation_name="node_id_generation",
            execution_time=execution_time,
            input_size=element_count,
            output_size=len(manager.get_all_ids()),
            cache_hits=manager_metrics["cache_hits"],
            cache_misses=manager_metrics["cache_misses"]
        )
        
        self.results.append(metrics)
        return metrics
    
    def benchmark_connection_processing(self, connection_count: int,
                                      performance_config: Optional[PerformanceConfig] = None) -> PerformanceMetrics:
        """Benchmark connection processing performance.
        
        Args:
            connection_count: Number of connections to process
            performance_config: Performance configuration to test
            
        Returns:
            Performance metrics
        """
        from .models import Component, Connection, BaseElement, TextElement
        
        config = performance_config or PerformanceConfig()
        processor = ConnectionProcessor(config)
        manager = OptimizedNodeIdManager(config)
        
        # Generate test connections
        connections = []
        for i in range(connection_count):
            source_element = BaseElement(
                id=f"source_{i}",
                type="rectangle",
                x=0, y=0, width=100, height=60
            )
            target_element = BaseElement(
                id=f"target_{i}",
                type="rectangle", 
                x=150, y=0, width=100, height=60
            )
            
            source_component = Component(
                shape=source_element,
                label=TextElement(
                    id=f"source_text_{i}",
                    type="text",
                    x=25, y=25, width=50, height=20,
                    text=f"Source {i}"
                ) if i % 2 == 0 else None,
                position=(0, 0),
                size=(100, 60)
            )
            
            target_component = Component(
                shape=target_element,
                label=TextElement(
                    id=f"target_text_{i}",
                    type="text",
                    x=175, y=25, width=50, height=20,
                    text=f"Target {i}"
                ) if i % 2 == 0 else None,
                position=(150, 0),
                size=(100, 60)
            )
            
            connection = Connection(
                source_component=source_component,
                target_component=target_component,
                arrow=BaseElement(
                    id=f"arrow_{i}",
                    type="arrow",
                    x=100, y=30, width=50, height=0
                ),
                direction="left-to-right"
            )
            
            connections.append(connection)
        
        start_time = time.time()
        
        # Process connections
        result_strings = processor.process_connections_batch(connections, manager)
        
        execution_time = time.time() - start_time
        
        metrics = PerformanceMetrics(
            operation_name="connection_processing",
            execution_time=execution_time,
            input_size=connection_count,
            output_size=len(result_strings)
        )
        
        self.results.append(metrics)
        return metrics
    
    def run_comprehensive_benchmark(self, sizes: List[int] = None) -> Dict[str, List[PerformanceMetrics]]:
        """Run comprehensive performance benchmarks.
        
        Args:
            sizes: List of sizes to test (default: [10, 50, 100, 500, 1000])
            
        Returns:
            Dictionary of benchmark results by operation type
        """
        if sizes is None:
            sizes = [10, 50, 100, 500, 1000]
        
        results = {
            "node_id_generation": [],
            "connection_processing": [],
            "optimized_vs_standard": []
        }
        
        for size in sizes:
            # Test node ID generation
            standard_config = PerformanceConfig(
                enable_id_caching=False,
                fast_id_generation=False
            )
            optimized_config = PerformanceConfig(
                enable_id_caching=True,
                fast_id_generation=True
            )
            
            standard_metrics = self.benchmark_node_id_generation(size, standard_config)
            optimized_metrics = self.benchmark_node_id_generation(size, optimized_config)
            
            results["node_id_generation"].extend([standard_metrics, optimized_metrics])
            
            # Test connection processing
            conn_metrics = self.benchmark_connection_processing(size, optimized_config)
            results["connection_processing"].append(conn_metrics)
            
            # Compare optimized vs standard
            improvement_ratio = standard_metrics.execution_time / max(optimized_metrics.execution_time, 0.001)
            comparison_metrics = PerformanceMetrics(
                operation_name=f"optimization_improvement_{size}",
                execution_time=improvement_ratio,
                input_size=size
            )
            results["optimized_vs_standard"].append(comparison_metrics)
        
        return results
    
    def generate_performance_report(self) -> str:
        """Generate a performance report from benchmark results.
        
        Returns:
            Formatted performance report
        """
        if not self.results:
            return "No benchmark results available."
        
        report = ["MERMAID GENERATION PERFORMANCE REPORT", "=" * 50, ""]
        
        # Group results by operation
        by_operation = defaultdict(list)
        for result in self.results:
            by_operation[result.operation_name].append(result)
        
        for operation, metrics_list in by_operation.items():
            report.append(f"\n{operation.upper()}:")
            report.append("-" * 30)
            
            for metrics in metrics_list:
                report.append(f"  Input Size: {metrics.input_size}")
                report.append(f"  Execution Time: {metrics.execution_time:.4f}s")
                report.append(f"  Throughput: {metrics.throughput:.2f} items/sec")
                if metrics.cache_hits + metrics.cache_misses > 0:
                    report.append(f"  Cache Hit Rate: {metrics.cache_hit_rate:.2%}")
                report.append("")
        
        return "\n".join(report)