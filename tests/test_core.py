"""Tests for the bpmndiff prototype."""

from __future__ import annotations

import unittest

from bpmndiff.decomposition import decompose
from bpmndiff.diff import DiffOptions, diff_models
from bpmndiff.lts import build_lts, compare_trace_equivalence
from bpmndiff.model import Edge, Node, ProcessModel
from bpmndiff.modes import run_mode_b, run_mode_c


def make_model(model_id: str, tasks: list[str], kind: str = "sequence") -> ProcessModel:
    """Build a small model.

    kind="sequence": start -> t1 -> ... -> end
    kind="xor" / "and": start -> gateway -> branches -> join -> end
    """
    model = ProcessModel(id=model_id, name=model_id, source=f"{model_id}.xpdl", fmt="xpdl")
    model.add_node(Node(f"{model_id}-start", "", "start"))
    previous = f"{model_id}-start"
    if kind in {"xor", "and"}:
        model.add_node(Node(f"{model_id}-split", "", kind))
        model.add_edge(Edge(f"{model_id}-e0", previous, f"{model_id}-split"))
        model.add_node(Node(f"{model_id}-join", "", "xor"))
        for index, label in enumerate(tasks):
            task_id = f"{model_id}-task{index}"
            model.add_node(Node(task_id, label, "task"))
            model.add_edge(Edge(f"{model_id}-s{index}", f"{model_id}-split", task_id))
            model.add_edge(Edge(f"{model_id}-j{index}", task_id, f"{model_id}-join"))
        model.add_node(Node(f"{model_id}-end", "", "end"))
        model.add_edge(Edge(f"{model_id}-ej", f"{model_id}-join", f"{model_id}-end"))
        return model

    for index, label in enumerate(tasks):
        task_id = f"{model_id}-task{index}"
        model.add_node(Node(task_id, label, "task"))
        model.add_edge(Edge(f"{model_id}-e{index}", previous, task_id))
        previous = task_id
    model.add_node(Node(f"{model_id}-end", "", "end"))
    model.add_edge(Edge(f"{model_id}-e-end", previous, f"{model_id}-end"))
    return model


class LTSTests(unittest.TestCase):
    def test_sequential_models_equivalent(self):
        a = make_model("a", ["Check form", "Save form"])
        b = make_model("b", ["Check form", "Save form"])
        result = compare_trace_equivalence(build_lts(a), build_lts(b))
        self.assertTrue(result["equivalent"])

    def test_extra_task_is_detected(self):
        a = make_model("a", ["Check form", "Save form"])
        b = make_model("b", ["Check form", "Verify form", "Save form"])
        result = compare_trace_equivalence(build_lts(a), build_lts(b))
        self.assertFalse(result["equivalent"])
        self.assertIn(result["counterexample"]["direction"], {"reference_only", "variant_only"})
        self.assertTrue(result["counterexample"]["trace"])

    def test_xor_vs_and_differ(self):
        a = make_model("a", ["Approve", "Reject"], kind="xor")
        b = make_model("b", ["Approve", "Reject"], kind="and")
        result = compare_trace_equivalence(build_lts(a), build_lts(b))
        self.assertFalse(result["equivalent"])

    def test_relabel_map_restores_equivalence(self):
        a = make_model("a", ["Check form", "Save form"])
        b = make_model("b", ["Verify form", "Store form"])
        result = compare_trace_equivalence(build_lts(a), build_lts(b))
        self.assertFalse(result["equivalent"])
        relabel = {"b-task0": "Check form", "b-task1": "Save form"}
        result = compare_trace_equivalence(build_lts(a), build_lts(b, relabel))
        self.assertTrue(result["equivalent"])

    def test_loop_is_finite_abstraction(self):
        a = make_model("a", ["Fill form"])
        a.add_node(Node("a-gw", "", "xor"))
        a.add_edge(Edge("loop1", "a-task0", "a-gw"))
        a.add_edge(Edge("loop2", "a-gw", "a-task0"))
        a.add_edge(Edge("loop3", "a-gw", "a-end"))
        lts = build_lts(a, max_states=1000)
        self.assertFalse(lts.truncated)
        self.assertTrue(lts.final)


class DecompositionTests(unittest.TestCase):
    def test_regions_include_whole_model(self):
        model = make_model("a", ["One", "Two", "Three"])
        decomposition = decompose(model)
        self.assertGreaterEqual(len(decomposition.regions), 1)
        self.assertEqual(decomposition.whole.nodes, frozenset(model.nodes))
        self.assertEqual(decomposition.whole.parent, None)

    def test_smallest_region_contains_node(self):
        model = make_model("a", ["One", "Two", "Three"])
        decomposition = decompose(model)
        region = decomposition.smallest_region_containing({"a-task1"})
        self.assertIn("a-task1", region.nodes)
        self.assertLessEqual(region.size, len(model.nodes))


class DiffTests(unittest.TestCase):
    def test_rename_only_is_non_behavioural(self):
        a = make_model("a", ["Check form", "Save form"])
        b = make_model("b", ["Check form", "Store form"])
        comparison = diff_models(a, b, DiffOptions(bisimulation=False))
        self.assertTrue(comparison.behavior["equivalent"])
        self.assertTrue(any(op["op"] == "RENAME" for op in comparison.operations))
        self.assertEqual(comparison.fusion["overall"], "non_behavioral_rename")

    def test_insert_operation_and_behaviour_change(self):
        a = make_model("a", ["Check form", "Save form"])
        b = make_model("b", ["Check form", "Verify form", "Save form"])
        comparison = diff_models(a, b, DiffOptions(bisimulation=False))
        self.assertTrue(any(op["op"] == "INSERT" for op in comparison.operations))
        self.assertFalse(comparison.behavior["equivalent"])
        self.assertIn("behavioral_change", comparison.fusion["overall"])

    def test_gateway_type_change(self):
        a = make_model("a", ["Approve", "Reject"], kind="xor")
        b = make_model("b", ["Approve", "Reject"], kind="and")
        comparison = diff_models(a, b, DiffOptions(bisimulation=False))
        ops = [op["op"] for op in comparison.operations]
        self.assertIn("CHANGE_GATEWAY_TYPE", ops)
        self.assertFalse(comparison.behavior["equivalent"])


class ModeTests(unittest.TestCase):
    def test_mode_b_core_and_variant_specific(self):
        ref = make_model("ref", ["A", "B", "C"])
        v1 = make_model("v1", ["A", "B", "C"])
        v2 = make_model("v2", ["A", "B"])
        result = run_mode_b(ref, [v1, v2], DiffOptions(bisimulation=False))
        core = {row["element"] for row in result["core_elements"]}
        partial = {row["element"] for row in result["variant_specific"]}
        self.assertIn("A", core)
        self.assertIn("B", core)
        self.assertIn("C", partial)

    def test_mode_c_lineage_revert_and_oracle(self):
        v1 = make_model("v1", ["Receive request", "Approve request"])
        v2 = make_model("v2", ["Receive request", "Review request"])
        v3 = make_model("v3", ["Receive request", "Approve request"])
        result = run_mode_c([v1, v2, v3], DiffOptions(bisimulation=False))
        self.assertTrue(result["oracle"]["consistent"])
        self.assertTrue(any(revert["type"] == "label_revert" for revert in result["reverts"]))


if __name__ == "__main__":
    unittest.main()
