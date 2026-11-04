"""Multi-format process parsers (XPDL 2.x and BPMN 2.0).

Only the standard library is used.  The parsers intentionally ignore layout
information and return a :class:`~bpmndiff.model.ProcessModel`.
"""

from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Iterable

from ..model import Edge, Node, ProcessModel


class ParseError(ValueError):
    """Raised when a file is not a supported process model."""


# ---------------------------------------------------------------------------
# XML helpers
# ---------------------------------------------------------------------------
def local_name(tag: str) -> str:
    """Return the local part of an XML tag (namespace independent)."""
    return tag.rsplit("}", 1)[-1]


def children(element: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in list(element) if local_name(c.tag) == name]


def descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in element.iter() if local_name(c.tag) == name]


def first_child(element: ET.Element, name: str) -> ET.Element | None:
    for child in list(element):
        if local_name(child.tag) == name:
            return child
    return None


def text_of(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return (element.text or "").strip()


def _graphics_box(element: ET.Element) -> tuple[float, float, float, float] | None:
    """Extract (x, y, width, height) from a BizAgi-style graphic block."""
    node_infos = first_child(element, "NodeGraphicsInfos")
    if node_infos is None:
        return None
    for info in children(node_infos, "NodeGraphicsInfo"):
        coords = first_child(info, "Coordinates")
        if coords is None:
            continue
        try:
            x = float(coords.attrib.get("XCoordinate", 0))
            y = float(coords.attrib.get("YCoordinate", 0))
            w = float(info.attrib.get("Width", 0))
            h = float(info.attrib.get("Height", 0))
        except ValueError:
            continue
        return x, y, w, h
    return None


def _assign_lanes_by_geometry(
    model: ProcessModel, lane_boxes: list[tuple[str, float, float]], node_boxes: dict[str, tuple[float, float]]
) -> None:
    """Best-effort lane assignment for XPDL files without flowNodeRef."""
    for node_id, (_, cy) in node_boxes.items():
        for lane_name, y0, height in lane_boxes:
            if y0 <= cy <= y0 + height:
                node = model.nodes.get(node_id)
                if node is not None and not node.lane:
                    node.lane = lane_name
                    if lane_name not in model.lanes:
                        model.lanes.append(lane_name)
                break


# ---------------------------------------------------------------------------
# XPDL
# ---------------------------------------------------------------------------
_GATEWAY_TYPES = {
    "parallel": "and",
    "and": "and",
    "exclusive": "xor",
    "xor": "xor",
    "inclusive": "or",
    "or": "or",
    "complex": "xor",
    "eventbased": "xor",
}


def _xpdl_gateway_kind(activity: ET.Element) -> str:
    explicit = activity.attrib.get("GatewayType", "")
    if not explicit:
        child = first_child(activity, "GatewayType")
        explicit = text_of(child)
    mapped = _GATEWAY_TYPES.get(explicit.replace(" ", "").lower())
    return mapped or "xor"  # BizAgi treats untyped routes as exclusive


def _xpdl_node(activity: ET.Element) -> Node:
    node_id = activity.attrib.get("Id", "")
    name = activity.attrib.get("Name", "")
    event = first_child(activity, "Event")
    if event is not None:
        if first_child(event, "StartEvent") is not None:
            return Node(node_id, name, "start")
        if first_child(event, "EndEvent") is not None:
            return Node(node_id, name, "end")
        return Node(node_id, name, "event")
    if first_child(activity, "Route") is not None:
        return Node(node_id, name, _xpdl_gateway_kind(activity))
    return Node(node_id, name, "task")


def _choose_process(processes: list[ET.Element], requested: str | None) -> ET.Element:
    if not processes:
        raise ParseError("XPDL package contains no WorkflowProcess")

    def score(proc: ET.Element) -> int:
        activities = first_child(proc, "Activities")
        return len(list(activities)) if activities is not None else 0

    if requested:
        for proc in processes:
            if requested in (proc.attrib.get("Id"), proc.attrib.get("Name")):
                return proc
        raise ParseError(f"process {requested!r} not found in XPDL package")
    return max(processes, key=score)


def parse_xpdl(path: str, process: str | None = None) -> ProcessModel:
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:  # pragma: no cover - depends on input files
        raise ParseError(f"invalid XML in {path}: {exc}") from exc
    root = tree.getroot()

    processes = descendants(root, "WorkflowProcess")
    proc = _choose_process(processes, process)
    proc_id = proc.attrib.get("Id", "")
    proc_name = proc.attrib.get("Name", os.path.basename(path))
    model = ProcessModel(id=proc_id, name=proc_name, source=path, fmt="xpdl")

    # Pool name (the visible pool, not the "Main Process" container).
    pool_name = ""
    for pool in descendants(root, "Pool"):
        if pool.attrib.get("Process") == proc_id:
            pool_name = pool.attrib.get("Name", "")
            break
    model.pool = pool_name  # type: ignore[attr-defined]

    lane_boxes: list[tuple[str, float, float]] = []
    for pool in descendants(root, "Pool"):
        if pool.attrib.get("Process") != proc_id:
            continue
        for lane in descendants(pool, "Lane"):
            lane_name = lane.attrib.get("Name", "")
            if lane_name and lane_name not in model.lanes:
                model.lanes.append(lane_name)
            box = _graphics_box(lane)
            if box is not None:
                lane_boxes.append((lane_name, box[1], box[3]))

    node_boxes: dict[str, tuple[float, float]] = {}
    activities = first_child(proc, "Activities")
    if activities is not None:
        for activity in children(activities, "Activity"):
            node = _xpdl_node(activity)
            if not node.id:
                continue
            node.pool = pool_name
            model.add_node(node)
            box = _graphics_box(activity)
            if box is not None:
                node_boxes[node.id] = (box[0], box[1] + box[3] / 2.0)

    if lane_boxes:
        _assign_lanes_by_geometry(model, lane_boxes, node_boxes)

    transitions = first_child(proc, "Transitions")
    if transitions is not None:
        for index, transition in enumerate(children(transitions, "Transition")):
            source = transition.attrib.get("From", "")
            target = transition.attrib.get("To", "")
            if source not in model.nodes or target not in model.nodes:
                continue
            condition_el = first_child(transition, "Condition")
            condition = ""
            if condition_el is not None:
                expression = first_child(condition_el, "Expression")
                condition = text_of(expression) or text_of(condition_el)
            model.add_edge(
                Edge(
                    id=transition.attrib.get("Id", f"flow-{index}"),
                    source=source,
                    target=target,
                    name=transition.attrib.get("Name", ""),
                    condition=condition,
                )
            )

    if not model.nodes:
        raise ParseError(f"no activities found in process {proc_name!r}")
    return model


# ---------------------------------------------------------------------------
# BPMN 2.0
# ---------------------------------------------------------------------------
_BPMN_NODE_KINDS = {
    "startEvent": "start",
    "endEvent": "end",
    "task": "task",
    "userTask": "task",
    "serviceTask": "task",
    "scriptTask": "task",
    "sendTask": "task",
    "receiveTask": "task",
    "manualTask": "task",
    "businessRuleTask": "task",
    "callActivity": "task",
    "subProcess": "task",
    "adHocSubProcess": "task",
    "transaction": "task",
    "intermediateCatchEvent": "event",
    "intermediateThrowEvent": "event",
    "boundaryEvent": "event",
    "exclusiveGateway": "xor",
    "parallelGateway": "and",
    "inclusiveGateway": "or",
    "eventBasedGateway": "xor",
    "complexGateway": "xor",
}


def parse_bpmn(path: str, process: str | None = None) -> ProcessModel:
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:  # pragma: no cover
        raise ParseError(f"invalid XML in {path}: {exc}") from exc
    root = tree.getroot()
    processes = descendants(root, "process")

    def score(proc: ET.Element) -> int:
        return sum(1 for child in list(proc) if local_name(child.tag) in _BPMN_NODE_KINDS)

    if not processes:
        raise ParseError("BPMN file contains no <process>")
    if process:
        selected = [
            p for p in processes if process in (p.attrib.get("id"), p.attrib.get("name"))
        ]
        if not selected:
            raise ParseError(f"process {process!r} not found in BPMN file")
        proc = selected[0]
    else:
        proc = max(processes, key=score)

    proc_id = proc.attrib.get("id", "")
    proc_name = proc.attrib.get("name", os.path.basename(path))
    model = ProcessModel(id=proc_id, name=proc_name, source=path, fmt="bpmn")

    # Pool name from collaboration/participant.
    pool_name = ""
    for participant in descendants(root, "participant"):
        if participant.attrib.get("processRef") == proc_id:
            pool_name = participant.attrib.get("name", "")
            break
    model.pool = pool_name  # type: ignore[attr-defined]

    # Lane membership.
    lane_of: dict[str, str] = {}
    for lane in descendants(proc, "lane"):
        lane_name = lane.attrib.get("name", "")
        if lane_name and lane_name not in model.lanes:
            model.lanes.append(lane_name)
        for ref in children(lane, "flowNodeRef"):
            if text_of(ref):
                lane_of[text_of(ref)] = lane_name

    # Direct flow nodes.  Nested subprocess internals are intentionally not
    # expanded; the subprocess itself is treated as one task.
    for child in list(proc):
        tag = local_name(child.tag)
        kind = _BPMN_NODE_KINDS.get(tag)
        if not kind:
            continue
        node_id = child.attrib.get("id", "")
        if not node_id:
            continue
        node = Node(
            id=node_id,
            name=child.attrib.get("name", ""),
            kind=kind,
            lane=lane_of.get(node_id, ""),
            pool=pool_name,
        )
        model.add_node(node)

    for index, flow in enumerate(descendants(proc, "sequenceFlow")):
        source = flow.attrib.get("sourceRef", "")
        target = flow.attrib.get("targetRef", "")
        if source not in model.nodes or target not in model.nodes:
            continue
        condition = ""
        condition_el = first_child(flow, "conditionExpression")
        if condition_el is not None:
            condition = text_of(condition_el)
        model.add_edge(
            Edge(
                id=flow.attrib.get("id", f"flow-{index}"),
                source=source,
                target=target,
                name=flow.attrib.get("name", ""),
                condition=condition,
            )
        )

    if not model.nodes:
        raise ParseError(f"no flow nodes found in process {proc_name!r}")
    return model


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def load_model(path: str, process: str | None = None) -> ProcessModel:
    """Load a `.xpdl`, `.bpmn` or `.xml` process file.

    The format is detected from the XML root element, not from the extension,
    because many datasets ship BPMN content in `.xml` files.
    """
    if not os.path.isfile(path):
        raise ParseError(f"file not found: {path}")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        raise ParseError(f"not a well-formed XML file: {path}: {exc}") from exc
    root_tag = local_name(root.tag)
    if root_tag == "Package":
        return parse_xpdl(path, process)
    if root_tag == "definitions":
        return parse_bpmn(path, process)
    raise ParseError(
        f"unsupported root element <{root_tag}> in {path}; expected an XPDL "
        "<Package> or a BPMN <definitions> document"
    )


def load_models(paths: Iterable[str], process: str | None = None) -> list[ProcessModel]:
    return [load_model(p, process) for p in paths]
