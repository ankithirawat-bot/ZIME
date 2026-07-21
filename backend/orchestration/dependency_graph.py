"""
Dependency graph.

A directed acyclic graph (DAG) of job dependencies. Supports adding jobs and
dependencies, topological ordering, cycle detection, and dependency/dependent
queries. No execution logic lives here.
"""

from __future__ import annotations

from collections import deque

from backend.orchestration.exceptions import DependencyError


class DependencyGraph:
    """Directed acyclic graph of job dependencies."""

    def __init__(self) -> None:
        self._nodes: set[str] = set()
        self._deps: dict[str, set[str]] = {}
        self._dependents: dict[str, set[str]] = {}

    def add_job(self, job_id: str, dependencies: tuple[str, ...] = ()) -> None:
        """Register a job and its dependencies."""
        self._nodes.add(job_id)
        self._deps.setdefault(job_id, set())
        for dep in dependencies:
            self.add_dependency(job_id, dep)

    def add_dependency(self, job_id: str, dep_id: str) -> None:
        """Add a dependency edge (job_id depends on dep_id)."""
        self._nodes.add(job_id)
        self._nodes.add(dep_id)
        self._deps.setdefault(job_id, set()).add(dep_id)
        self._dependents.setdefault(dep_id, set()).add(job_id)
        self._dependents.setdefault(job_id, set())

    def has_node(self, job_id: str) -> bool:
        """Return True if the job exists in the graph."""
        return job_id in self._nodes

    def dependencies_of(self, job_id: str) -> tuple[str, ...]:
        """Return the dependency ids of a job (sorted)."""
        return tuple(sorted(self._deps.get(job_id, set())))

    def dependents_of(self, job_id: str) -> tuple[str, ...]:
        """Return the direct dependent ids of a job (sorted)."""
        return tuple(sorted(self._dependents.get(job_id, set())))

    def _adjacency(self) -> tuple[dict[str, set[str]], dict[str, int]]:
        adj: dict[str, set[str]] = {n: set() for n in self._nodes}
        indeg: dict[str, int] = {n: 0 for n in self._nodes}
        for node, deps in self._deps.items():
            for dep in deps:
                adj[dep].add(node)
                indeg[node] += 1
        return adj, indeg

    def topological_order(self) -> list[str]:
        """Return job ids in dependency-respecting order.

        Raises:
            DependencyError: When the graph contains a cycle.
        """
        adj, indeg = self._adjacency()
        queue = deque(sorted(n for n in self._nodes if indeg[n] == 0))
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in sorted(adj[node]):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self._nodes):
            cycle = self._find_cycle()
            raise DependencyError(f"Cycle detected in dependency graph: {cycle}")
        return order

    def _find_cycle(self) -> list[str]:
        """Return a cycle path using DFS coloring, or empty list."""
        white, gray, black = 0, 1, 2
        color: dict[str, int] = {n: white for n in self._nodes}
        stack: list[str] = []

        def dfs(node: str) -> list[str]:
            color[node] = gray
            stack.append(node)
            for nxt in sorted(self._deps.get(node, set())):
                if color.get(nxt, white) == gray:
                    idx = stack.index(nxt)
                    return stack[idx:] + [nxt]
                if color.get(nxt, white) == white:
                    found = dfs(nxt)
                    if found:
                        return found
            stack.pop()
            color[node] = black
            return []

        for n in sorted(self._nodes):
            if color[n] == white:
                found = dfs(n)
                if found:
                    return found
        return []

    def validate(self) -> None:
        """Validate the graph: detect cycles.

        Raises:
            DependencyError: When a cycle is present.
        """
        self.topological_order()
