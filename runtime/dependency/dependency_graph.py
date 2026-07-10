"""Dependency injection graph for module initialization order."""

from __future__ import annotations

import logging
from typing import Dict, List, Set

logger = logging.getLogger("ai-companion.runtime.dependency")


class DependencyGraph:
    """Manages dependency relationships between modules and computes correct initialization order."""

    def __init__(self) -> None:
        self._graph: Dict[str, Set[str]] = {}

    def add_module(self, name: str, dependencies: List[str] | None = None) -> None:
        """Register a module and its dependencies."""
        if name not in self._graph:
            self._graph[name] = set()
        if dependencies:
            for dep in dependencies:
                self._graph[name].add(dep)
                if dep not in self._graph:
                    self._graph[dep] = set()

    def resolve_order(self) -> List[str]:
        """Compute the topological sort order of module initialization."""
        visited: Set[str] = set()
        temp: Set[str] = set()
        order: List[str] = []

        def visit(node: str) -> None:
            if node in temp:
                raise RuntimeError(f"Cyclic dependency detected involving module: {node}")
            if node not in visited:
                temp.add(node)
                for edge in self._graph.get(node, set()):
                    visit(edge)
                temp.remove(node)
                visited.add(node)
                order.append(node)

        for module in self._graph:
            if module not in visited:
                visit(module)

        logger.info("DependencyGraph: Resolved initialization order: %s", order)
        return order


# Global singleton
dependency_graph = DependencyGraph()
