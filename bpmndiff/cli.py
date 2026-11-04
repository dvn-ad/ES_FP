"""Command-line interface for the bpmndiff prototype."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .alignment import AlignmentConfig
from .diff import DiffOptions, diff_models
from .llm import get_adjudicator
from .modes import run_mode_b, run_mode_c
from .parsers import ParseError, load_model
from .report import render_html, render_json, render_markdown, render_text


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--process", metavar="ID|NAME", help="select a specific process inside the file")
    parser.add_argument("--max-states", type=int, default=20000, help="LTS state exploration cap (default: 20000)")
    parser.add_argument("--no-bisimulation", action="store_true", help="skip the partition-refinement check")
    parser.add_argument("--llm", action="store_true", help="enable optional LLM adjudication for ambiguous pairs")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.45,
        help="minimum label similarity for a match (default: 0.45)",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bpmndiff",
        description="Compare BPMN/XPDL process models: alignment, edit script and behavioural checks.",
    )
    parser.add_argument("files", nargs="+", help="two or more .bpmn/.xpdl/.xml files")
    parser.add_argument("--mode", choices=["A", "B", "C"], default="A", help="A pairwise, B reference-vs-variants, C version chain")
    parser.add_argument("--format", choices=["text", "json", "markdown", "html"], default="text")
    parser.add_argument("--out", metavar="PATH", help="write the report to a file instead of stdout")
    parser.add_argument("--html", metavar="PATH", help="also write a standalone HTML report")
    parser.add_argument("--fail-on-change", action="store_true", help="exit with status 1 when models differ behaviourally")
    parser.add_argument(
        "--track-reverts",
        action="store_true",
        help="Mode C: enable lineage revert detection (enabled by default; kept for CLI compatibility)",
    )
    _add_common_options(parser)
    parser.add_argument("--version", action="version", version=f"bpmndiff {__version__}")
    return parser


def _options(args: argparse.Namespace) -> DiffOptions:
    config = AlignmentConfig(match_threshold=args.threshold)
    adjudicator = get_adjudicator(args.llm)
    return DiffOptions(
        max_states=args.max_states,
        bisimulation=not args.no_bisimulation,
        use_llm=bool(adjudicator),
        llm=adjudicator,
        alignment_config=config,
    )


def _run(args: argparse.Namespace) -> tuple[dict, bool]:
    mode = args.mode
    if mode == "A" and len(args.files) != 2:
        raise SystemExit("mode A requires exactly two files")
    if mode in {"B", "C"} and len(args.files) < 2:
        raise SystemExit(f"mode {mode} requires at least two files")

    models = [load_model(path, args.process) for path in args.files]
    options = _options(args)

    if mode == "A":
        comparison = diff_models(models[0], models[1], options)
        result = comparison.to_dict()
        result["mode"] = "A"
        behavior_changed = comparison.behavior.get("equivalent") is False
    elif mode == "B":
        result = run_mode_b(models[0], models[1:], options)
        behavior_changed = any(item["behavior"]["equivalent"] is False for item in result["per_variant"])
    else:
        result = run_mode_c(models, options)
        behavior_changed = any(step["behavior_equivalent"] is False for step in result["steps"])
    return result, behavior_changed


def _write(path: str, content: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _emit(result: dict, args: argparse.Namespace) -> None:
    if args.format == "json":
        content = render_json(result)
    elif args.format == "markdown":
        content = render_markdown(result)
    elif args.format == "html":
        content = render_html(result)
    else:
        content = render_text(result)

    if args.out:
        _write(args.out, content)
        print(f"report written to {args.out}")
    else:
        print(content)

    if args.html:
        _write(args.html, render_html(result))
        print(f"HTML report written to {args.html}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Demo on the Mini Hospital dataset
# ---------------------------------------------------------------------------
def _dataset_root() -> Path:
    env = os.environ.get("BPMNDIFF_DATASET")
    candidates = []
    if env:
        candidates.append(Path(env))
    repo = Path(__file__).resolve().parent.parent
    candidates.append(repo / "BPMN Diagrams Dataset of Functional Requirements" / "XPDL Dataset")
    candidates.append(Path.cwd() / "BPMN Diagrams Dataset of Functional Requirements" / "XPDL Dataset")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise SystemExit(
        "dataset not found; pass --dataset or set BPMNDIFF_DATASET to the XPDL dataset folder"
    )


def _find_model(root: Path, prefix: str) -> Path:
    matches = sorted(root.glob(f"{prefix}.*"))
    if not matches:
        raise FileNotFoundError(f"no dataset folder starting with {prefix!r}")
    for folder in matches:
        xpdl = sorted(folder.glob("*.xpdl"))
        if xpdl:
            return xpdl[0]
        bpmn = sorted(folder.glob("*.bpmn"))
        if bpmn:
            return bpmn[0]
    raise FileNotFoundError(f"no model file in folder {matches[0]}")


def _slug(text: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in text.lower()).strip("_")[:60]


def run_demo(dataset: Path | None = None, out_dir: Path | None = None) -> int:
    root = dataset or _dataset_root()
    output = out_dir or (Path.cwd() / "reports")
    output.mkdir(parents=True, exist_ok=True)

    scenarios = [
        (
            "A",
            "Old vs. new patient registration",
            ["51", "52"],
            "51 vs 52 · old patient vs general new patient registration",
        ),
        (
            "A",
            "General vs. corporate new patient registration",
            ["52", "53"],
            "52 vs 53 · general vs corporate new patient registration",
        ),
        (
            "A",
            "General vs. corporate inpatient registration",
            ["54", "55"],
            "54 vs 55 · general vs corporate inpatient registration",
        ),
        (
            "A",
            "General patient cashier vs. down payment",
            ["58", "59"],
            "58 vs 59 · general patient cashier vs down payment",
        ),
        (
            "B",
            "Patient registration family",
            ["52", "53", "54", "55"],
            "reference 52 vs variants 53, 54, 55",
        ),
        (
            "C",
            "Patient registration evolution chain",
            ["51", "52", "53"],
            "51 -> 52 -> 53",
        ),
    ]

    options = DiffOptions(max_states=20000, bisimulation=True)
    summary: list[dict] = []
    markdown_parts = [
        "# bpmndiff demo report",
        "",
        f"Dataset: `{root}`",
        "",
        "| Scenario | Mode | Verdict | Trace equivalent | Details |",
        "|---|---|---|---|---|",
    ]

    for index, (mode, title, prefixes, description) in enumerate(scenarios, start=1):
        try:
            paths = [_find_model(root, prefix) for prefix in prefixes]
            models = [load_model(str(path)) for path in paths]
            if mode == "A":
                result = diff_models(models[0], models[1], options).to_dict()
                result["mode"] = "A"
                verdict = result["fusion"]["overall"]
                equiv = result["behavior"]["equivalent"]
                details = f"{len(result['operations'])} operations"
            elif mode == "B":
                result = run_mode_b(models[0], models[1:], options)
                verdict = ", ".join(item["summary"] for item in result["per_variant"])
                equiv = all(item["behavior"]["equivalent"] for item in result["per_variant"])
                details = f"{len(result['core_elements'])} core elements"
            else:
                result = run_mode_c(models, options)
                verdict = " -> ".join(step["summary"] for step in result["steps"])
                equiv = all(step["behavior_equivalent"] for step in result["steps"])
                details = f"{len(result['reverts'])} reverts, oracle consistent={result['oracle']['consistent']}"

            slug = f"{index:02d}_{mode}_{_slug(title)}"
            _write(str(output / f"{slug}.json"), render_json(result))
            _write(str(output / f"{slug}.html"), render_html(result))
            _write(str(output / f"{slug}.md"), render_markdown(result))

            summary.append(
                {
                    "scenario": title,
                    "mode": mode,
                    "description": description,
                    "models": [model.name for model in models],
                    "verdict": verdict,
                    "trace_equivalent": equiv,
                    "details": details,
                    "report": f"{slug}.html",
                }
            )
            markdown_parts.append(
                f"| {title} | {mode} | {verdict} | {'yes' if equiv else 'no'} | {details} |"
            )
            print(
                f"[{index}/{len(scenarios)}] {title}: {verdict} "
                f"({'equivalent' if equiv else 'NOT equivalent'})"
            )
        except (ParseError, FileNotFoundError, KeyError, ValueError) as exc:
            print(f"[{index}/{len(scenarios)}] {title}: FAILED - {exc}", file=sys.stderr)
            summary.append({"scenario": title, "mode": mode, "error": str(exc)})
            markdown_parts.append(f"| {title} | {mode} | error | - | {exc} |")

    markdown_parts += [
        "",
        "## Scenario details",
        "",
    ]
    for item in summary:
        if "report" not in item:
            continue
        markdown_parts.append(f"### {item['scenario']}\n")
        markdown_parts.append(f"- Mode: {item['mode']}")
        markdown_parts.append(f"- Models: {', '.join(item['models'])}")
        markdown_parts.append(f"- Verdict: **{item['verdict']}**")
        markdown_parts.append(f"- Trace equivalent: {item['trace_equivalent']}")
        markdown_parts.append(f"- Details: {item['details']}")
        markdown_parts.append(f"- HTML: [{item['report']}]({item['report']})\n")

    _write(str(output / "demo_report.md"), "\n".join(markdown_parts))
    _write(str(output / "demo_summary.json"), json.dumps(summary, indent=2))
    print(f"demo reports written to {output}")
    return 0


def _build_demo_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bpmndiff demo", description="Run the Mini Hospital dataset demo.")
    parser.add_argument("--dataset", help="path to the XPDL dataset folder")
    parser.add_argument("--out", default="reports", help="output directory (default: reports)")
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "demo":
        args = _build_demo_parser().parse_args(argv[1:])
        return run_demo(Path(args.dataset) if args.dataset else None, Path(args.out))

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result, behavior_changed = _run(args)
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    _emit(result, args)
    if args.fail_on_change and behavior_changed:
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
