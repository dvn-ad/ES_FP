"""Simplified branching-bisimulation check via partition refinement.

Tau transitions are removed through tau-closures and the resulting signature
is refined until stable (in the spirit of Groote et al.'s partition-refinement
algorithms used by ``ltscompare``).  This is a lightweight approximation used
as a second behavioural opinion next to exact trace equivalence.
"""

from __future__ import annotations

from collections import deque

from .lts import LTS, tau_closure


def weak_bisimilar(lts_a: LTS, lts_b: LTS, max_states: int = 6000) -> dict:
    states: list[tuple[int, int]] = []
    for index in range(len(lts_a.states)):
        states.append((0, index))
    for index in range(len(lts_b.states)):
        states.append((1, index))
    if len(states) > max_states:
        return {"equivalent": None, "reason": "state space too large for bisimulation", "checked": False}

    def lts_of(tag: int) -> LTS:
        return lts_a if tag == 0 else lts_b

    closures: dict[tuple[int, int], frozenset[int]] = {}
    for state in states:
        tag, index = state
        closures[state] = tau_closure(lts_of(tag), frozenset({index}))

    def terminal(state: tuple[int, int]) -> str:
        tag, index = state
        lts = lts_of(tag)
        if index in lts.final:
            return "final"
        if index in lts.dead:
            return "dead"
        return "alive"

    block = {state: 0 for state in states}
    iterations = 0
    while True:
        iterations += 1
        signatures: dict[tuple[int, int], tuple] = {}
        for state in states:
            tag, _ = state
            lts = lts_of(tag)
            visible = frozenset(
                (label, block[(tag, target)])
                for member in closures[state]
                for label, target in lts.out(member)
                if label is not None
            )
            silent_blocks = frozenset(block[(tag, member)] for member in closures[state])
            signatures[state] = (terminal(state), visible, silent_blocks)

        unique: dict[tuple, int] = {}
        new_block: dict[tuple[int, int], int] = {}
        for state in states:
            signature = signatures[state]
            if signature not in unique:
                unique[signature] = len(unique)
            new_block[state] = unique[signature]
        changed = any(new_block[state] != block[state] for state in states)
        block = new_block
        if not changed:
            break
        if iterations > len(states) + 2:
            break

    initial_a = (0, lts_a.initial)
    initial_b = (1, lts_b.initial)
    equivalent = block[initial_a] == block[initial_b]
    return {
        "equivalent": equivalent,
        "reason": "initial states are in the same partition block"
        if equivalent
        else "initial states are separated by partition refinement",
        "checked": True,
        "blocks": len(set(block.values())),
        "iterations": iterations,
    }
