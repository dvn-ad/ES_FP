"""Normalised, layout-free process model shared by all parsers.

The whole pipeline works on :class:`ProcessModel`.  Visual information
(coordinates, colours, ...) is deliberately discarded at parse time so that
downstream stages only reason about control flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


TASK_KINDS = {"task"}
EVENT_KINDS = {"start", "end", "event"}
GATEWAY_KINDS = {"xor", "and", "or"}

#: A human readable name for every structural node kind.
KIND_LABELS = {
    "task": "task",
    "start": "start event",
    "end": "end event",
    "event": "intermediate event",
    "xor": "exclusive gateway (XOR)",
    "and": "parallel gateway (AND)",
    "or": "inclusive gateway (OR)",
}


def kind_family(kind: str) -> str:
    """Return the coarse alignment family of a node kind."""
    if kind in TASK_KINDS:
        return "task"
    if kind in EVENT_KINDS:
        return "event"
    if kind in GATEWAY_KINDS:
        return "gateway"
    return "other"


@dataclass
class Node:
    """A flow node (activity, event or gateway)."""

    id: str
    name: str = ""
    kind: str = "task"
    lane: str = ""
    pool: str = ""

    @property
    def family(self) -> str:
        return kind_family(self.kind)

    @property
    def is_gateway(self) -> bool:
        return self.kind in GATEWAY_KINDS

    @property
    def is_event(self) -> bool:
        return self.kind in EVENT_KINDS

    @property
    def display_name(self) -> str:
        name = " ".join(self.name.split())
        return name if name else f"<{KIND_LABELS.get(self.kind, self.kind)}>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.display_name,
            "kind": self.kind,
            "family": self.family,
            "lane": self.lane,
            "pool": self.pool,
        }


@dataclass
class Edge:
    """A sequence flow."""

    id: str
    source: str
    target: str
    name: str = ""
    condition: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "name": self.name,
            "condition": self.condition,
        }


@dataclass
class ProcessModel:
    """A single workflow process in canonical form."""

    id: str
    name: str
    source: str = ""
    fmt: str = ""
    pool: str = ""
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    lanes: list[str] = field(default_factory=list)

    # -- construction -----------------------------------------------------
    def add_node(self, node: Node) -> Node:
        self.nodes[node.id] = node
        if node.lane and node.lane not in self.lanes:
            self.lanes.append(node.lane)
        return node

    def add_edge(self, edge: Edge) -> Edge:
        self.edges.append(edge)
        return edge

    # -- graph helpers ----------------------------------------------------
    def out_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.source == node_id]

    def in_edges(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.target == node_id]

    def successors(self, node_id: str) -> list[str]:
        return [e.target for e in self.out_edges(node_id)]

    def predecessors(self, node_id: str) -> list[str]:
        return [e.source for e in self.in_edges(node_id)]

    def in_degree(self, node_id: str) -> int:
        return len(self.in_edges(node_id))

    def out_degree(self, node_id: str) -> int:
        return len(self.out_edges(node_id))

    def start_nodes(self) -> list[str]:
        starts = [n.id for n in self.nodes.values() if n.kind == "start"]
        if starts:
            return sorted(starts)
        return sorted(n.id for n in self.nodes.values() if self.in_degree(n.id) == 0)

    def end_nodes(self) -> list[str]:
        ends = [n.id for n in self.nodes.values() if n.kind == "end"]
        if ends:
            return sorted(ends)
        return sorted(n.id for n in self.nodes.values() if self.out_degree(n.id) == 0)

    def terminal_nodes(self) -> list[str]:
        """Nodes that cannot continue: explicit ends plus sinks."""
        return sorted(
            {n.id for n in self.nodes.values() if n.kind == "end"}
            | {n.id for n in self.nodes.values() if self.out_degree(n.id) == 0}
        )

    def submodel(self, node_ids: Iterable[str], name: str | None = None) -> "ProcessModel":
        """Induced subgraph used for fragment-level behavioural checks."""
        keep = set(node_ids)
        sub = ProcessModel(
            id=f"{self.id}::fragment",
            name=name or f"{self.name} (fragment)",
            source=self.source,
            fmt=self.fmt,
        )
        for nid in keep:
            if nid in self.nodes:
                sub.nodes[nid] = self.nodes[nid]
        for e in self.edges:
            if e.source in keep and e.target in keep:
                sub.add_edge(e)
        sub.lanes = [lane for lane in self.lanes if any(n.lane == lane for n in sub.nodes.values())]
        return sub

    def stats(self) -> dict:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "tasks": sum(1 for n in self.nodes.values() if n.kind == "task"),
            "gateways": sum(1 for n in self.nodes.values() if n.is_gateway),
            "events": sum(1 for n in self.nodes.values() if n.is_event),
            "lanes": len(self.lanes),
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "source": self.source,
            "format": self.fmt,
            "pool": self.pool,
            "lanes": self.lanes,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "stats": self.stats(),
        }
