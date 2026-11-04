"""Human-readable and machine-readable report rendering."""

from __future__ import annotations

import html
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


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
_CSS = """
:root { --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --muted:#94a3b8;
        --accent:#38bdf8; --ok:#4ade80; --warn:#fbbf24; --bad:#f87171; }
* { box-sizing: border-box; }
body { margin:0; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif;
       background:var(--bg); color:var(--text); line-height:1.55; }
main { max-width: 1080px; margin: 0 auto; padding: 40px 24px 80px; }
h1,h2 { line-height:1.2; }
h1 { font-size: 1.8rem; margin-bottom: .2em; }
h2 { margin-top: 2.2em; border-bottom: 1px solid #334155; padding-bottom: .3em; }
.sub { color:var(--muted); margin-top:0; }
.cards { display:grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap:14px; margin:24px 0; }
.card { background:var(--panel); border:1px solid #334155; border-radius:12px; padding:16px; }
.card .label { color:var(--muted); font-size:.78rem; text-transform:uppercase; letter-spacing:.06em; }
.card .value { font-size:1.35rem; font-weight:600; margin-top:4px; }
.ok { color:var(--ok); } .bad { color:var(--bad); } .warn { color:var(--warn); }
table { width:100%; border-collapse:collapse; margin:16px 0; font-size:.92rem; }
th,td { text-align:left; padding:9px 11px; border-bottom:1px solid #334155; vertical-align:top; }
th { color:var(--muted); font-weight:600; background:#172033; }
code { background:#0b1220; border:1px solid #334155; border-radius:5px; padding:1px 5px; }
.badge { display:inline-block; border-radius:999px; padding:2px 9px; font-size:.78rem; font-weight:600; }
.badge.ok { background:#052e16; } .badge.bad { background:#3f1212; } .badge.warn { background:#3a2c05; }
.trace { font-family:ui-monospace, monospace; color:#cbd5e1; }
footer { margin-top:60px; color:var(--muted); font-size:.85rem; }
"""


def _badge(text: str, css: str) -> str:
    return f'<span class="badge {css}">{html.escape(text)}</span>'


def _render_a_html(result: dict) -> str:
    ref, var = result["reference"], result["variant"]
    behavior, fusion = result["behavior"], result["fusion"]
    eq = behavior.get("equivalent")
    eq_class = "ok" if eq is True else ("bad" if eq is False else "warn")
    lines = [
        f"<h1>{html.escape(ref['name'])} <span style='color:#64748b'>vs</span> {html.escape(var['name'])}</h1>",
        "<p class='sub'>Mode A · pairwise process comparison</p>",
        "<div class='cards'>",
        f"<div class='card'><div class='label'>Trace equivalence</div><div class='value {eq_class}'>{'Equivalent' if eq is True else ('Not equivalent' if eq is False else 'Inconclusive')}</div></div>",
        f"<div class='card'><div class='label'>Operations</div><div class='value'>{len(result['operations'])}</div></div>",
        f"<div class='card'><div class='label'>Matched elements</div><div class='value'>{result['alignment']['counts'].get('matched', 0)}</div></div>",
        f"<div class='card'><div class='label'>Fusion verdict</div><div class='value'>{html.escape(fusion['overall'])}</div></div>",
        "</div>",
    ]
    if fusion.get("needs_review"):
        lines.append("<p>" + _badge("needs review", "warn") + " ambiguous element pairs require adjudication.</p>")
    if behavior.get("counterexample"):
        ce = behavior["counterexample"]
        lines.append(
            f"<p class='bad'>Counterexample ({html.escape(ce['direction'])}): "
            f"<span class='trace'>{html.escape(_trace(ce['trace']))}</span></p>"
        )
        lines.append(f"<p class='sub'>{html.escape(ce['detail'])}</p>")

    lines += ["<h2>Edit script</h2>"]
    if result["operations"]:
        rows = []
        for op in result["operations"]:
            rows.append(
                "<tr><td><code>"
                + html.escape(op["op"])
                + "</code></td><td>"
                + html.escape(_op_target(op))
                + "</td><td>"
                + html.escape(op.get("detail", ""))
                + "</td><td>"
                + ("<span class='warn'>yes</span>" if op.get("needs_review") else "no")
                + "</td></tr>"
            )
        lines.append("<table><tr><th>Operation</th><th>Element</th><th>Detail</th><th>Review</th></tr>" + "".join(rows) + "</table>")
    else:
        lines.append("<p>No differences.</p>")

    lines.append("<h2>Behavioural verification</h2>")
    lines.append(f"<p>{_badge(_behavior_word(eq), eq_class)} &nbsp; {html.escape(behavior.get('method', ''))}</p>")
    bisim = behavior.get("branching_bisimulation")
    if bisim:
        cls = "ok" if bisim.get("equivalent") else "bad"
        lines.append(f"<p>Branching bisimulation: {_badge(_behavior_word(bisim.get('equivalent')), cls)} <span class='sub'>{html.escape(bisim.get('reason', ''))}</span></p>")
    samples = behavior.get("trace_samples", {}).get("reference", {}).get("traces", [])
    if samples:
        lines.append("<p class='sub'>Reference trace samples:</p><ul class='trace'>")
        for trace in samples[:5]:
            lines.append(f"<li>{html.escape(_trace(trace))}</li>")
        lines.append("</ul>")

    lines.append(f"<h2>SESE fragments</h2><p>{result['fragments']['count']} regions · {len(result['fragments']['affected'])} affected</p>")
    if result["fragments"]["affected"]:
        rows = []
        for fragment in result["fragments"]["affected"]:
            if fragment.get("status") == "checked":
                state = _badge(_behavior_word(fragment.get("equivalent")), "ok" if fragment.get("equivalent") else "bad")
                counter = (fragment.get("counterexample") or {}).get("trace", [])
            else:
                state = _badge("skipped", "warn")
                counter = []
            rows.append(
                f"<tr><td>{html.escape(fragment['id'])}</td><td>{fragment['size']}</td><td>{state}</td>"
                f"<td class='trace'>{html.escape(_trace(counter))}</td></tr>"
            )
        lines.append("<table><tr><th>Region</th><th>Nodes</th><th>Behaviour</th><th>Counterexample</th></tr>" + "".join(rows) + "</table>")

    lines.append("<h2>Alignment</h2>")
    pairs = [p for p in result["alignment"]["pairs"] if p["a"] and p["b"]]
    if pairs:
        rows = []
        for pair in pairs:
            review = "warn" if pair.get("needs_review") else ""
            rows.append(
                f"<tr><td>{html.escape(pair.get('a') or '')}</td><td>{html.escape(pair.get('b') or '')}</td>"
                f"<td><span class='badge {review}'>{html.escape(pair['label'])}</span></td>"
                f"<td>{pair.get('score', 0):.2f}</td><td>{html.escape(pair.get('reason', ''))}</td></tr>"
            )
        lines.append("<table><tr><th>Reference</th><th>Variant</th><th>Label</th><th>Score</th><th>Reason</th></tr>" + "".join(rows) + "</table>")
    return "\n".join(lines)


def _render_generic_html(result: dict) -> str:
    mode = result.get("mode", "A")
    title = "Reference vs. many variants" if mode == "B" else "Version chain"
    body = [f"<h1>{title}</h1>", f"<p class='sub'>Mode {mode}</p>", "<pre class='trace'>" + html.escape(render_text(result)) + "</pre>"]
    return "\n".join(body)


def render_html(result: dict) -> str:
    mode = result.get("mode", "A")
    body = _render_a_html(result) if mode == "A" else _render_generic_html(result)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>bpmndiff report</title><style>{_CSS}</style></head>
<body><main>{body}<footer>Generated by bpmndiff · pure-Python BPMN/XPDL comparison prototype</footer></main></body></html>"""
