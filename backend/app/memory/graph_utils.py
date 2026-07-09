"""Prerequisite-graph utilities: topological sort + cycle detection.

The graph is represented as an adjacency map ``{concept: [prerequisite, ...]}``
(a prerequisite must be learned before the concept that depends on it). A valid
learning path is a topological order of this DAG.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping


class CycleError(ValueError):
    """Raised when the prerequisite graph contains a cycle (not a DAG)."""

    def __init__(self, remaining: Iterable[str]) -> None:
        self.remaining = sorted(remaining)
        super().__init__(f"prerequisite graph has a cycle involving: {self.remaining}")


def _all_nodes(prereqs: Mapping[str, list[str]]) -> list[str]:
    """Every node: dict keys plus any prereq referenced but not itself a key.

    Order is deterministic (keys first in insertion order, then new prereqs).
    O(V + E).
    """
    seen: dict[str, None] = {}
    for node, deps in prereqs.items():
        seen.setdefault(node, None)
        for dep in deps:
            seen.setdefault(dep, None)
    return list(seen)


def topological_sort(prereqs: Mapping[str, list[str]]) -> list[str]:
    """Return concepts in learnable order (prereqs first) via Kahn's algorithm.

    Complexity: O(V + E). Raises :class:`CycleError` if the graph is cyclic.
    """
    nodes = _all_nodes(prereqs)
    # Forward adjacency: prereq -> [dependents]; indegree = number of prereqs.
    dependents: dict[str, list[str]] = {n: [] for n in nodes}
    indegree: dict[str, int] = {n: 0 for n in nodes}
    for node in nodes:
        for prereq in prereqs.get(node, []):
            dependents[prereq].append(node)
            indegree[node] += 1

    # Seed the queue in input order for a deterministic, stable path.
    queue: deque[str] = deque(n for n in nodes if indegree[n] == 0)
    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                queue.append(dependent)

    if len(order) != len(nodes):
        raise CycleError(n for n in nodes if indegree[n] > 0)
    return order


def has_cycle(prereqs: Mapping[str, list[str]]) -> bool:
    """True iff the prerequisite graph is cyclic. O(V + E)."""
    try:
        topological_sort(prereqs)
    except CycleError:
        return True
    return False


def prerequisites(prereqs: Mapping[str, list[str]], concept: str) -> list[str]:
    """Direct prerequisites of a concept. O(indegree) — a single dict lookup."""
    return list(prereqs.get(concept, []))


def is_unlocked(
    prereqs: Mapping[str, list[str]], concept: str, mastered: set[str]
) -> bool:
    """True iff every direct prerequisite of ``concept`` is mastered. O(indegree)."""
    return all(p in mastered for p in prereqs.get(concept, []))
