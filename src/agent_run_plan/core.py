"""Lightweight structured plan with step status tracking for agent runs.

Example::

    from agent_run_plan import AgentRunPlan

    plan = AgentRunPlan("Summarise document")
    plan.add_step("fetch", "Fetch the document from URL")
    plan.add_step("parse", "Parse the raw content")
    plan.add_step("summarise", "Produce a summary")
    plan.add_step("save", "Save to output file")

    plan.mark_running("fetch")
    plan.mark_done("fetch", result="downloaded 4096 bytes")
    plan.mark_running("parse")
    plan.mark_failed("parse", error="UnicodeDecodeError")

    plan.progress()      # (1, 4)
    plan.has_failures()  # True
    plan.is_complete()   # False
    print(plan.render())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepStatus(str, Enum):
    """Lifecycle status of a plan step."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


_TERMINAL: frozenset[StepStatus] = frozenset(
    [StepStatus.DONE, StepStatus.FAILED, StepStatus.SKIPPED]
)

_STATUS_ICON: dict[StepStatus, str] = {
    StepStatus.PENDING: "○",
    StepStatus.RUNNING: "◉",
    StepStatus.DONE: "✓",
    StepStatus.FAILED: "✗",
    StepStatus.SKIPPED: "⊘",
}


@dataclass
class PlanStep:
    """A single step within an :class:`AgentRunPlan`.

    Attributes:
        name:        Unique step identifier.
        description: Human-readable description.
        status:      Current lifecycle status.
        result:      Output from the step if it succeeded.
        error:       Error message if the step failed.
        metadata:    Arbitrary key/value store.
    """

    name: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        """``True`` if the step has reached a final state."""
        return self.status in _TERMINAL

    @property
    def succeeded(self) -> bool:
        """``True`` if the step completed successfully."""
        return self.status == StepStatus.DONE

    @property
    def failed(self) -> bool:
        """``True`` if the step failed."""
        return self.status == StepStatus.FAILED

    @property
    def skipped(self) -> bool:
        """``True`` if the step was skipped."""
        return self.status == StepStatus.SKIPPED

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "metadata": dict(self.metadata),
        }

    def __repr__(self) -> str:
        icon = _STATUS_ICON.get(self.status, "?")
        return f"PlanStep({icon} {self.name!r}, status={self.status.value!r})"


class AgentRunPlan:
    """Track progress of a multi-step agent run.

    Example::

        plan = AgentRunPlan("My task")
        plan.add_step("step_1", "Do something")
        plan.add_step("step_2", "Do something else")

        plan.mark_running("step_1")
        plan.mark_done("step_1", result="value")
        plan.mark_skipped("step_2", reason="not needed")

        plan.is_complete()    # True
        plan.has_failures()   # False
        plan.progress()       # (2, 2) — completed, total
    """

    def __init__(self, name: str = "", *, description: str = "") -> None:
        self._name = name
        self._description = description
        self._steps: list[PlanStep] = []
        self._step_index: dict[str, int] = {}

    @property
    def name(self) -> str:
        """Plan name."""
        return self._name

    @property
    def description(self) -> str:
        """Plan description."""
        return self._description

    # ------------------------------------------------------------------
    # Adding steps
    # ------------------------------------------------------------------

    def add_step(
        self,
        name: str,
        description: str = "",
        *,
        metadata: dict[str, Any] | None = None,
    ) -> PlanStep:
        """Append a new pending step to the plan.

        Args:
            name:        Unique step name.
            description: Human-readable description.
            metadata:    Optional key/value metadata.

        Returns:
            The new :class:`PlanStep`.

        Raises:
            KeyError: If *name* is already present.
        """
        if name in self._step_index:
            raise KeyError(f"Step already exists: {name!r}")
        step = PlanStep(
            name=name,
            description=description,
            metadata=dict(metadata) if metadata else {},
        )
        self._step_index[name] = len(self._steps)
        self._steps.append(step)
        return step

    # ------------------------------------------------------------------
    # Status transitions
    # ------------------------------------------------------------------

    def mark_running(self, name: str) -> None:
        """Transition *name* to RUNNING.

        Raises:
            KeyError: If step not found.
        """
        self._get(name).status = StepStatus.RUNNING

    def mark_done(self, name: str, *, result: Any = None) -> None:
        """Transition *name* to DONE.

        Args:
            name:   Step name.
            result: Optional result to store.
        """
        step = self._get(name)
        step.status = StepStatus.DONE
        step.result = result
        step.error = ""

    def mark_failed(self, name: str, *, error: str = "") -> None:
        """Transition *name* to FAILED.

        Args:
            name:  Step name.
            error: Optional error message to store.
        """
        step = self._get(name)
        step.status = StepStatus.FAILED
        step.error = error

    def mark_skipped(self, name: str, *, reason: str = "") -> None:
        """Transition *name* to SKIPPED.

        Args:
            name:   Step name.
            reason: Optional reason stored in ``error`` field.
        """
        step = self._get(name)
        step.status = StepStatus.SKIPPED
        step.error = reason

    def reset_step(self, name: str) -> None:
        """Reset *name* back to PENDING, clearing result and error."""
        step = self._get(name)
        step.status = StepStatus.PENDING
        step.result = None
        step.error = ""

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get(self, name: str) -> PlanStep:
        """Return the step with *name*.

        Raises:
            KeyError: If not found.
        """
        return self._get(name)

    def steps(self) -> list[PlanStep]:
        """All steps in insertion order."""
        return list(self._steps)

    def step_count(self) -> int:
        """Total number of steps."""
        return len(self._steps)

    def progress(self) -> tuple[int, int]:
        """Return ``(completed, total)`` where *completed* counts terminal steps."""
        completed = sum(1 for s in self._steps if s.is_terminal)
        return completed, len(self._steps)

    def is_complete(self) -> bool:
        """``True`` if every step has reached a terminal state."""
        return all(s.is_terminal for s in self._steps)

    def has_failures(self) -> bool:
        """``True`` if any step is in FAILED state."""
        return any(s.failed for s in self._steps)

    def current_step(self) -> PlanStep | None:
        """Return the first RUNNING step, or ``None``."""
        for s in self._steps:
            if s.status == StepStatus.RUNNING:
                return s
        return None

    def next_pending(self) -> PlanStep | None:
        """Return the first PENDING step, or ``None``."""
        for s in self._steps:
            if s.status == StepStatus.PENDING:
                return s
        return None

    def steps_by_status(self, status: StepStatus) -> list[PlanStep]:
        """All steps with the given *status*."""
        return [s for s in self._steps if s.status == status]

    def failed_steps(self) -> list[PlanStep]:
        """All steps in FAILED state."""
        return self.steps_by_status(StepStatus.FAILED)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, *, indent: str = "  ") -> str:
        """Render the plan as a human-readable ASCII report.

        Returns:
            Multi-line string.
        """
        done, total = self.progress()
        if self._name:
            header = f"Plan: {self._name} [{done}/{total}]"
        else:
            header = f"Plan [{done}/{total}]"
        lines = [header]
        for step in self._steps:
            icon = _STATUS_ICON.get(step.status, "?")
            line = f"{indent}{icon} {step.name}"
            if step.description:
                line += f" — {step.description}"
            if step.error:
                line += f" ({step.error})"
            lines.append(line)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        done, total = self.progress()
        return {
            "name": self._name,
            "description": self._description,
            "step_count": total,
            "completed": done,
            "is_complete": self.is_complete(),
            "has_failures": self.has_failures(),
            "steps": [s.to_dict() for s in self._steps],
        }

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self._steps)

    def __repr__(self) -> str:
        done, total = self.progress()
        return f"AgentRunPlan({self._name!r}, {done}/{total} steps)"

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get(self, name: str) -> PlanStep:
        idx = self._step_index.get(name)
        if idx is None:
            raise KeyError(f"Step not found: {name!r}")
        return self._steps[idx]
