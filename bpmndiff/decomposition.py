"""SESE-style decomposition based on dominators and postdominators.

Full RPST construction is outside the scope of the prototype, but the
fragment tree produced here serves the same purpose: it isolates small
single-entry/single-exit regions so that behavioural equivalence can be
checked per affected region instead of only on the whole model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .model import ProcessModel


VIRTUAL_START = "\x00start"
VIRTUAL_END = "\x00end"


@dataclass
class Region:
    id: str
    entry: str
    exit: str
    nodes: frozenset[str]
    parent: str | None = None
    children: list[str] = field(default_factory=list)
    depth: int = 0

    @property
    def size(self) -> int:
        return len(self.nodes)

    def to_dict(self, model: ProcessModel | None = None) -> dict:
        def label(node_id: str) -> str:
            if node_id == VIRTUAL_START:
                return "(start)"
            if node_id == VIRTUAL_END:
                return "(end)"
            if model and node_id in model.nodes:
                return model.nodes[node_id].display_name
            return node_id

        return {
            "id": self.id,
            "entry": label(self.entry),
            "exit": label(self.exit),
            "size": self.size,
            "parent": self.parent,
            "depth": self.depth,
            "nodes": sorted(self.nodes),
        }


@dataclass
class Decomposition:
    regions: list[Region]
    whole: Region
    _by_id: dict[str, Region] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._by_id = {r.id: r for r in self.regions}

    def region(self, region_id: str) -> Region | None:
        return self._by_id.get(region_id)

    def smallest_region_containing(self, node_ids: set[str]) -> Region:
        candidates = [r for r in self.regions if node_ids <= r.nodes]
        if not candidates:
            return self.whole
        return min(candidates, key=lambda r: (r.size, r.depth))

    def regions_containing(self, node_ids: set[str]) -> list[Region]:
        return sorted(
            [r for r in self.regions if node_ids <= r.nodes],
            key=lambda r: (r.size, r.depth),
        )

    def top_level(self) -> list[Region]:
        return [r for r in self.regions if r.parent is None]

    def to_dict(self, model: ProcessModel | None = None) -> dict:
        return {"count": len(self.regions), "regions": [r.to_dict(model) for r in self.regions]}


def _dominators(
    nodes: set[str],
    succ: dict[str, set[str]],
    pred: dict[str, set[str]],
    start: str,
) -> dict[str, set[str]]:
    dom = {node: set(nodes) for node in nodes}
    dom[start] = {start}
    changed = True
    while changed:
        changed = False
        for node in nodes - {start}:
            parents = pred.get(node, set())
            if not parents:
                new = {node}
            else:
                intersection = set(nodes)
                for parent in parents:
                    intersection &= dom.get(parent, set(nodes))
                new = {node} | intersection
            if new != dom[node]:
                dom[node] = new
                changed = True
    return dom


def _build_graph(model: ProcessModel) -> tuple[set[str], dict[str, set[str]], dict[str, set[str]]]:
    nodes = set(model.nodes) | {VIRTUAL_START, VIRTUAL_END}
    succ: dict[str, set[str]] = {node: set() for node in nodes}
    for edge in model.edges:
        if edge.source in model.nodes and edge.target in model.nodes:
            succ[edge.source].add(edge.target)
    for start in model.start_nodes():
        succ[VIRTUAL_START].add(start)
    for terminal in model.terminal_nodes():
        succ[terminal].add(VIRTUAL_END)
    pred: dict[str, set[str]] = {node: set() for node in nodes}
    for source, targets in succ.items():
        for target in targets:
            pred[target].add(source)
    return nodes, succ, pred


def _sese_region(
    model: ProcessModel,
    dom: dict[str, set[str]],
    postdom: dict[str, set[str]],
    entry: str,
    exit_node: str,
) -> frozenset[str] | None:
    region_nodes = {
        node for node in model.nodes if entry in dom.get(node, set()) and exit_node in postdom.get(node, set())
    }
    if len(region_nodes) < 2:
        return None

    incoming = 0
    outgoing = 0
    for edge in model.edges:
        source_inside = edge.source in region_nodes
        target_inside = edge.target in region_nodes
        if not source_inside and target_inside:
            if edge.target != entry:
                return None
            incoming += 1
        elif source_inside and not target_inside:
            if edge.source != exit_node:
                return None
            outgoing += 1
    if entry != VIRTUAL_START and incoming != 1:
        return None
    if exit_node != VIRTUAL_END and outgoing != 1:
        return None
    if entry == VIRTUAL_START and incoming != 0:
        return None
    if exit_node == VIRTUAL_END and outgoing != 0:
        return None
    return frozenset(region_nodes)


def decompose(model: ProcessModel) -> Decomposition:
    """Build a tree of SESE-like regions for ``model``."""
    nodes, succ, pred = _build_graph(model)
    dom = _dominators(nodes, succ, pred, VIRTUAL_START)

    reverse_succ = pred
    reverse_pred = succ
    postdom = _dominators(nodes, reverse_succ, reverse_pred, VIRTUAL_END)

    candidates: dict[frozenset[str], tuple[str, str]] = {}
    for entry in nodes:
        for exit_node in nodes:
            if entry == exit_node:
                continue
            if entry not in dom.get(exit_node, set()):
                continue
            if exit_node not in postdom.get(entry, set()):
                continue
            region_nodes = _sese_region(model, dom, postdom, entry, exit_node)
            if region_nodes and region_nodes not in candidates:
                candidates[region_nodes] = (entry, exit_node)

    # The whole process is always the root region.
    whole_nodes = frozenset(model.nodes)
    candidates.pop(whole_nodes, None)
    whole_entry = VIRTUAL_START
    whole_exit = VIRTUAL_END

    ordered = sorted(candidates.items(), key=lambda item: (len(item[0]), sorted(item[0])))
    regions: list[Region] = []
    for index, (region_nodes, (entry, exit_node)) in enumerate(ordered):
        depth = 0
        parent: Region | None = None
        for other in regions:
            if region_nodes < other.nodes and (parent is None or other.size < parent.size):
                parent = other
        if parent is not None:
            depth = parent.depth + 1
        region = Region(
            id=f"R{index:02d}",
            entry=entry,
            exit=exit_node,
            nodes=region_nodes,
            parent=parent.id if parent else None,
            depth=depth,
        )
        regions.append(region)
        if parent is not None:
            parent.children.append(region.id)

    # Insert the whole model at the root of the tree.
    whole = Region(
        id="R-root",
        entry=whole_entry,
        exit=whole_exit,
        nodes=whole_nodes,
        parent=None,
        depth=0,
    )
    for region in regions:
        if region.parent is None:
            region.parent = whole.id
            region.depth += 1
            whole.children.append(region.id)
    regions = [whole] + regions
    # Recompute depth relative to the whole root.
    by_id = {r.id: r for r in regions}

    def depth_of(region: Region, seen: set[str] | None = None) -> int:
        seen = seen or set()
        if region.id == whole.id:
            return 0
        if region.parent is None or region.parent in seen:
            return 1
        seen.add(region.id)
        return 1 + depth_of(by_id[region.parent], seen)

    for region in regions:
        region.depth = depth_of(region)
    return Decomposition(regions=regions, whole=whole)
