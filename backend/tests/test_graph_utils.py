"""Tests for topological sort + cycle detection."""

from __future__ import annotations

import pytest

from app.memory.graph_utils import (
    CycleError,
    has_cycle,
    is_unlocked,
    prerequisites,
    topological_sort,
)
from app.seed.concepts import edges_for_topic


def _is_valid_topo_order(order: list[str], prereqs: dict[str, list[str]]) -> bool:
    position = {node: i for i, node in enumerate(order)}
    for node, deps in prereqs.items():
        for dep in deps:
            if position[dep] > position[node]:
                return False
    return True


def test_linear_chain_orders_prereqs_first() -> None:
    graph = {"c": ["b"], "b": ["a"], "a": []}
    assert topological_sort(graph) == ["a", "b", "c"]


def test_diamond_is_valid_order() -> None:
    graph = {"d": ["b", "c"], "b": ["a"], "c": ["a"], "a": []}
    order = topological_sort(graph)
    assert _is_valid_topo_order(order, graph)
    assert order[0] == "a" and order[-1] == "d"


def test_includes_prereqs_that_are_not_keys() -> None:
    # "root" appears only as a prerequisite, never as a key.
    graph = {"leaf": ["root"]}
    order = topological_sort(graph)
    assert set(order) == {"root", "leaf"}
    assert order == ["leaf", "root"] or order == ["root", "leaf"]
    assert _is_valid_topo_order(order, graph)


def test_simple_cycle_raises() -> None:
    graph = {"a": ["b"], "b": ["a"]}
    with pytest.raises(CycleError) as exc:
        topological_sort(graph)
    assert set(exc.value.remaining) == {"a", "b"}
    assert has_cycle(graph) is True


def test_self_loop_is_a_cycle() -> None:
    assert has_cycle({"a": ["a"]}) is True


def test_empty_graph() -> None:
    assert topological_sort({}) == []
    assert has_cycle({}) is False


def test_prerequisites_and_unlocked() -> None:
    graph = {"forward": ["activations", "linear_algebra"]}
    assert prerequisites(graph, "forward") == ["activations", "linear_algebra"]
    assert prerequisites(graph, "missing") == []
    assert is_unlocked(graph, "forward", {"activations", "linear_algebra"}) is True
    assert is_unlocked(graph, "forward", {"activations"}) is False
    assert is_unlocked(graph, "linear_algebra", set()) is True  # no prereqs


@pytest.mark.parametrize("topic", ["neural-networks", "sql"])
def test_seed_topics_are_acyclic_and_sortable(topic: str) -> None:
    graph = edges_for_topic(topic)
    assert not has_cycle(graph)
    order = topological_sort(graph)
    assert _is_valid_topo_order(order, graph)
    assert len(order) == len(graph)
