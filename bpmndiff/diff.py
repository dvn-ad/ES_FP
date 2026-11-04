"""Edit-script generation, behavioural verification and fusion verdicts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .alignment import Alignment, AlignmentConfig, align, normalize_label, relabel_map
from .bisimulation import weak_bisimilar
from .decomposition import Decomposition, Region, decompose
from .lts import build_lts, compare_trace_equivalence, enumerate_traces
from .model import KIND_LABELS, ProcessModel


@dataclass
class DiffOptions:
    max_states: int = 20000
    max_dfa_states: int = 5000
    bisimulation: bool = True
    use_llm: bool = False
    llm: object = None
    alignment_config: AlignmentConfig = field(default_factory=AlignmentConfig)


@dataclass
class Comparison:
    reference: ProcessModel
    variant: ProcessModel
    alignment: Alignment
    operations: list[dict]
    behavior: dict
    decomposition: Decomposition
    affected_regions: list[dict]
    fusion: dict
    options: DiffOptions

    def to_dict(self) -> dict:
        alignment = self.alignment.to_dict()
        for item, pair in zip(alignment["pairs"], self.alignment.pairs):
            if pair.a is not None and pair.a in self.reference.nodes:
                item["a_id"] = pair.a
                item["a"] = self.reference.nodes[pair.a].display_name
            if pair.b is not None and pair.b in self.variant.nodes:
                item["b_id"] = pair.b
                item["b"] = self.variant.nodes[pair.b].display_name
        return {
            "mode": "A",
            "reference": {
                "id": self.reference.id,
                "name": self.reference.name,
                "source": self.reference.source,
                "format": self.reference.fmt,
                "pool": self.reference.pool,
                "stats": self.reference.stats(),
            },
            "variant": {
                "id": self.variant.id,
                "name": self.variant.name,
                "source": self.variant.source,
                "format": self.variant.fmt,
                "pool": self.variant.pool,
                "stats": self.variant.stats(),
            },
            "alignment": alignment,
            "operations": self.operations,
            "behavior": self.behavior,
            "fragments": {
                "count": len(self.decomposition.regions),
                "affected": self.affected_regions,
            },
            "fusion": self.fusion,
        }


def _node_ref(model: ProcessModel, node_id: str) -> dict:
    node = model.nodes[node_id]
    return {
        "id": node.id,
        "name": node.display_name,
        "kind": node.kind,
        "kind_label": KIND_LABELS.get(node.kind, node.kind),
        "lane": node.lane,
    }


def _build_operations(
    reference: ProcessModel, variant: ProcessModel, alignment: Alignment
) -> list[dict]:
    operations: list[dict] = []

    for pair in alignment.matched_pairs:
        a = reference.nodes[pair.a]
        b = variant.nodes[pair.b]

        if a.family != b.family:
            operations.append(
                {
                    "op": "CHANGE_TYPE",
                    "element": "node",
                    "before": _node_ref(reference, a.id),
                    "after": _node_ref(variant, b.id),
                    "detail": f"{KIND_LABELS.get(a.kind, a.kind)} -> {KIND_LABELS.get(b.kind, b.kind)}",
                    "label": pair.label,
                    "confidence": pair.confidence,
                    "needs_review": pair.needs_review,
                }
            )
        elif a.is_gateway and b.is_gateway and a.kind != b.kind:
            operations.append(
                {
                    "op": "CHANGE_GATEWAY_TYPE",
                    "element": "gateway",
                    "before": _node_ref(reference, a.id),
                    "after": _node_ref(variant, b.id),
                    "detail": f"{a.kind.upper()} -> {b.kind.upper()}",
                    "label": pair.label,
                    "confidence": pair.confidence,
                    "needs_review": pair.needs_review,
                }
            )

        if normalize_label(a.name) != normalize_label(b.name) and (
            a.name.strip() or b.name.strip()
        ):
            operations.append(
                {
                    "op": "RENAME",
                    "element": "node",
                    "before": _node_ref(reference, a.id),
                    "after": _node_ref(variant, b.id),
                    "detail": f'"{a.display_name}" -> "{b.display_name}"',
                    "label": pair.label,
                    "score": round(pair.score, 3),
                    "confidence": pair.confidence,
                    "needs_review": pair.needs_review,
                }
            )

    for pair in alignment.unmatched_a:
        operations.append(
            {
                "op": "DELETE",
                "element": "node",
                "before": _node_ref(reference, pair.a),
                "after": None,
                "detail": f'removed {KIND_LABELS.get(reference.nodes[pair.a].kind, "node")}',
                "label": "unmatched",
                "confidence": "high",
                "needs_review": False,
            }
        )
    for pair in alignment.unmatched_b:
        operations.append(
            {
                "op": "INSERT",
                "element": "node",
                "before": None,
                "after": _node_ref(variant, pair.b),
                "detail": f'added {KIND_LABELS.get(variant.nodes[pair.b].kind, "node")}',
                "label": "unmatched",
                "confidence": "high",
                "needs_review": False,
            }
        )

    # Sequence-flow changes between already-matched nodes.
    mapped_ref_flows: Counter[tuple[str, str]] = Counter()
    for edge in reference.edges:
        if edge.source in alignment.a_to_b and edge.target in alignment.a_to_b:
            mapped_ref_flows[(alignment.a_to_b[edge.source], alignment.a_to_b[edge.target])] += 1
    variant_flows: Counter[tuple[str, str]] = Counter(
        (edge.source, edge.target) for edge in variant.edges
    )

    for (source, target), count in (mapped_ref_flows - variant_flows).items():
        operations.append(
            {
                "op": "DELETE_FLOW",
                "element": "flow",
                "before": {
                    "source": reference.nodes[alignment.b_to_a[source]].display_name,
                    "target": reference.nodes[alignment.b_to_a[target]].display_name,
                    "source_id": alignment.b_to_a[source],
                    "target_id": alignment.b_to_a[target],
                },
                "after": None,
                "detail": f"flow removed ({count}x)",
                "label": "unmatched",
                "confidence": "high",
                "needs_review": False,
            }
        )
    for (source, target), count in (variant_flows - mapped_ref_flows).items():
        operations.append(
            {
                "op": "INSERT_FLOW",
                "element": "flow",
                "before": None,
                "after": {
                    "source": variant.nodes[source].display_name,
                    "target": variant.nodes[target].display_name,
                    "source_id": source,
                    "target_id": target,
                },
                "detail": f"flow added ({count}x)",
                "label": "unmatched",
                "confidence": "high",
                "needs_review": False,
            }
        )

    order = {
        "DELETE": 0,
        "INSERT": 1,
        "RENAME": 2,
        "CHANGE_TYPE": 3,
        "CHANGE_GATEWAY_TYPE": 4,
        "DELETE_FLOW": 5,
        "INSERT_FLOW": 6,
    }
    operations.sort(key=lambda op: (order.get(op["op"], 99), str(op.get("before") or op.get("after"))))
    return operations


def _change_anchor_sets(
    reference: ProcessModel, variant: ProcessModel, alignment: Alignment, operations: list[dict]
) -> tuple[list[set[str]], dict[str, set[str]]]:
    """Build change-site anchors and the direct reference nodes per site."""
    groups: list[set[str]] = []
    direct: dict[str, set[str]] = {}
    for operation in operations:
        kind = operation["op"]
        if kind in {"RENAME", "CHANGE_TYPE", "CHANGE_GATEWAY_TYPE", "DELETE"}:
            before = operation.get("before") or {}
            a_id = before.get("id")
            if a_id not in reference.nodes:
                continue
            anchors = {a_id}
            for neighbour in reference.predecessors(a_id) + reference.successors(a_id):
                if neighbour in alignment.a_to_b:
                    anchors.add(neighbour)
            groups.append(anchors)
            direct.setdefault(a_id, set()).update(anchors)
        elif kind == "INSERT":
            after = operation.get("after") or {}
            b_id = after.get("id")
            anchors: set[str] = set()
            if b_id in variant.nodes:
                for neighbour in variant.predecessors(b_id) + variant.successors(b_id):
                    if neighbour in alignment.b_to_a:
                        anchors.add(alignment.b_to_a[neighbour])
            if anchors:
                groups.append(anchors)
        elif kind in {"INSERT_FLOW", "DELETE_FLOW"}:
            payload = operation.get("before") or operation.get("after") or {}
            ids: set[str] = set()
            for key in ("source_id", "target_id"):
                node_id = payload.get(key)
                if node_id in reference.nodes:
                    ids.add(node_id)
                elif node_id in alignment.b_to_a:
                    ids.add(alignment.b_to_a[node_id])
            if ids:
                groups.append(ids)
    return groups, direct


def _fragment_results(
    reference: ProcessModel,
    variant: ProcessModel,
    alignment: Alignment,
    decomposition: Decomposition,
    selected: list[Region],
    label_override: dict[str, str],
    options: DiffOptions,
) -> tuple[list[dict], dict[str, dict]]:
    if not selected:
        return [], {}

    results: list[dict] = []
    by_region: dict[str, dict] = {}
    unique = {region.id: region for region in selected}
    matched_variant_nodes = set(alignment.a_to_b.values())
    for region in sorted(unique.values(), key=lambda item: (item.size, item.id)):
        mapped = {alignment.a_to_b[node_id] for node_id in region.nodes if node_id in alignment.a_to_b}
        # Include inserted variant elements that sit on a path between two
        # mapped fragment nodes (for example the new "company information"
        # task in the Mini Hospital variant).
        changed = True
        while changed:
            changed = False
            for node_id in variant.nodes:
                if node_id in mapped or node_id in matched_variant_nodes:
                    continue
                predecessors = variant.predecessors(node_id)
                successors = variant.successors(node_id)
                if any(p in mapped for p in predecessors) and any(s in mapped for s in successors):
                    mapped.add(node_id)
                    changed = True
        report = {
            "id": region.id,
            "entry": reference.nodes[region.entry].display_name
            if region.entry in reference.nodes
            else "(start)",
            "exit": reference.nodes[region.exit].display_name
            if region.exit in reference.nodes
            else "(end)",
            "size": region.size,
            "nodes": [reference.nodes[n].display_name for n in sorted(region.nodes) if n in reference.nodes],
            "node_ids": sorted(region.nodes),
            "status": "checked",
        }
        ref_sub = reference.submodel(region.nodes, name=f"{reference.name} / {region.id}")
        var_sub = variant.submodel(mapped, name=f"{variant.name} / {region.id}")
        if not ref_sub.start_nodes() or not var_sub.start_nodes():
            report["status"] = "skipped"
            report["reason"] = "fragment has no entry point"
        else:
            ref_lts = build_lts(ref_sub, max_states=options.max_states, open_ends=True)
            restricted_map = {
                node_id: label for node_id, label in label_override.items() if node_id in var_sub.nodes
            }
            var_lts = build_lts(
                var_sub, restricted_map, max_states=options.max_states, open_ends=True
            )
            behavior = compare_trace_equivalence(ref_lts, var_lts)
            report.update(
                {
                    "equivalent": behavior["equivalent"],
                    "method": behavior["method"],
                    "counterexample": behavior["counterexample"],
                    "states": {"reference": len(ref_lts.states), "variant": len(var_lts.states)},
                }
            )
        results.append(report)
        by_region[region.id] = report
    return results, by_region


def _pair_behavior(
    pair,
    direct: dict[str, set[str]],
    by_region: dict[str, dict],
    whole: dict,
    decomposition: Decomposition,
) -> dict:
    if pair.a is None or pair.b is None:
        return {"equivalent": False, "scope": "structural"}
    if pair.a not in direct:
        # This element itself was not changed; do not attribute a change that
        # happened elsewhere in the model to it.
        return {"equivalent": True, "scope": "unchanged"}
    region = decomposition.smallest_region_containing(direct[pair.a])
    result = by_region.get(region.id)
    if result and result.get("status") == "checked":
        return {"equivalent": result.get("equivalent"), "scope": region.id}
    return {"equivalent": whole.get("equivalent"), "scope": "whole-model"}


def diff_models(
    reference: ProcessModel, variant: ProcessModel, options: DiffOptions | None = None
) -> Comparison:
    options = options or DiffOptions()
    config = options.alignment_config
    config.use_llm = options.use_llm
    alignment = align(reference, variant, config, llm=options.llm)

    operations = _build_operations(reference, variant, alignment)
    label_override = relabel_map(reference, variant, alignment)

    if operations:
        ref_lts = build_lts(reference, max_states=options.max_states)
        var_lts = build_lts(variant, label_override, max_states=options.max_states)
        behavior = compare_trace_equivalence(ref_lts, var_lts)
        behavior["reference_lts"] = ref_lts.stats()
        behavior["variant_lts"] = var_lts.stats()
        if options.bisimulation:
            behavior["branching_bisimulation"] = weak_bisimilar(ref_lts, var_lts, max_states=6000)
        behavior["trace_samples"] = {
            "reference": enumerate_traces(ref_lts, limit=10, max_traces=8),
            "variant": enumerate_traces(var_lts, limit=10, max_traces=8),
        }
    else:
        behavior = {
            "equivalent": True,
            "inconclusive": False,
            "method": "no edit operations; behaviour is identical by construction",
            "counterexample": None,
            "truncated": False,
            "reference_lts": {},
            "variant_lts": {},
            "trace_samples": {"reference": {"traces": []}, "variant": {"traces": []}},
        }

    decomposition = decompose(reference)
    groups, direct = _change_anchor_sets(reference, variant, alignment, operations)
    selected: dict[str, Region] = {}
    for anchors in groups:
        region = decomposition.smallest_region_containing(anchors)
        selected[region.id] = region
    if groups and not selected:
        selected[decomposition.whole.id] = decomposition.whole
    affected, by_region = _fragment_results(
        reference,
        variant,
        alignment,
        decomposition,
        list(selected.values()),
        label_override,
        options,
    )
    # Report only the outer change sites; nested sub-regions are still kept in
    # ``by_region`` so that per-element verdicts can use the tightest scope.
    reported_regions = [
        item
        for item in affected
        if not any(
            set(item["node_ids"]) < set(other["node_ids"])
            for other in affected
            if other is not item
        )
    ]

    # Fusion matrix (per element pair).
    pair_verdicts: list[dict] = []
    for pair in alignment.pairs:
        if not pair.matched:
            verdict = "structural_change"
            scope = "element"
            equivalent = False
        else:
            local = _pair_behavior(pair, direct, by_region, behavior, decomposition)
            equivalent = local.get("equivalent")
            scope = local.get("scope", "whole-model")
            if pair.needs_review:
                verdict = "needs_review"
            elif pair.label == "meaning_changed":
                verdict = "semantic_change"
            elif equivalent is True:
                verdict = (
                    "unchanged"
                    if pair.label == "identical"
                    and normalize_label(reference.nodes[pair.a].name)
                    == normalize_label(variant.nodes[pair.b].name)
                    else "non_behavioral_rename"
                )
            elif equivalent is False:
                verdict = "behavioral_change"
            else:
                verdict = "inconclusive"
        pair_verdicts.append(
            {
                "a": reference.nodes[pair.a].display_name if pair.a else None,
                "b": variant.nodes[pair.b].display_name if pair.b else None,
                "label": pair.label,
                "verdict": verdict,
                "behaviour_scope": scope,
                "equivalent": equivalent,
                "needs_review": pair.needs_review,
            }
        )

    operation_counts = Counter(op["op"] for op in operations)
    needs_review = sum(1 for pair in alignment.pairs if pair.needs_review)
    has_structural = any(op["op"] in {"INSERT", "DELETE"} for op in operations)
    has_semantic = any(pair.label == "meaning_changed" for pair in alignment.pairs)
    has_rename = operation_counts.get("RENAME", 0) > 0
    equivalent = behavior.get("equivalent")

    if not operations:
        overall = "identical"
    elif equivalent is False and (has_semantic or needs_review):
        overall = "semantic_and_behavioral_change"
    elif equivalent is False:
        overall = "behavioral_change"
    elif equivalent is None:
        overall = "inconclusive_behavior"
    elif has_semantic:
        overall = "semantic_change"
    elif has_structural:
        overall = "structural_change_non_behavioral"
    elif has_rename:
        overall = "non_behavioral_rename"
    else:
        overall = "unchanged"

    fusion = {
        "overall": overall,
        "needs_review": needs_review > 0,
        "element_verdicts": pair_verdicts,
        "verdict_counts": dict(Counter(item["verdict"] for item in pair_verdicts)),
        "operation_counts": dict(operation_counts),
    }

    return Comparison(
        reference=reference,
        variant=variant,
        alignment=alignment,
        operations=operations,
        behavior=behavior,
        decomposition=decomposition,
        affected_regions=reported_regions,
        fusion=fusion,
        options=options,
    )
