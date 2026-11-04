"""Mode A/B/C orchestration.

Mode A is implemented by :mod:`bpmndiff.diff`; this module adds the
reference-vs-many-variants matrix (Mode B) and the version-chain lineage,
revert detection and transitivity oracle (Mode C).
"""

from __future__ import annotations

from .diff import Comparison, DiffOptions, diff_models
from .model import ProcessModel


def _model_summary(model: ProcessModel) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "source": model.source,
        "format": model.fmt,
        "pool": model.pool,
        "stats": model.stats(),
    }


# ---------------------------------------------------------------------------
# Mode B: reference vs. many variants
# ---------------------------------------------------------------------------
def run_mode_b(
    reference: ProcessModel, variants: list[ProcessModel], options: DiffOptions | None = None
) -> dict:
    options = options or DiffOptions()
    comparisons: list[Comparison] = [
        diff_models(reference, variant, options) for variant in variants
    ]

    matrix: list[dict] = []
    for ref_node in reference.nodes.values():
        row = {
            "element": ref_node.display_name,
            "id": ref_node.id,
            "kind": ref_node.kind,
            "variants": {},
        }
        present_count = 0
        for variant, comparison in zip(variants, comparisons):
            pair = comparison.alignment.pair_of_a.get(ref_node.id)
            if pair is not None and pair.matched:
                present_count += 1
                row["variants"][variant.name] = {
                    "status": "present",
                    "label": pair.label,
                    "counterpart": variant.nodes[pair.b].display_name,
                }
            else:
                row["variants"][variant.name] = {"status": "absent"}
        row["present_in"] = present_count
        row["scope"] = "core" if present_count == len(variants) else (
            "variant_specific" if present_count > 0 else "absent_everywhere"
        )
        matrix.append(row)

    variant_specific: list[dict] = []
    for variant, comparison in zip(variants, comparisons):
        inserted = [
            {
                "element": variant.nodes[pair.b].display_name,
                "kind": variant.nodes[pair.b].kind,
                "first_seen_in": variant.name,
            }
            for pair in comparison.alignment.unmatched_b
        ]
        variant_specific.append({"variant": variant.name, "inserted_elements": inserted})

    core_elements = [row for row in matrix if row["scope"] == "core"]
    partial_elements = [row for row in matrix if row["scope"] == "variant_specific"]

    return {
        "mode": "B",
        "reference": _model_summary(reference),
        "variants": [_model_summary(v) for v in variants],
        "per_variant": [
            {
                "variant": variant.name,
                "summary": comparison.fusion["overall"],
                "behavior": {
                    "equivalent": comparison.behavior["equivalent"],
                    "counterexample": comparison.behavior["counterexample"],
                },
                "operation_counts": comparison.fusion["operation_counts"],
                "alignment_counts": comparison.alignment.counts(),
            }
            for variant, comparison in zip(variants, comparisons)
        ],
        "matrix": matrix,
        "core_elements": core_elements,
        "variant_specific": partial_elements,
        "inserted": variant_specific,
        "comparisons": [comparison.to_dict() for comparison in comparisons],
    }


# ---------------------------------------------------------------------------
# Mode C: version chain
# ---------------------------------------------------------------------------
def _revert_events(
    lineage: dict[str, dict], deleted: list[dict], inserted: list[dict]
) -> list[dict]:
    events: list[dict] = []
    for origin, entry in lineage.items():
        history = entry["history"]
        for index in range(2, len(history)):
            previous = history[index - 1]
            current = history[index]
            before = history[index - 2]
            if not (previous["present"] and current["present"] and before["present"]):
                continue
            if current["label"] == before["label"] and previous["label"] != before["label"]:
                events.append(
                    {
                        "type": "label_revert",
                        "origin": origin,
                        "element": entry["origin_name"],
                        "step": current["model"],
                        "from": previous["label"],
                        "back_to": current["label"],
                    }
                )
            if (
                before.get("kind") in {"xor", "and", "or"}
                and current.get("kind") == before.get("kind")
                and previous.get("kind") != before.get("kind")
            ):
                events.append(
                    {
                        "type": "gateway_type_revert",
                        "origin": origin,
                        "element": entry["origin_name"],
                        "step": current["model"],
                        "from": previous.get("kind"),
                        "back_to": current.get("kind"),
                    }
                )
    deleted_labels = {item["element"] for item in deleted}
    for item in inserted:
        if item["element"] in deleted_labels:
            events.append(
                {
                    "type": "reinsertion",
                    "origin": item["origin"],
                    "element": item["element"],
                    "step": item["step"],
                }
            )
    return events


def run_mode_c(models: list[ProcessModel], options: DiffOptions | None = None) -> dict:
    options = options or DiffOptions()
    steps = [
        {"from": models[i].name, "to": models[i + 1].name, "index": i + 1}
        for i in range(len(models) - 1)
    ]
    comparisons = [diff_models(models[i], models[i + 1], options) for i in range(len(models) - 1)]

    lineage: dict[str, dict] = {}
    for node in models[0].nodes.values():
        lineage[node.id] = {
            "origin": node.id,
            "origin_name": node.display_name,
            "kind": node.kind,
            "history": [{"step": 0, "model": models[0].name, "present": True, "label": node.display_name, "kind": node.kind}],
        }
    current_origin: dict[str, str] = {node.id: node.id for node in models[0].nodes.values()}

    deleted: list[dict] = []
    inserted: list[dict] = []

    for step_number, comparison in enumerate(comparisons, start=1):
        alignment = comparison.alignment
        new_origin: dict[str, str] = {}
        for pair in alignment.matched_pairs:
            origin = current_origin.get(pair.a)
            if origin is None:
                origin = f"v{step_number}:{pair.b}"
                lineage.setdefault(
                    origin,
                    {
                        "origin": origin,
                        "origin_name": models[step_number].nodes[pair.b].display_name,
                        "kind": models[step_number].nodes[pair.b].kind,
                        "history": [],
                    },
                )
            new_origin[pair.b] = origin
        for pair in alignment.unmatched_b:
            origin = f"v{step_number}:{pair.b}"
            new_origin[pair.b] = origin
            lineage.setdefault(
                origin,
                {
                    "origin": origin,
                    "origin_name": models[step_number].nodes[pair.b].display_name,
                    "kind": models[step_number].nodes[pair.b].kind,
                    "history": [],
                },
            )
            inserted.append(
                {
                    "origin": origin,
                    "element": models[step_number].nodes[pair.b].display_name,
                    "kind": models[step_number].nodes[pair.b].kind,
                    "step": models[step_number].name,
                }
            )
        for pair in alignment.unmatched_a:
            deleted.append(
                {
                    "element": models[step_number - 1].nodes[pair.a].display_name,
                    "kind": models[step_number - 1].nodes[pair.a].kind,
                    "step": models[step_number].name,
                }
            )

        model = models[step_number]
        for node_id, origin in new_origin.items():
            entry = lineage[origin]
            entry["history"].append(
                {
                    "step": step_number,
                    "model": model.name,
                    "present": True,
                    "label": model.nodes[node_id].display_name,
                    "kind": model.nodes[node_id].kind,
                }
            )
        for origin, entry in lineage.items():
            if origin in {item for item in new_origin.values()}:
                continue
            entry["history"].append(
                {"step": step_number, "model": model.name, "present": False, "label": None, "kind": None}
            )
        current_origin = new_origin

    reverts = _revert_events(lineage, deleted, inserted)

    # -- transitivity oracle -------------------------------------------------
    direct = diff_models(models[0], models[-1], options)
    direct_map = direct.alignment.a_to_b
    final_by_origin = {origin: node_id for node_id, origin in current_origin.items()}
    origin_ids = set(lineage)
    discrepancies: list[dict] = []

    for origin, entry in lineage.items():
        if origin not in {node.id for node in models[0].nodes.values()}:
            continue
        direct_target = direct_map.get(origin)
        composed_target = final_by_origin.get(origin)
        if direct_target != composed_target:
            discrepancies.append(
                {
                    "element": entry["origin_name"],
                    "direct_target": models[-1].nodes[direct_target].display_name
                    if direct_target in models[-1].nodes
                    else None,
                    "chained_target": models[-1].nodes[composed_target].display_name
                    if composed_target in models[-1].nodes
                    else None,
                    "type": "target_mismatch",
                }
            )
    for node_id, origin in current_origin.items():
        if origin not in origin_ids or origin.startswith("v"):
            continue
        direct_source = direct.alignment.b_to_a.get(node_id)
        if direct_source != origin:
            discrepancies.append(
                {
                    "element": models[-1].nodes[node_id].display_name,
                    "direct_source": models[0].nodes[direct_source].display_name
                    if direct_source in models[0].nodes
                    else None,
                    "chained_source": lineage[origin]["origin_name"],
                    "type": "source_mismatch",
                }
            )

    oracle_consistent = not discrepancies
    return {
        "mode": "C",
        "chain": [_model_summary(model) for model in models],
        "steps": [
            {
                "index": step["index"],
                "from": step["from"],
                "to": step["to"],
                "summary": comparison.fusion["overall"],
                "behavior_equivalent": comparison.behavior["equivalent"],
                "operation_counts": comparison.fusion["operation_counts"],
                "counterexample": comparison.behavior["counterexample"],
            }
            for step, comparison in zip(steps, comparisons)
        ],
        "lineage": list(lineage.values()),
        "reverts": reverts,
        "inserted": inserted,
        "deleted": deleted,
        "oracle": {
            "consistent": oracle_consistent,
            "rule": "diff(V1,Vn) must agree with the composition of consecutive diffs",
            "discrepancies": discrepancies[:50],
            "direct_summary": direct.fusion["overall"],
        },
        "comparisons": [comparison.to_dict() for comparison in comparisons],
    }
