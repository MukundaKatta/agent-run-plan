"""Tests for agent_run_plan.

These tests use only the Python standard-library ``unittest`` framework
so they can be run with no third-party dependencies::

    python -m unittest discover -s tests
"""

from __future__ import annotations

import unittest

from agent_run_plan import AgentRunPlan, PlanStep, StepStatus


# ---------------------------------------------------------------------------
# StepStatus enum
# ---------------------------------------------------------------------------


class StepStatusTests(unittest.TestCase):
    def test_step_status_values(self):
        self.assertEqual(StepStatus.PENDING.value, "pending")
        self.assertEqual(StepStatus.RUNNING.value, "running")
        self.assertEqual(StepStatus.DONE.value, "done")
        self.assertEqual(StepStatus.FAILED.value, "failed")
        self.assertEqual(StepStatus.SKIPPED.value, "skipped")

    def test_step_status_is_str(self):
        # StepStatus subclasses str, so it compares equal to its value.
        self.assertEqual(StepStatus.DONE, "done")


# ---------------------------------------------------------------------------
# PlanStep
# ---------------------------------------------------------------------------


class PlanStepTests(unittest.TestCase):
    def test_plan_step_defaults(self):
        step = PlanStep(name="fetch")
        self.assertEqual(step.name, "fetch")
        self.assertEqual(step.description, "")
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertIsNone(step.result)
        self.assertEqual(step.error, "")
        self.assertEqual(step.metadata, {})

    def test_plan_step_is_terminal_pending(self):
        step = PlanStep(name="x", status=StepStatus.PENDING)
        self.assertFalse(step.is_terminal)

    def test_plan_step_is_terminal_running(self):
        step = PlanStep(name="x", status=StepStatus.RUNNING)
        self.assertFalse(step.is_terminal)

    def test_plan_step_is_terminal_done(self):
        step = PlanStep(name="x", status=StepStatus.DONE)
        self.assertTrue(step.is_terminal)

    def test_plan_step_is_terminal_failed(self):
        step = PlanStep(name="x", status=StepStatus.FAILED)
        self.assertTrue(step.is_terminal)

    def test_plan_step_is_terminal_skipped(self):
        step = PlanStep(name="x", status=StepStatus.SKIPPED)
        self.assertTrue(step.is_terminal)

    def test_plan_step_succeeded(self):
        step = PlanStep(name="x", status=StepStatus.DONE)
        self.assertTrue(step.succeeded)

    def test_plan_step_succeeded_false(self):
        step = PlanStep(name="x", status=StepStatus.FAILED)
        self.assertFalse(step.succeeded)

    def test_plan_step_failed(self):
        step = PlanStep(name="x", status=StepStatus.FAILED)
        self.assertTrue(step.failed)

    def test_plan_step_skipped(self):
        step = PlanStep(name="x", status=StepStatus.SKIPPED)
        self.assertTrue(step.skipped)

    def test_plan_step_to_dict(self):
        step = PlanStep(
            name="fetch",
            description="Get data",
            status=StepStatus.DONE,
            result="ok",
            error="",
            metadata={"url": "https://example.com"},
        )
        d = step.to_dict()
        self.assertEqual(d["name"], "fetch")
        self.assertEqual(d["description"], "Get data")
        self.assertEqual(d["status"], "done")
        self.assertEqual(d["result"], "ok")
        self.assertEqual(d["metadata"], {"url": "https://example.com"})

    def test_plan_step_to_dict_copies_metadata(self):
        meta = {"k": 1}
        step = PlanStep(name="x", metadata=meta)
        d = step.to_dict()
        d["metadata"]["k"] = 2
        self.assertEqual(step.metadata, {"k": 1})

    def test_plan_step_repr(self):
        step = PlanStep(name="fetch", status=StepStatus.RUNNING)
        r = repr(step)
        self.assertIn("fetch", r)
        self.assertIn("running", r)


# ---------------------------------------------------------------------------
# AgentRunPlan — creation
# ---------------------------------------------------------------------------


class PlanCreationTests(unittest.TestCase):
    def test_plan_empty(self):
        plan = AgentRunPlan("task")
        self.assertEqual(plan.name, "task")
        self.assertEqual(plan.step_count(), 0)
        self.assertEqual(len(plan), 0)
        self.assertEqual(plan.steps(), [])
        self.assertTrue(plan.is_complete())  # vacuously true
        self.assertFalse(plan.has_failures())

    def test_plan_no_name(self):
        plan = AgentRunPlan()
        self.assertEqual(plan.name, "")

    def test_plan_description(self):
        plan = AgentRunPlan("task", description="A task description")
        self.assertEqual(plan.description, "A task description")

    def test_plan_description_default(self):
        plan = AgentRunPlan("task")
        self.assertEqual(plan.description, "")

    def test_steps_returns_copy(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        returned = plan.steps()
        returned.clear()
        self.assertEqual(plan.step_count(), 1)

    def test_plan_add_step_returns_step(self):
        plan = AgentRunPlan()
        step = plan.add_step("fetch", "Fetch data")
        self.assertIsInstance(step, PlanStep)
        self.assertEqual(step.name, "fetch")
        self.assertEqual(step.status, StepStatus.PENDING)

    def test_plan_add_step_duplicate_raises(self):
        plan = AgentRunPlan()
        plan.add_step("fetch")
        with self.assertRaises(KeyError):
            plan.add_step("fetch")

    def test_plan_add_step_empty_name_raises(self):
        plan = AgentRunPlan()
        with self.assertRaises(ValueError):
            plan.add_step("")

    def test_plan_add_multiple_steps(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.add_step("c")
        self.assertEqual(plan.step_count(), 3)
        self.assertEqual([s.name for s in plan.steps()], ["a", "b", "c"])

    def test_plan_add_step_with_metadata(self):
        plan = AgentRunPlan()
        step = plan.add_step("x", metadata={"priority": 1})
        self.assertEqual(step.metadata, {"priority": 1})

    def test_plan_add_step_copies_metadata(self):
        meta = {"priority": 1}
        plan = AgentRunPlan()
        step = plan.add_step("x", metadata=meta)
        meta["priority"] = 99
        self.assertEqual(step.metadata, {"priority": 1})


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TransitionTests(unittest.TestCase):
    def test_mark_running(self):
        plan = AgentRunPlan()
        plan.add_step("fetch")
        plan.mark_running("fetch")
        self.assertEqual(plan.get("fetch").status, StepStatus.RUNNING)

    def test_mark_done(self):
        plan = AgentRunPlan()
        plan.add_step("fetch")
        plan.mark_done("fetch", result="data")
        step = plan.get("fetch")
        self.assertEqual(step.status, StepStatus.DONE)
        self.assertEqual(step.result, "data")

    def test_mark_done_clears_error(self):
        plan = AgentRunPlan()
        plan.add_step("x")
        plan.mark_failed("x", error="oops")
        plan.mark_done("x")
        self.assertEqual(plan.get("x").error, "")

    def test_mark_failed(self):
        plan = AgentRunPlan()
        plan.add_step("fetch")
        plan.mark_failed("fetch", error="timeout")
        step = plan.get("fetch")
        self.assertEqual(step.status, StepStatus.FAILED)
        self.assertEqual(step.error, "timeout")

    def test_mark_skipped(self):
        plan = AgentRunPlan()
        plan.add_step("optional")
        plan.mark_skipped("optional", reason="not needed")
        step = plan.get("optional")
        self.assertEqual(step.status, StepStatus.SKIPPED)
        self.assertEqual(step.error, "not needed")

    def test_reset_step(self):
        plan = AgentRunPlan()
        plan.add_step("x")
        plan.mark_done("x", result="data")
        plan.reset_step("x")
        step = plan.get("x")
        self.assertEqual(step.status, StepStatus.PENDING)
        self.assertIsNone(step.result)
        self.assertEqual(step.error, "")

    def test_mark_running_missing_raises(self):
        plan = AgentRunPlan()
        with self.assertRaises(KeyError):
            plan.mark_running("ghost")

    def test_mark_done_missing_raises(self):
        plan = AgentRunPlan()
        with self.assertRaises(KeyError):
            plan.mark_done("ghost")

    def test_mark_failed_missing_raises(self):
        plan = AgentRunPlan()
        with self.assertRaises(KeyError):
            plan.mark_failed("ghost")

    def test_mark_skipped_missing_raises(self):
        plan = AgentRunPlan()
        with self.assertRaises(KeyError):
            plan.mark_skipped("ghost")

    def test_reset_step_missing_raises(self):
        plan = AgentRunPlan()
        with self.assertRaises(KeyError):
            plan.reset_step("ghost")

    def test_reset_step_keeps_metadata(self):
        plan = AgentRunPlan()
        plan.add_step("x", metadata={"k": 1})
        plan.mark_done("x", result="data")
        plan.reset_step("x")
        self.assertEqual(plan.get("x").metadata, {"k": 1})

    def test_reset_all(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_done("a", result="x")
        plan.mark_failed("b", error="boom")
        plan.reset()
        for step in plan.steps():
            self.assertEqual(step.status, StepStatus.PENDING)
            self.assertIsNone(step.result)
            self.assertEqual(step.error, "")
        self.assertEqual(plan.progress(), (0, 2))


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------


class QueryTests(unittest.TestCase):
    def test_get_step(self):
        plan = AgentRunPlan()
        plan.add_step("fetch", "Get data")
        step = plan.get("fetch")
        self.assertEqual(step.name, "fetch")
        self.assertEqual(step.description, "Get data")

    def test_get_step_missing_raises(self):
        plan = AgentRunPlan()
        with self.assertRaises(KeyError):
            plan.get("ghost")

    def test_progress_empty(self):
        plan = AgentRunPlan()
        self.assertEqual(plan.progress(), (0, 0))

    def test_progress_all_pending(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        self.assertEqual(plan.progress(), (0, 2))

    def test_progress_partial(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.add_step("c")
        plan.mark_done("a")
        plan.mark_failed("b", error="oops")
        self.assertEqual(plan.progress(), (2, 3))

    def test_is_complete_all_done(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_done("a")
        plan.mark_done("b")
        self.assertTrue(plan.is_complete())

    def test_is_complete_mixed_terminal(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.add_step("c")
        plan.mark_done("a")
        plan.mark_failed("b")
        plan.mark_skipped("c")
        self.assertTrue(plan.is_complete())

    def test_is_complete_pending_remains(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_done("a")
        self.assertFalse(plan.is_complete())

    def test_has_failures_true(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.mark_failed("a")
        self.assertTrue(plan.has_failures())

    def test_has_failures_false(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.mark_done("a")
        self.assertFalse(plan.has_failures())

    def test_current_step(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_running("b")
        self.assertEqual(plan.current_step().name, "b")

    def test_current_step_none(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        self.assertIsNone(plan.current_step())

    def test_next_pending(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_done("a")
        self.assertEqual(plan.next_pending().name, "b")

    def test_next_pending_none(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.mark_done("a")
        self.assertIsNone(plan.next_pending())

    def test_steps_by_status(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.add_step("c")
        plan.mark_done("a")
        plan.mark_done("b")
        done = plan.steps_by_status(StepStatus.DONE)
        self.assertEqual(len(done), 2)

    def test_pending_steps(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_done("a")
        pending = plan.pending_steps()
        self.assertEqual([s.name for s in pending], ["b"])

    def test_done_steps(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_done("a")
        done = plan.done_steps()
        self.assertEqual([s.name for s in done], ["a"])

    def test_failed_steps(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_failed("a", error="err1")
        plan.mark_done("b")
        failures = plan.failed_steps()
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0].name, "a")

    def test_skipped_steps(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_skipped("a", reason="n/a")
        skipped = plan.skipped_steps()
        self.assertEqual([s.name for s in skipped], ["a"])

    def test_summary_empty(self):
        plan = AgentRunPlan()
        self.assertEqual(
            plan.summary(),
            {
                "pending": 0,
                "running": 0,
                "done": 0,
                "failed": 0,
                "skipped": 0,
            },
        )

    def test_summary_counts(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        plan.add_step("b")
        plan.add_step("c")
        plan.add_step("d")
        plan.mark_done("a")
        plan.mark_done("b")
        plan.mark_failed("c")
        plan.mark_running("d")
        summary = plan.summary()
        self.assertEqual(summary["done"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["running"], 1)
        self.assertEqual(summary["pending"], 0)
        # Total of all buckets equals the step count.
        self.assertEqual(sum(summary.values()), plan.step_count())


# ---------------------------------------------------------------------------
# Rendering and serialization
# ---------------------------------------------------------------------------


class RenderTests(unittest.TestCase):
    def test_render_contains_step_names(self):
        plan = AgentRunPlan("My Task")
        plan.add_step("fetch", "Get data")
        plan.add_step("process")
        plan.mark_done("fetch", result="ok")
        output = plan.render()
        self.assertIn("fetch", output)
        self.assertIn("process", output)
        self.assertIn("My Task", output)

    def test_render_shows_progress(self):
        plan = AgentRunPlan("T")
        plan.add_step("a")
        plan.mark_done("a")
        output = plan.render()
        self.assertIn("1/1", output)

    def test_render_shows_error(self):
        plan = AgentRunPlan()
        plan.add_step("x")
        plan.mark_failed("x", error="timeout")
        output = plan.render()
        self.assertIn("timeout", output)

    def test_render_no_name_header(self):
        plan = AgentRunPlan()
        plan.add_step("a")
        output = plan.render()
        self.assertTrue(output.startswith("Plan [0/1]"))

    def test_render_custom_indent(self):
        plan = AgentRunPlan("T")
        plan.add_step("a", "do a")
        output = plan.render(indent="    ")
        self.assertIn("    ", output)

    def test_to_dict(self):
        plan = AgentRunPlan("task", description="A task")
        plan.add_step("a")
        plan.mark_done("a", result=42)
        d = plan.to_dict()
        self.assertEqual(d["name"], "task")
        self.assertEqual(d["description"], "A task")
        self.assertEqual(d["step_count"], 1)
        self.assertEqual(d["completed"], 1)
        self.assertTrue(d["is_complete"])
        self.assertFalse(d["has_failures"])
        self.assertEqual(len(d["steps"]), 1)
        self.assertEqual(d["steps"][0]["result"], 42)

    def test_to_dict_is_json_serialisable(self):
        import json

        plan = AgentRunPlan("task")
        plan.add_step("a", "do a", metadata={"n": 1})
        plan.mark_done("a", result="ok")
        # Should not raise.
        encoded = json.dumps(plan.to_dict())
        self.assertIn("\"name\"", encoded)

    def test_repr(self):
        plan = AgentRunPlan("task")
        plan.add_step("a")
        plan.add_step("b")
        plan.mark_done("a")
        r = repr(plan)
        self.assertIn("task", r)
        self.assertIn("1/2", r)


if __name__ == "__main__":
    unittest.main()
