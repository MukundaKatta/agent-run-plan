"""Tests for agent_run_plan."""

from __future__ import annotations

import pytest

from agent_run_plan import AgentRunPlan, PlanStep, StepStatus

# ---------------------------------------------------------------------------
# StepStatus enum
# ---------------------------------------------------------------------------


def test_step_status_values():
    assert StepStatus.PENDING.value == "pending"
    assert StepStatus.RUNNING.value == "running"
    assert StepStatus.DONE.value == "done"
    assert StepStatus.FAILED.value == "failed"
    assert StepStatus.SKIPPED.value == "skipped"


# ---------------------------------------------------------------------------
# PlanStep
# ---------------------------------------------------------------------------


def test_plan_step_defaults():
    step = PlanStep(name="fetch")
    assert step.name == "fetch"
    assert step.description == ""
    assert step.status == StepStatus.PENDING
    assert step.result is None
    assert step.error == ""
    assert step.metadata == {}


def test_plan_step_is_terminal_pending():
    step = PlanStep(name="x", status=StepStatus.PENDING)
    assert step.is_terminal is False


def test_plan_step_is_terminal_running():
    step = PlanStep(name="x", status=StepStatus.RUNNING)
    assert step.is_terminal is False


def test_plan_step_is_terminal_done():
    step = PlanStep(name="x", status=StepStatus.DONE)
    assert step.is_terminal is True


def test_plan_step_is_terminal_failed():
    step = PlanStep(name="x", status=StepStatus.FAILED)
    assert step.is_terminal is True


def test_plan_step_is_terminal_skipped():
    step = PlanStep(name="x", status=StepStatus.SKIPPED)
    assert step.is_terminal is True


def test_plan_step_succeeded():
    step = PlanStep(name="x", status=StepStatus.DONE)
    assert step.succeeded is True


def test_plan_step_succeeded_false():
    step = PlanStep(name="x", status=StepStatus.FAILED)
    assert step.succeeded is False


def test_plan_step_failed():
    step = PlanStep(name="x", status=StepStatus.FAILED)
    assert step.failed is True


def test_plan_step_skipped():
    step = PlanStep(name="x", status=StepStatus.SKIPPED)
    assert step.skipped is True


def test_plan_step_to_dict():
    step = PlanStep(
        name="fetch",
        description="Get data",
        status=StepStatus.DONE,
        result="ok",
        error="",
        metadata={"url": "https://example.com"},
    )
    d = step.to_dict()
    assert d["name"] == "fetch"
    assert d["description"] == "Get data"
    assert d["status"] == "done"
    assert d["result"] == "ok"
    assert d["metadata"] == {"url": "https://example.com"}


def test_plan_step_repr():
    step = PlanStep(name="fetch", status=StepStatus.RUNNING)
    r = repr(step)
    assert "fetch" in r
    assert "running" in r


# ---------------------------------------------------------------------------
# AgentRunPlan — creation
# ---------------------------------------------------------------------------


def test_plan_empty():
    plan = AgentRunPlan("task")
    assert plan.name == "task"
    assert plan.step_count() == 0
    assert len(plan) == 0
    assert plan.steps() == []
    assert plan.is_complete() is True  # vacuously true
    assert plan.has_failures() is False


def test_plan_no_name():
    plan = AgentRunPlan()
    assert plan.name == ""


def test_plan_description():
    plan = AgentRunPlan("task", description="A task description")
    assert plan.description == "A task description"


def test_plan_description_default():
    plan = AgentRunPlan("task")
    assert plan.description == ""


def test_steps_returns_copy():
    plan = AgentRunPlan()
    plan.add_step("a")
    returned = plan.steps()
    returned.clear()
    assert plan.step_count() == 1


def test_plan_add_step_returns_step():
    plan = AgentRunPlan()
    step = plan.add_step("fetch", "Fetch data")
    assert isinstance(step, PlanStep)
    assert step.name == "fetch"
    assert step.status == StepStatus.PENDING


def test_plan_add_step_duplicate_raises():
    plan = AgentRunPlan()
    plan.add_step("fetch")
    with pytest.raises(KeyError):
        plan.add_step("fetch")


def test_plan_add_multiple_steps():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.add_step("c")
    assert plan.step_count() == 3
    assert [s.name for s in plan.steps()] == ["a", "b", "c"]


def test_plan_add_step_with_metadata():
    plan = AgentRunPlan()
    step = plan.add_step("x", metadata={"priority": 1})
    assert step.metadata == {"priority": 1}


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def test_mark_running():
    plan = AgentRunPlan()
    plan.add_step("fetch")
    plan.mark_running("fetch")
    assert plan.get("fetch").status == StepStatus.RUNNING


def test_mark_done():
    plan = AgentRunPlan()
    plan.add_step("fetch")
    plan.mark_done("fetch", result="data")
    step = plan.get("fetch")
    assert step.status == StepStatus.DONE
    assert step.result == "data"


def test_mark_done_clears_error():
    plan = AgentRunPlan()
    plan.add_step("x")
    plan.mark_failed("x", error="oops")
    plan.mark_done("x")
    assert plan.get("x").error == ""


def test_mark_failed():
    plan = AgentRunPlan()
    plan.add_step("fetch")
    plan.mark_failed("fetch", error="timeout")
    step = plan.get("fetch")
    assert step.status == StepStatus.FAILED
    assert step.error == "timeout"


def test_mark_skipped():
    plan = AgentRunPlan()
    plan.add_step("optional")
    plan.mark_skipped("optional", reason="not needed")
    step = plan.get("optional")
    assert step.status == StepStatus.SKIPPED
    assert step.error == "not needed"


def test_reset_step():
    plan = AgentRunPlan()
    plan.add_step("x")
    plan.mark_done("x", result="data")
    plan.reset_step("x")
    step = plan.get("x")
    assert step.status == StepStatus.PENDING
    assert step.result is None
    assert step.error == ""


def test_mark_running_missing_raises():
    plan = AgentRunPlan()
    with pytest.raises(KeyError):
        plan.mark_running("ghost")


def test_mark_done_missing_raises():
    plan = AgentRunPlan()
    with pytest.raises(KeyError):
        plan.mark_done("ghost")


def test_mark_failed_missing_raises():
    plan = AgentRunPlan()
    with pytest.raises(KeyError):
        plan.mark_failed("ghost")


def test_mark_skipped_missing_raises():
    plan = AgentRunPlan()
    with pytest.raises(KeyError):
        plan.mark_skipped("ghost")


def test_reset_step_missing_raises():
    plan = AgentRunPlan()
    with pytest.raises(KeyError):
        plan.reset_step("ghost")


def test_reset_step_keeps_metadata():
    plan = AgentRunPlan()
    plan.add_step("x", metadata={"k": 1})
    plan.mark_done("x", result="data")
    plan.reset_step("x")
    assert plan.get("x").metadata == {"k": 1}


# ---------------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------------


def test_get_step():
    plan = AgentRunPlan()
    plan.add_step("fetch", "Get data")
    step = plan.get("fetch")
    assert step.name == "fetch"
    assert step.description == "Get data"


def test_get_step_missing_raises():
    plan = AgentRunPlan()
    with pytest.raises(KeyError):
        plan.get("ghost")


def test_progress_empty():
    plan = AgentRunPlan()
    assert plan.progress() == (0, 0)


def test_progress_all_pending():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    assert plan.progress() == (0, 2)


def test_progress_partial():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.add_step("c")
    plan.mark_done("a")
    plan.mark_failed("b", error="oops")
    assert plan.progress() == (2, 3)


def test_is_complete_all_done():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.mark_done("a")
    plan.mark_done("b")
    assert plan.is_complete() is True


def test_is_complete_mixed_terminal():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.add_step("c")
    plan.mark_done("a")
    plan.mark_failed("b")
    plan.mark_skipped("c")
    assert plan.is_complete() is True


def test_is_complete_pending_remains():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.mark_done("a")
    assert plan.is_complete() is False


def test_has_failures_true():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.mark_failed("a")
    assert plan.has_failures() is True


def test_has_failures_false():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.mark_done("a")
    assert plan.has_failures() is False


def test_current_step():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.mark_running("b")
    assert plan.current_step().name == "b"


def test_current_step_none():
    plan = AgentRunPlan()
    plan.add_step("a")
    assert plan.current_step() is None


def test_next_pending():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.mark_done("a")
    assert plan.next_pending().name == "b"


def test_next_pending_none():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.mark_done("a")
    assert plan.next_pending() is None


def test_steps_by_status():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.add_step("c")
    plan.mark_done("a")
    plan.mark_done("b")
    done = plan.steps_by_status(StepStatus.DONE)
    assert len(done) == 2


def test_failed_steps():
    plan = AgentRunPlan()
    plan.add_step("a")
    plan.add_step("b")
    plan.mark_failed("a", error="err1")
    plan.mark_done("b")
    failures = plan.failed_steps()
    assert len(failures) == 1
    assert failures[0].name == "a"


# ---------------------------------------------------------------------------
# Rendering and serialization
# ---------------------------------------------------------------------------


def test_render_contains_step_names():
    plan = AgentRunPlan("My Task")
    plan.add_step("fetch", "Get data")
    plan.add_step("process")
    plan.mark_done("fetch", result="ok")
    output = plan.render()
    assert "fetch" in output
    assert "process" in output
    assert "My Task" in output


def test_render_shows_progress():
    plan = AgentRunPlan("T")
    plan.add_step("a")
    plan.mark_done("a")
    output = plan.render()
    assert "1/1" in output


def test_render_shows_error():
    plan = AgentRunPlan()
    plan.add_step("x")
    plan.mark_failed("x", error="timeout")
    output = plan.render()
    assert "timeout" in output


def test_to_dict():
    plan = AgentRunPlan("task", description="A task")
    plan.add_step("a")
    plan.mark_done("a", result=42)
    d = plan.to_dict()
    assert d["name"] == "task"
    assert d["description"] == "A task"
    assert d["step_count"] == 1
    assert d["completed"] == 1
    assert d["is_complete"] is True
    assert d["has_failures"] is False
    assert len(d["steps"]) == 1
    assert d["steps"][0]["result"] == 42


def test_repr():
    plan = AgentRunPlan("task")
    plan.add_step("a")
    plan.add_step("b")
    plan.mark_done("a")
    r = repr(plan)
    assert "task" in r
    assert "1/2" in r
