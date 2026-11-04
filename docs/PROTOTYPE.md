# Prototype implementation notes

This document maps the requirements in `overview.md` / `feedback.md` to the
code and the demo evidence. The user-facing guide is [`../README.md`](../README.md).

## 1. Requirement coverage

| Requirement | Implementation | Evidence |
|---|---|---|
| Parse `.bpmn`, `.xpdl`, `.xml`; drop layout | `bpmndiff/parsers/__init__.py`; root-element detection; `ProcessModel` contains no coordinates | `tests/test_parsers.py`; demo loads 68 XPDL models |
| Tiered alignment: exact → lexical → embedding → LLM | `bpmndiff/alignment.py`; Jaro-Winkler, sequence ratio, canonical-token Dice, structural gateway matching, optional `llm.py` | `test_core.py`, 52/53 and 54/55 demo outputs |
| Pair classes: identical / synonym / meaning_changed / unmatched | `Pair.label` and `needs_review`; domain-contrast guard (`general/corporate`, …) | 54/55: typo = synonym; `general → corporate` = meaning change |
| SESE/RPST decomposition | `bpmndiff/decomposition.py`; dominator/postdominator candidate regions + boundary check | `test_regions_*`; affected regions in reports |
| Relabel variant from alignment | `relabel_map()` in `alignment.py`, passed to LTS construction | `test_relabel_map_restores_equivalence` |
| Per-fragment equivalence, only where behaviour differs | `diff._fragment_results()`; smallest affected region, inserted-node expansion, `open_ends=True` | 52/53 fragment `R05` returns a variant-only counterexample |
| Edit ops: INSERT / DELETE / RENAME / CHANGE_GATEWAY_TYPE | `diff._build_operations()`; also `CHANGE_TYPE`, `INSERT_FLOW`, `DELETE_FLOW` | 52/53: INSERT + RENAME + flows; `test_gateway_type_change` |
| Pure-Python LTS, tau-closure, determinisation, trace compare | `bpmndiff/lts.py` | `test_sequential_models_equivalent`, `test_xor_vs_and_differ` |
| Branching bisimulation via partition refinement | `bpmndiff/bisimulation.py`; tau-closure signatures | 54/55: equivalent; XOR/AND: separated |
| Fusion matrix (four classes × behaviour) | `fusion` block in `diff.py` | `reports/*.md` |
| Mode A: pairwise | `diff_models()` + CLI | scenarios 1–4 |
| Mode B: reference vs many variants | `modes.run_mode_b()`; core / partial / inserted matrix | scenario 5: 12 core elements |
| Mode C: version chain, lineage, reverts, transitivity oracle | `modes.run_mode_c()` | scenario 6: 13 lineages, 0 reverts, oracle consistent |
| CLI `bpmndiff a.xpdl b.xpdl` | `bpmndiff/cli.py`, `python -m bpmndiff` | `tests/test_cli.py` |
| Report formats | text / JSON / Markdown / standalone HTML in `report.py` | `reports/` |

## 2. Pipeline walk-through (52 vs 53)

1. **Parse** both BizAgi XPDL packages. The visible pool is selected (not the
   empty `Main Process`), untyped `Route` activities become XOR gateways, and
   all graphic information is discarded.
2. **Align** 12 reference nodes to 13 variant nodes: 11 identical, one
   `meaning_changed` (`general → corporate`), one inserted task. The inserted
   task has no counterpart, so it is unmatched on the variant side.
3. **Decompose** the reference into 38 SESE-style candidate regions.
4. **Relabel** the variant's matched labels to the reference labels (including
   the semantic pair), so a pure rename does not create a false behavioural
   difference.
5. **Compare** token-passing LTSs. The variant-only trace
   `… → Enter the patient's address → Enters company informationk 1 →
   Selects the register button` is the shortest counterexample.
6. **Scope** the change to region `R05` (address → register button). Its
   fragment-level check is also not equivalent and contains the inserted node.
7. **Emit** the edit script, fragment results and fusion verdict
   `semantic_and_behavioral_change`.

## 3. Fusion rules used

```python
if not matched:                        structural_change
elif needs_review:                     needs_review
elif label == "meaning_changed":       semantic_change
elif local_behaviour is True:          non_behavioral_rename (or unchanged)
elif local_behaviour is False:         behavioral_change
else:                                  inconclusive
```

The whole-model trace check sets the overall verdict; fragment checks refine
the per-element verdict when the element is directly part of a change site.
Elements elsewhere in the model are not blamed for a change they did not
cause.

## 4. Determinism and offline behaviour

* Alignment and LTS exploration are deterministic (sorted iteration, stable
  tie-breakers).
* The demo never accesses the network.
* LLM adjudication is opt-in (`--llm`) and only sees ambiguous label pairs.
* When state exploration is capped, trace equivalence becomes `INCONCLUSIVE`
  instead of a false `True`.

## 5. Known gaps (prototype scope)

* Region decomposition is a dominator-based approximation, not a canonical
  RPST; candidate regions can overlap.
* AND/OR join semantics are simplified (no token synchronisation).
* Transition conditions, data stores, messages and sub-process interiors are
  not part of the behavioural abstraction.
* Visio `.vdx` is not supported.
* Large models can hit the state cap; use `--max-states` or
  `--no-bisimulation`.

## 6. Reproduction

```bash
python3 -m unittest discover -s tests -v
python3 -m bpmndiff demo --out reports
python3 -m bpmndiff \
  "…/52.Mini hospital (FO).General new patient registration/Diagram 1.xpdl" \
  "…/53.Mini hospital (FO).Corporate new patient registration/Diagram 1.xpdl" \
  --mode A --html reports/52_vs_53.html
```
