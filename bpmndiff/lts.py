"""Pure-Python labelled transition system (LTS) engine for a BPMN subset.

The token game supports start/end events, tasks, and XOR/AND/OR gateways.
Gateways and start events emit silent (``tau``) transitions.  Trace
equivalence is decided by tau-closure + subset construction + a product
automaton check, so it is exact for the finite abstraction produced here
(state exploration is bounded to keep the prototype predictable).
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from itertools import combinations

from .model import ProcessModel


DEAD = "\x00dead"


@dataclass
class LTS:
    states: list[frozenset[str] | str]
    initial: int
    transitions: list[tuple[int, str | None, int]]
    final: set[int] = field(default_factory=set)
    dead: set[int] = field(default_factory=set)
    truncated: bool = False
    _out: dict[int, list[tuple[str | None, int]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._out = {i: [] for i in range(len(self.states))}
        for source, label, target in self.transitions:
            self._out.setdefault(source, []).append((label, target))

    def out(self, state: int) -> list[tuple[str | None, int]]:
        return self._out.get(state, [])

    def stats(self) -> dict:
        return {
            "states": len(self.states),
            "transitions": len(self.transitions),
            "final_states": len(self.final),
            "deadlock_states": len(self.dead),
            "truncated": self.truncated,
        }


def _subsets(items: list[str]) -> list[tuple[str, ...]]:
    result: list[tuple[str, ...]] = []
    for size in range(1, len(items) + 1):
        result.extend(combinations(items, size))
    return result


def build_lts(
    model: ProcessModel,
    label_map: dict[str, str] | None = None,
    max_states: int = 20000,
    open_ends: bool = False,
) -> LTS:
    """Explore the token-passing state space of ``model``.

    ``label_map`` overrides task labels (used to relabel a variant before the
    behavioural comparison).  ``open_ends`` treats sinks as successful
    completion, which is what fragment-level checks need because a fragment
    has no explicit end event of its own.
    """
    label_map = label_map or {}
    initial_tokens = frozenset(model.start_nodes())
    keys: list[frozenset[str] | str] = [initial_tokens]
    index: dict[frozenset[str] | str, int] = {initial_tokens: 0}
    transitions: list[tuple[int, str | None, int]] = []
    final: set[int] = set()
    dead: set[int] = set()
    queue: deque[int] = deque([0])
    truncated = False

    dead_index: int | None = None

    def state_id(key: frozenset[str] | str) -> int | None:
        nonlocal truncated, dead_index
        if key in index:
            return index[key]
        if key == DEAD:
            if dead_index is not None:
                return dead_index
            if len(keys) >= max_states:
                truncated = True
                return None
            dead_index = len(keys)
            index[DEAD] = dead_index
            keys.append(DEAD)
            dead.add(dead_index)
            return dead_index
        if len(keys) >= max_states:
            truncated = True
            return None
        new_id = len(keys)
        index[key] = new_id  # type: ignore[index]
        keys.append(key)
        queue.append(new_id)
        return new_id

    while queue:
        state = queue.popleft()
        key = keys[state]
        if key == DEAD:
            continue
        tokens: frozenset[str] = key  # type: ignore[assignment]
        if not tokens:
            final.add(state)
            continue

        moves: list[tuple[str | None, frozenset[str] | str]] = []
        for node_id in sorted(tokens):
            node = model.nodes.get(node_id)
            if node is None:
                continue
            successors = model.successors(node_id)
            base = set(tokens)
            base.discard(node_id)

            def target_set(selected: list[str]) -> frozenset[str] | str:
                if not selected:
                    return frozenset(base) if open_ends else DEAD
                return frozenset(base | set(selected))

            if node.kind == "end":
                moves.append((None, frozenset(base)))
            elif node.kind == "xor":
                if not successors:
                    moves.append((None, target_set([])))
                for successor in successors:
                    moves.append((None, target_set([successor])))
            elif node.kind == "and":
                moves.append((None, target_set(successors)))
            elif node.kind == "or":
                if not successors:
                    moves.append((None, target_set([])))
                for subset in _subsets(successors):
                    moves.append((None, target_set(list(subset))))
            elif node.kind == "start":
                moves.append((None, target_set(successors)))
            else:
                label = label_map.get(node_id, node.display_name)
                moves.append((label, target_set(successors)))

        seen_moves: set[tuple[str | None, frozenset[str] | str]] = set()
        for label, target_key in moves:
            if (label, target_key) in seen_moves:
                continue
            seen_moves.add((label, target_key))
            target_id = state_id(target_key)
            if target_id is None:
                continue
            transitions.append((state, label, target_id))

    return LTS(
        states=keys,
        initial=0,
        transitions=transitions,
        final=final,
        dead=dead,
        truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Tau closure and determinisation
# ---------------------------------------------------------------------------
def tau_closure(lts: LTS, states: frozenset[int]) -> frozenset[int]:
    result = set(states)
    stack = list(states)
    while stack:
        state = stack.pop()
        for label, target in lts.out(state):
            if label is None and target not in result:
                result.add(target)
                stack.append(target)
    return frozenset(result)


@dataclass
class DFA:
    states: list[frozenset[int]]
    initial: int
    transitions: list[tuple[int, str, int]]
    accepting: set[int]
    can_complete: set[int]
    truncated: bool = False
    _out: dict[int, dict[str, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._out = {i: {} for i in range(len(self.states))}
        for source, label, target in self.transitions:
            self._out[source][label] = target

    def out(self, state: int) -> dict[str, int]:
        return self._out.get(state, {})


def determinize(lts: LTS, max_states: int = 5000) -> DFA:
    start = tau_closure(lts, frozenset({lts.initial}))
    states: list[frozenset[int]] = [start]
    index: dict[frozenset[int], int] = {start: 0}
    transitions: list[tuple[int, str, int]] = []
    accepting: set[int] = set()
    queue: deque[int] = deque([0])
    truncated = lts.truncated

    while queue:
        state = queue.popleft()
        subset = states[state]
        if any(member in lts.final for member in subset):
            accepting.add(state)
        grouped: dict[str, set[int]] = {}
        for member in subset:
            for label, target in lts.out(member):
                if label is None:
                    continue
                grouped.setdefault(label, set()).add(target)
        for label, targets in grouped.items():
            closed = tau_closure(lts, frozenset(targets))
            if closed not in index:
                if len(states) >= max_states:
                    truncated = True
                    continue
                index[closed] = len(states)
                states.append(closed)
                queue.append(index[closed])
            transitions.append((state, label, index[closed]))

    can_complete: set[int] = set()
    reverse: dict[int, set[int]] = {i: set() for i in range(len(states))}
    for source, _, target in transitions:
        reverse[target].add(source)
    stack = list(accepting)
    can_complete.update(accepting)
    while stack:
        state = stack.pop()
        for parent in reverse[state]:
            if parent not in can_complete:
                can_complete.add(parent)
                stack.append(parent)

    return DFA(
        states=states,
        initial=0,
        transitions=transitions,
        accepting=accepting,
        can_complete=can_complete,
        truncated=truncated,
    )


# ---------------------------------------------------------------------------
# Equivalence
# ---------------------------------------------------------------------------
def _shortest_completion(dfa: DFA, state: int, limit: int = 50) -> tuple[str, ...]:
    """Shortest accepted continuation from ``state`` (empty if accepting)."""
    if state in dfa.accepting:
        return ()
    queue: deque[tuple[int, tuple[str, ...]]] = deque([(state, ())])
    visited = {state}
    while queue:
        current, path = queue.popleft()
        if len(path) >= limit:
            continue
        for label, target in sorted(dfa.out(current).items()):
            if target in visited:
                continue
            new_path = path + (label,)
            if target in dfa.accepting:
                return new_path
            visited.add(target)
            queue.append((target, new_path))
    return ()


def _counterexample_path(
    path: tuple[str, ...], direction: str, detail: str
) -> dict:
    return {
        "direction": direction,
        "trace": list(path),
        "detail": detail,
    }


def compare_trace_equivalence(lts_a: LTS, lts_b: LTS) -> dict:
    """Compare the accepted trace languages of two LTSs exactly."""
    dfa_a = determinize(lts_a)
    dfa_b = determinize(lts_b)
    queue: deque[tuple[int, int, tuple[str, ...]]] = deque([(dfa_a.initial, dfa_b.initial, ())])
    visited: set[tuple[int, int]] = {(dfa_a.initial, dfa_b.initial)}

    while queue:
        state_a, state_b, path = queue.popleft()
        accepts_a = state_a in dfa_a.accepting
        accepts_b = state_b in dfa_b.accepting
        can_a = state_a in dfa_a.can_complete
        can_b = state_b in dfa_b.can_complete

        if accepts_a != accepts_b:
            direction = "reference_only" if accepts_a else "variant_only"
            return {
                "equivalent": False,
                "inconclusive": False,
                "method": "trace_equivalence (tau-closure + subset construction)",
                "counterexample": _counterexample_path(
                    path, direction, "one model accepts this completed trace, the other does not"
                ),
                "dfa_states": {"reference": len(dfa_a.states), "variant": len(dfa_b.states)},
                "truncated": dfa_a.truncated or dfa_b.truncated,
            }
        if can_a != can_b:
            direction = "reference_only" if can_a else "variant_only"
            dfa = dfa_a if can_a else dfa_b
            state = state_a if can_a else state_b
            completion = _shortest_completion(dfa, state)
            return {
                "equivalent": False,
                "inconclusive": False,
                "method": "trace_equivalence (tau-closure + subset construction)",
                "counterexample": _counterexample_path(
                    path + completion,
                    direction,
                    "only this model can complete the trace",
                ),
                "dfa_states": {"reference": len(dfa_a.states), "variant": len(dfa_b.states)},
                "truncated": dfa_a.truncated or dfa_b.truncated,
            }

        out_a = dfa_a.out(state_a)
        out_b = dfa_b.out(state_b)
        for label in sorted(set(out_a) | set(out_b)):
            target_a = out_a.get(label)
            target_b = out_b.get(label)
            if target_a is None or target_b is None:
                present, missing = (dfa_a, dfa_b) if target_a is not None else (dfa_b, dfa_a)
                present_state = target_a if target_a is not None else target_b
                if present_state in present.can_complete:
                    direction = "reference_only" if present is dfa_a else "variant_only"
                    completion = _shortest_completion(present, present_state)
                    return {
                        "equivalent": False,
                        "inconclusive": False,
                        "method": "trace_equivalence (tau-closure + subset construction)",
                        "counterexample": _counterexample_path(
                            path + (label,) + completion,
                            direction,
                            "only this model can execute the differing task and still complete",
                        ),
                        "dfa_states": {
                            "reference": len(dfa_a.states),
                            "variant": len(dfa_b.states),
                        },
                        "truncated": dfa_a.truncated or dfa_b.truncated,
                    }
                continue
            pair = (target_a, target_b)
            if pair not in visited:
                visited.add(pair)
                queue.append((target_a, target_b, path + (label,)))

    truncated = dfa_a.truncated or dfa_b.truncated
    if truncated:
        return {
            "equivalent": None,
            "inconclusive": True,
            "method": "trace_equivalence (tau-closure + subset construction)",
            "counterexample": None,
            "reason": "state exploration was truncated before a verdict was reached",
            "dfa_states": {"reference": len(dfa_a.states), "variant": len(dfa_b.states)},
            "truncated": True,
        }
    return {
        "equivalent": True,
        "inconclusive": False,
        "method": "trace_equivalence (tau-closure + subset construction)",
        "counterexample": None,
        "dfa_states": {"reference": len(dfa_a.states), "variant": len(dfa_b.states)},
        "truncated": False,
    }


def enumerate_traces(lts: LTS, limit: int = 12, max_traces: int = 200) -> dict:
    """Collect a bounded sample of accepted traces for human-readable reports."""
    dfa = determinize(lts)
    traces: list[list[str]] = []
    truncated = False
    stack: list[tuple[int, tuple[str, ...]]] = [(dfa.initial, ())]
    seen: set[tuple[int, tuple[str, ...]]] = set()
    while stack and len(traces) < max_traces:
        state, trace = stack.pop()
        if trace and state in dfa.accepting:
            traces.append(list(trace))
        if len(trace) >= limit:
            truncated = True
            continue
        for label, target in sorted(dfa.out(state).items()):
            item = (target, trace + (label,))
            if item in seen:
                continue
            seen.add(item)
            stack.append(item)
    traces.sort(key=lambda item: (len(item), item))
    return {
        "count": len(traces),
        "traces": traces[:max_traces],
        "truncated": truncated or dfa.truncated,
    }
