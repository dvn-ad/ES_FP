"""Human-readable and machine-readable report rendering."""

from __future__ import annotations

import json
import os
from typing import Iterable

def _short(path: str) -> str:
    if not path:
        return ""
    return os.path.basename(path)


def _trace(trace: Iterable[str]) -> str:
    return " -> ".join(trace) if trace else "(empty trace)"


def _behavior_word(equivalent: bool | None) -> str:
    if equivalent is True:
        return "EQUIVALENT"
    if equivalent is False:
        return "NOT EQUIVALENT"
    return "INCONCLUSIVE"


def _yes_no(value) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _op_target(operation: dict) -> str:
    payload = operation.get("before") or operation.get("after") or {}
    if operation["element"] == "flow":
        if payload.get("source") or payload.get("target"):
            return f'{payload.get("source", "?")} -> {payload.get("target", "?")}'
        return "sequence flow"
    return payload.get("name", "?")


def _format_operation(operation: dict) -> str:
    op = operation["op"]
    detail = operation.get("detail", "")
    target = _op_target(operation)
    review = "  [needs review]" if operation.get("needs_review") else ""
    if op in {"RENAME", "CHANGE_TYPE", "CHANGE_GATEWAY_TYPE"}:
        before = (operation.get("before") or {}).get("name", "?")
        after = (operation.get("after") or {}).get("name", "?")
        if op == "RENAME":
            return f'RENAME               "{before}" -> "{after}"{review}'
        return f"{op:<20} {before}  [{detail}]{review}"
    if op in {"DELETE", "DELETE_FLOW"}:
        return f"{op:<20} {target}{review}"
    return f"{op:<20} {target}{review}"


def _render_a_text(result: dict) -> str:
    ref = result["reference"]
    var = result["variant"]
    alignment = result["alignment"]
    counts = alignment["counts"]
    behavior = result["behavior"]
    fusion = result["fusion"]
    lines: list[str] = []
    line = "=" * 78
    lines.append(line)
    lines.append(" bpmndiff | Mode A | pairwise process comparison")
    lines.append(line)
    lines.append(f" Reference : {ref['name']}  ({ref['format']}, {_short(ref['source'])})")
    lines.append(f"             {ref['stats']['nodes']} nodes, {ref['stats']['edges']} flows")
    lines.append(f" Variant   : {var['name']}  ({var['format']}, {_short(var['source'])})")
    lines.append(f"             {var['stats']['nodes']} nodes, {var['stats']['edges']} flows")
    lines.append("")
    lines.append(
        " Alignment : "
        + ", ".join(
            [
                f"{counts.get('identical', 0)} identical",
                f"{counts.get('synonym', 0)} synonym",
                f"{counts.get('meaning_changed', 0)} meaning-changed",
                f"{len([p for p in alignment['pairs'] if p['a'] and not p['b']])} deleted",
                f"{len([p for p in alignment['pairs'] if p['b'] and not p['a']])} inserted",
            ]
        )
    )
    if counts.get("needs_review"):
        lines.append(f"             {counts['needs_review']} pair(s) flagged needs-review")
    lines.append("")
    lines.append(f" Edit script ({len(result['operations'])} operations)")
    lines.append("-" * 78)
    if result["operations"]:
        for operation in result["operations"]:
            lines.append("  " + _format_operation(operation))
    else:
        lines.append("  (no differences)")
    lines.append("")
    lines.append(" Behaviour")
    lines.append("-" * 78)
    lines.append(f"  Trace equivalence      : {_behavior_word(behavior.get('equivalent'))}")
    lines.append(f"  Method                 : {behavior.get('method', 'n/a')}")
    if behavior.get("truncated"):
        lines.append("  Note                   : state exploration was truncated (see --max-states)")
    counterexample = behavior.get("counterexample")
    if counterexample:
        lines.append(
            f"  Counterexample [{counterexample['direction']}] : {_trace(counterexample['trace'])}"
        )
        lines.append(f"     {counterexample['detail']}")
    bisim = behavior.get("branching_bisimulation")
    if bisim:
        lines.append(
            f"  Branching bisimulation : {_behavior_word(bisim.get('equivalent'))}"
            f" ({bisim.get('reason', '')})"
        )
    samples = behavior.get("trace_samples", {})
    ref_samples = (samples.get("reference") or {}).get("traces", [])
    if ref_samples:
        lines.append("  Reference trace sample :")
        for trace in ref_samples[:3]:
            lines.append("     " + _trace(trace))
    lines.append("")
    fragments = result["fragments"]
    lines.append(f" SESE fragments: {fragments['count']} region(s), {len(fragments['affected'])} affected")
    lines.append("-" * 78)
    if fragments["affected"]:
        for fragment in fragments["affected"]:
            status = fragment.get("status")
            if status == "checked":
                state = _behavior_word(fragment.get("equivalent"))
                lines.append(f"  {fragment['id']} [{fragment['size']} nodes] {state}")
                if fragment.get("counterexample"):
                    ce = fragment["counterexample"]
                    lines.append(f"      counterexample [{ce['direction']}]: {_trace(ce['trace'])}")
            else:
                lines.append(
                    f"  {fragment['id']} [{fragment['size']} nodes] SKIPPED - {fragment.get('reason', '')}"
                )
    else:
        lines.append("  (no affected region)")
    lines.append("")
    lines.append(" Fusion verdict")
    lines.append("-" * 78)
    lines.append(f"  Overall     : {fusion['overall']}")
    lines.append(f"  Element mix : {fusion['verdict_counts']}")
    if fusion.get("needs_review"):
        lines.append("  Review      : one or more element pairs need manual/LLM review")
    return "\n".join(lines)


def _render_b_text(result: dict) -> str:
    lines: list[str] = []
    line = "=" * 78
    lines.append(line)
    lines.append(" bpmndiff | Mode B | reference vs. many variants")
    lines.append(line)
    lines.append(f" Reference : {result['reference']['name']}  ({result['reference']['format']})")
    for variant in result["variants"]:
        lines.append(f" Variant   : {variant['name']}  ({variant['format']})")
    lines.append("")
    lines.append(" Per-variant summary")
    lines.append("-" * 78)
    for item in result["per_variant"]:
        behavior = _behavior_word(item["behavior"]["equivalent"]).lower()
        lines.append(f"  {item['variant']}")
        lines.append(f"    verdict={item['summary']}, trace={behavior}")
        lines.append(f"    operations={item['operation_counts']}")
        if item["behavior"].get("counterexample"):
            ce = item["behavior"]["counterexample"]
            lines.append(f"    counterexample [{ce['direction']}]: {_trace(ce['trace'])}")
    lines.append("")
    lines.append(f" Core elements (present in all {len(result['variants'])} variants): {len(result['core_elements'])}")
    lines.append("-" * 78)
    for row in result["core_elements"][:12]:
        lines.append(f"  [core] {row['element']}")
    if len(result["core_elements"]) > 12:
        lines.append(f"  ... {len(result['core_elements']) - 12} more")
    lines.append("")
    lines.append(f" Variant-specific reference elements: {len(result['variant_specific'])}")
    lines.append("-" * 78)
    for row in result["variant_specific"][:12]:
        present = [name for name, status in row["variants"].items() if status["status"] == "present"]
        lines.append(f"  [partial] {row['element']}  (present in: {', '.join(present)})")
    if len(result["variant_specific"]) > 12:
        lines.append(f"  ... {len(result['variant_specific']) - 12} more")
    lines.append("")
    lines.append(" Elements inserted in individual variants")
    lines.append("-" * 78)
    any_inserted = False
    for item in result["inserted"]:
        for element in item["inserted_elements"][:8]:
            any_inserted = True
            lines.append(f"  [{item['variant']}] + {element['element']}")
        if len(item["inserted_elements"]) > 8:
            lines.append(f"  ... {len(item['inserted_elements']) - 8} more in {item['variant']}")
    if not any_inserted:
        lines.append("  (none)")
    return "\n".join(lines)


def _render_c_text(result: dict) -> str:
    lines: list[str] = []
    line = "=" * 78
    lines.append(line)
    lines.append(" bpmndiff | Mode C | version chain")
    lines.append(line)
    lines.append(" Chain: " + "  ->  ".join(model["name"] for model in result["chain"]))
    lines.append("")
    lines.append(" Consecutive steps")
    lines.append("-" * 78)
    for step in result["steps"]:
        behavior = _behavior_word(step["behavior_equivalent"]).lower()
        lines.append(
            f"  {step['index']}. {step['from']} -> {step['to']}: "
            f"{step['summary']} ({behavior})"
        )
        lines.append(f"     operations={step['operation_counts']}")
        if step.get("counterexample"):
            ce = step["counterexample"]
            lines.append(f"     counterexample [{ce['direction']}]: {_trace(ce['trace'])}")
    lines.append("")
    lines.append(f" Element lineage: {len(result['lineage'])} tracked element(s)")
    lines.append("-" * 78)
    changed = [
        entry
        for entry in result["lineage"]
        if len({h["label"] for h in entry["history"] if h["present"]}) > 1
    ]
    for entry in changed[:12]:
        labels = [h["label"] for h in entry["history"] if h["present"]]
        lines.append(f"  {entry['origin_name']}: " + " -> ".join(labels))
    if not changed:
        lines.append("  (no label changes)")
    if len(changed) > 12:
        lines.append(f"  ... {len(changed) - 12} more")
    lines.append("")
    lines.append(f" Reverts detected: {len(result['reverts'])}")
    lines.append("-" * 78)
    if result["reverts"]:
        for revert in result["reverts"][:12]:
            lines.append(f"  {revert['type']}: {revert['element']} @ {revert.get('step', '?')}")
    else:
        lines.append("  (none)")
    lines.append("")
    lines.append(" Transitivity oracle")
    lines.append("-" * 78)
    oracle = result["oracle"]
    lines.append(f"  Consistent: {oracle['consistent']}")
    lines.append(f"  Rule      : {oracle['rule']}")
    if oracle["discrepancies"]:
        for item in oracle["discrepancies"][:10]:
            lines.append(
                f"  ! {item['element']}: direct={item.get('direct_target') or item.get('direct_source')}, "
                f"chained={item.get('chained_target') or item.get('chained_source')}"
            )
    return "\n".join(lines)


def render_text(result: dict) -> str:
    mode = result.get("mode", "A")
    if mode == "B":
        return _render_b_text(result)
    if mode == "C":
        return _render_c_text(result)
    return _render_a_text(result)


def render_json(result: dict) -> str:
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------
def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def _render_a_markdown(result: dict) -> str:
    ref, var = result["reference"], result["variant"]
    behavior, fusion = result["behavior"], result["fusion"]
    lines = [
        f"# Pairwise comparison: {ref['name']} vs {var['name']}",
        "",
        _md_table(
            ["Model", "Format", "Nodes", "Flows", "Source"],
            [
                ["Reference", ref["format"], ref["stats"]["nodes"], ref["stats"]["edges"], ref["source"]],
                ["Variant", var["format"], var["stats"]["nodes"], var["stats"]["edges"], var["source"]],
            ],
        ),
        "",
        "## Edit script",
        "",
    ]
    if result["operations"]:
        rows = [
            [op["op"], _op_target(op), op.get("detail", ""), "yes" if op.get("needs_review") else "no"]
            for op in result["operations"]
        ]
        lines.append(_md_table(["Operation", "Element", "Detail", "Review"], rows))
    else:
        lines.append("_No differences._")

    lines += ["", "## Behavioural verification", ""]
    lines.append(f"- Trace equivalence: **{_behavior_word(behavior.get('equivalent'))}**")
    lines.append(f"- Method: `{behavior.get('method', 'n/a')}`")
    if behavior.get("counterexample"):
        ce = behavior["counterexample"]
        lines.append(f"- Counterexample ({ce['direction']}): `{_trace(ce['trace'])}`")
        lines.append(f"  - {ce['detail']}")
    bisim = behavior.get("branching_bisimulation")
    if bisim:
        lines.append(f"- Branching bisimulation: **{_behavior_word(bisim.get('equivalent'))}**")

    lines += ["", f"## SESE fragments ({result['fragments']['count']} regions)", ""]
    if result["fragments"]["affected"]:
        rows = []
        for fragment in result["fragments"]["affected"]:
            state = _behavior_word(fragment.get("equivalent")) if fragment.get("status") == "checked" else "skipped"
            counterexample = fragment.get("counterexample") or {}
            rows.append([fragment["id"], fragment["size"], state, _trace(counterexample.get("trace", []))])
        lines.append(_md_table(["Region", "Nodes", "Behaviour", "Counterexample"], rows))
    else:
        lines.append("_No affected region._")

    lines += [
        "",
        "## Fusion verdict",
        "",
        f"**{fusion['overall']}**",
        "",
        f"- Element verdicts: `{fusion['verdict_counts']}`",
        f"- Operations: `{fusion['operation_counts']}`",
        f"- Needs review: {fusion['needs_review']}",
    ]
    return "\n".join(lines)


def _render_b_markdown(result: dict) -> str:
    lines = [
        "# Reference vs. many variants",
        "",
        f"Reference: **{result['reference']['name']}**",
        "",
        _md_table(
            ["Variant", "Verdict", "Trace equivalence", "Operations"],
            [
                [
                    item["variant"],
                    item["summary"],
                    _yes_no(item["behavior"]["equivalent"]),
                    str(item["operation_counts"]),
                ]
                for item in result["per_variant"]
            ],
        ),
        "",
        f"## Core elements ({len(result['core_elements'])})",
        "",
    ]
    for row in result["core_elements"]:
        lines.append(f"- {row['element']}")
    lines += ["", f"## Variant-specific elements ({len(result['variant_specific'])})", ""]
    for row in result["variant_specific"]:
        present = [name for name, status in row["variants"].items() if status["status"] == "present"]
        lines.append(f"- {row['element']} — present in {', '.join(present)}")
    return "\n".join(lines)


def _render_c_markdown(result: dict) -> str:
    lines = [
        "# Version chain",
        "",
        " → ".join(model["name"] for model in result["chain"]),
        "",
        "## Consecutive steps",
        "",
        _md_table(
            ["Step", "Transition", "Verdict", "Trace equiv.", "Operations"],
            [
                [
                    step["index"],
                    f"{step['from']} → {step['to']}",
                    step["summary"],
                    _yes_no(step["behavior_equivalent"]),
                    str(step["operation_counts"]),
                ]
                for step in result["steps"]
            ],
        ),
        "",
        f"## Reverts ({len(result['reverts'])})",
        "",
    ]
    for revert in result["reverts"]:
        lines.append(f"- `{revert['type']}` — {revert['element']} at {revert.get('step', '?')}")
    if not result["reverts"]:
        lines.append("_None detected._")
    oracle = result["oracle"]
    lines += [
        "",
        "## Transitivity oracle",
        "",
        f"- Consistent: **{oracle['consistent']}**",
        f"- Discrepancies: {len(oracle['discrepancies'])}",
    ]
    for item in oracle["discrepancies"]:
        lines.append(f"  - {item['element']}: {item}")
    return "\n".join(lines)


def render_markdown(result: dict) -> str:
    mode = result.get("mode", "A")
    if mode == "B":
        return _render_b_markdown(result)
    if mode == "C":
        return _render_c_markdown(result)
    return _render_a_markdown(result)
