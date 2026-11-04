# bpmndiff — BPMN/XPDL process comparison prototype

A dependency-free Python prototype for comparing business process models
across formats. It implements the pipeline described in
[`docs/overview.md`](docs/overview.md) and the follow-up requirements in
[`docs/feedback.md`](docs/feedback.md):

```
parse & normalise (drop layout)
        │
        ▼
tiered element alignment (exact → lexical → semantic → optional LLM)
        │
        ▼
SESE-style region decomposition
        │
        ▼
relabel the variant with the verified alignment
        │
        ▼
per-fragment LTS behavioural equivalence
        │
        ▼
edit script + fusion matrix + Mode A/B/C reports
```

The demo runs on the **Mini Hospital (cashier / FO / ED)** subset of the
`BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset` (68 BizAgi
XPDL files).

---

## Quick start

Requirements: Python 3.10+ (standard library only).

```bash
# Run the bundled dataset demo (writes reports/ with HTML/Markdown/JSON)
python3 -m bpmndiff demo

# Pairwise comparison
python3 -m bpmndiff reference.xpdl variant.xpdl --mode A

# Reference vs. many variants
python3 -m bpmndiff ref.xpdl v1.xpdl v2.xpdl v3.xpdl --mode B

# Version chain
python3 -m bpmndiff v1.bpmn v2.bpmn v3.xpdl --mode C --track-reverts

# Machine-readable output + standalone HTML
python3 -m bpmndiff a.xpdl b.xpdl --format json --out diff.json --html diff.html
```

Optional installation as a console command, in a local virtual environment:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/bpmndiff --help
```

The package has no runtime dependencies, so the virtual environment only keeps
the `bpmndiff` entry point and its metadata isolated from the system Python.

The only optional dependency is a reachable OpenAI-compatible endpoint for
LLM adjudication of ambiguous label pairs (see below). Everything else is
offline and deterministic.

---

## Demo results

Run:

```bash
python3 -m bpmndiff demo --out reports
```

The scenarios are real process-family pairs from the Mini Hospital dataset:

| # | Scenario | Mode | Verdict | Trace equivalent |
|---|---|---|---|---|
| 1 | 51 old-patient registration → 52 general new-patient registration | A | semantic + behavioural change | no |
| 2 | 52 general → 53 corporate new-patient registration | A | semantic + behavioural change | no |
| 3 | 54 general → 55 corporate inpatient registration | A | semantic change only | **yes** |
| 4 | 58 general cashier → 59 down payment | A | semantic + behavioural change | no |
| 5 | 52 reference vs 53/54/55 variants | B | 12 core elements, variant-specific inserts | no |
| 6 | 51 → 52 → 53 registration chain | C | 2 steps, 13 tracked lineages, 0 reverts, oracle consistent | no |

Highlights:

* **52 vs 53** — the corporate variant inserts one task
  (`Enters company informationk 1`) between *Enter the patient's address* and
  *Selects the register button*. The diff reports `INSERT` + two `INSERT_FLOW`
  operations, one `DELETE_FLOW`, one `RENAME`, and produces a counterexample
  trace that is accepted only by the variant.
* **54 vs 55** — apart from the semantic `general → corporate` change, the only
  textual difference is the typo `Displays → Risplays`. The lexical/semantic
  matcher classifies the typo as a synonym, so the trace language and branching
  bisimulation are **equivalent**.
* **Mode B** — the matrix separates 12 core elements (present in every
  registration variant) from elements inserted only in the corporate or
  inpatient variants.
* **Mode C** — the transitivity oracle confirms that the direct 51→53 diff
  agrees with the composition 51→52→53; no reverts occur in this chain.

Generated artefacts live in [`reports/`](reports/):
`demo_report.md`, `demo_summary.json`, and per-scenario `.html`, `.md`, `.json`
files. Each HTML report is standalone (no server, no external assets).

---

## CLI reference

```
bpmndiff FILES... [--mode {A,B,C}] [--format {text,json,markdown,html}]
         [--out PATH] [--html PATH] [--process ID|NAME]
         [--max-states N] [--no-bisimulation] [--llm]
         [--threshold 0.45] [--fail-on-change]

bpmndiff demo [--dataset PATH] [--out DIR]
```

| Option | Meaning |
|---|---|
| `--mode A` | Pairwise comparison (default). Exactly two files. |
| `--mode B` | One reference + N variants. Produces a core/variant-specific matrix. |
| `--mode C` | Ordered version chain. Produces lineage, reverts and a transitivity oracle. |
| `--process` | Select a workflow process by id or name inside a multi-process package. |
| `--max-states` | LTS exploration cap per model (default 20 000). |
| `--no-bisimulation` | Skip the partition-refinement check (faster). |
| `--llm` | Send only ambiguous label pairs to an OpenAI-compatible endpoint. |
| `--threshold` | Minimum label similarity for the lexical stage (default 0.45). |
| `--fail-on-change` | Exit with status 1 when trace equivalence is `False` (CI gate). |
| `--html` | Always write an additional standalone HTML report. |

Exit codes: `0` success, `1` behavioural change with `--fail-on-change`,
`2` parse/input error.

### Optional LLM fallback

Ambiguous pairs (similarity roughly 0.45–0.62) are marked `needs_review` by
default. To let an LLM adjudicate them:

```bash
export BPMNDIFF_LLM=1
export BPMNDIFF_LLM_URL=https://api.openai.com/v1/chat/completions
export BPMNDIFF_LLM_MODEL=gpt-4o-mini
export OPENAI_API_KEY=...
bpmndiff a.xpdl b.xpdl --llm
```

The response must be a JSON array with `label`, `confidence` and `reason` per
pair. Failures fall back to `needs_review`; the offline demo never calls the
network.

---

## What is implemented

### 1. Multi-format parsing and normalisation

* **XPDL 2.x** (`<Package>`) — `WorkflowProcess`, `Activity`/`Event`/`Route`,
  `Transition`, pools, lanes. BizAgi lanes are recovered from lane/activity
  `NodeGraphicsInfo` coordinates when `flowNodeRef`-style membership is absent.
* **BPMN 2.0** (`<definitions>`) — start/end/intermediate events, tasks,
  sub-processes (treated atomically), XOR/AND/OR gateways, sequence flows,
  lanes and participants.
* Format detection is based on the XML root, not the extension, so BPMN content
  in an `.xml` file is accepted. Layout/colour/coordinate data is discarded.
* BizAgi `Route` elements carry no `GatewayType`; they are normalised to XOR,
  matching BizAgi's default exclusive semantics. Explicit
  `GatewayType`/`parallelGateway`/`inclusiveGateway` values are respected.

### 2. Tiered alignment

1. **Exact** — normalised label equality (case, punctuation, whitespace).
2. **Lexical** — Jaro-Winkler plus sequence similarity for typos.
3. **Semantic (offline)** — canonical tokens, a domain synonym lexicon
   (`save/store`, `display/show`, `search/find`, `select/choose`, …) and
   token Dice overlap.
4. **Structural** — gateways and unnamed events are paired by matched
   neighbourhood context and degree.
5. **LLM fallback (optional)** — only ambiguous candidate pairs.

Pairs receive `identical`, `synonym`, `meaning_changed` or `unmatched`, a
confidence value and a `needs_review` flag. Domain contrasts
(`general/corporate`, `inpatient/outpatient`, `old/new`, …) deliberately cap
the score, so a business-variable change is not reported as a harmless rename.

### 3. SESE-style decomposition

Regions are derived from dominator/postdominator pairs and filtered by a
single-entry/single-exit boundary check. The result is a region tree with the
whole model as root. This is a practical approximation of an RPST: the
prototype only needs a reliable "smallest region containing the change" for
scoped behavioural checks. Fragment checks treat sinks as successful exits
(`open_ends=True`) because a fragment has no explicit end event of its own.

### 4. Behavioural engine (pure Python LTS)

* Token-passing semantics for start/end events, tasks, XOR, AND and OR
  gateways. Gateways and start events emit silent `tau` transitions.
* **Trace equivalence**: tau-closure → subset construction → product-automaton
  language comparison. A shortest counterexample trace and direction
  (`reference_only` / `variant_only`) are returned.
* **Branching bisimulation**: partition refinement over tau-closure
  signatures, in the spirit of the `ltscompare` algorithms (simplified for the
  prototype).
* Fragment-level checks run on the smallest affected regions and include
  inserted variant nodes that lie between mapped fragment nodes.
* Exploration is capped (`--max-states`) and reported as `INCONCLUSIVE`
  rather than silently claiming equivalence when truncated.

### 5. Edit script and fusion

Supported operations: `INSERT`, `DELETE`, `RENAME`, `CHANGE_TYPE`,
`CHANGE_GATEWAY_TYPE`, plus `INSERT_FLOW` / `DELETE_FLOW`.

Per-element fusion follows the table in the specification:

| Alignment label | Behaviour | Verdict |
|---|---|---|
| `identical` / `synonym` | equivalent | non-behavioural rename |
| `identical` / `synonym` | not equivalent | behavioural change + counterexample |
| `meaning_changed` | either | semantic change (and behavioural if not equivalent) |
| `unmatched` | not equivalent | structural insert/delete |
| low confidence | any | **needs review** |

### 6. Modes

* **A — pairwise**: full edit script, behaviour, fragments, fusion.
* **B — reference vs variants**: per-variant diffs plus an aggregate matrix of
  core elements and variant-specific/inserted elements.
* **C — version chain**: consecutive diffs, element lineage, rename/type/reinsert
  revert detection, and a transitivity oracle comparing the direct first→last
  diff with the composition of consecutive diffs.

---

## Project layout

```
FP/
├── bpmndiff/
│   ├── model.py           # layout-free ProcessModel / Node / Edge
│   ├── parsers/           # XPDL + BPMN 2.0 loaders (stdlib ElementTree)
│   ├── alignment.py       # normalisation, similarity, pair/alignment model
│   ├── llm.py             # optional OpenAI-compatible adjudicator
│   ├── decomposition.py   # dominator/postdominator SESE-style regions
│   ├── lts.py             # token game, tau-closure, determinisation, traces
│   ├── bisimulation.py    # partition-refinement behavioural check
│   ├── diff.py            # edit script, fragment checks, fusion verdicts
│   ├── modes.py           # Mode B matrix + Mode C lineage/oracle
│   ├── report.py          # text / Markdown / JSON / standalone HTML
│   └── cli.py             # argparse CLI + dataset demo
├── tests/                 # 18 unittest cases (no third-party test runner)
├── reports/               # generated demo artefacts
├── docs/                  # source specification documents
└── pyproject.toml
```

Run the tests with:

```bash
python3 -m unittest discover -s tests -v
```

---

## Dataset notes

* Path: `BPMN Diagrams Dataset of Functional Requirements/XPDL Dataset/`.
* 68 XPDL 2.2 files from BizAgi Process Modeler, one diagram per functional
  requirement folder.
* Models contain pools/lanes, XOR routes, data-store references, and
  conditional transitions. Transition conditions are currently parsed but not
  evaluated (they do not affect the control-flow abstraction).
* The demo deliberately compares related functional variants
  (registration/registration, inpatient/inpatient, cashier/down-payment) so
  that alignment and behavioural differences are meaningful.

---

## Limitations and next steps

* **RPST approximation** — regions are dominator-based candidates, not a fully
  canonical RPST; nested/overlapping candidates can be reported. The smallest
  enclosing region used for scoped checks is reliable for the dataset sizes
  tested.
* **Gateway semantics** — untyped BizAgi routes default to XOR; AND/OR joins
  use a simplified token game (tokens are not synchronised at joins). This is
  sufficient for the small demo fragments but not a full BPMN execution
  semantics.
* **Conditions and data** — sequence-flow conditions, data objects and message
  flows are ignored; the comparison is control-flow only.
* **Sub-processes** are treated as atomic tasks; their interiors are not
  expanded.
* **Formats** — BPMN 2.0 and XPDL 2.x are supported. Visio `.vdx` and other
  vendor formats mentioned in the specification are not yet parsed.
* **Scale** — state exploration and alignment are polynomial-ish but the LTS
  is exponential in the worst case. Large models may return
  `INCONCLUSIVE`; raise `--max-states` or use `--no-bisimulation` for speed.
* **LLM adjudication** is opt-in and conservative; without it, ambiguous pairs
  remain explicitly flagged for manual review.
