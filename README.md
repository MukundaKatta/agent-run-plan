# agent-run-plan

Lightweight structured plan with step status tracking for agent runs. Zero runtime dependencies, fully type-hinted (ships a `py.typed` marker).

Track steps through `pending → running → done / failed / skipped`.

## Install

```bash
pip install agent-run-plan
```

## Usage

```python
from agent_run_plan import AgentRunPlan

plan = AgentRunPlan("Summarise document")
plan.add_step("fetch",     "Fetch the document from URL")
plan.add_step("parse",     "Parse the raw content")
plan.add_step("summarise", "Produce a summary")
plan.add_step("save",      "Save to output file")

plan.mark_running("fetch")
plan.mark_done("fetch", result="downloaded 4096 bytes")
plan.mark_running("parse")
plan.mark_failed("parse", error="UnicodeDecodeError")

plan.progress()      # (1, 4) — completed, total
plan.has_failures()  # True
plan.is_complete()   # False

print(plan.render())
# Plan: Summarise document [1/4]
#   ✓ fetch — Fetch the document from URL
#   ✗ parse — Parse the raw content (UnicodeDecodeError)
#   ○ summarise — Produce a summary
#   ○ save — Save to output file
```

## Step status

| Status | Description | Terminal |
|--------|-------------|----------|
| `PENDING` | Not yet started | No |
| `RUNNING` | Currently executing | No |
| `DONE` | Completed successfully | Yes |
| `FAILED` | Completed with error | Yes |
| `SKIPPED` | Deliberately bypassed | Yes |

## AgentRunPlan API

```python
plan = AgentRunPlan("name", description="...")

# Add steps
plan.add_step("name", "description", metadata={...})

# Transitions
plan.mark_running("name")
plan.mark_done("name", result=value)
plan.mark_failed("name", error="message")
plan.mark_skipped("name", reason="not needed")
plan.reset_step("name")        # back to PENDING

# Query
plan.get("name")               # PlanStep, raises KeyError if missing
plan.steps()                   # list[PlanStep] in insertion order
plan.step_count()              # total steps
plan.progress()                # (completed, total)
plan.is_complete()             # True if all steps are terminal
plan.has_failures()            # True if any step is FAILED
plan.current_step()            # first RUNNING step or None
plan.next_pending()            # first PENDING step or None
plan.steps_by_status(status)   # filter by StepStatus
plan.pending_steps()           # shortcut for PENDING steps
plan.done_steps()              # shortcut for DONE steps
plan.failed_steps()            # shortcut for FAILED steps
plan.skipped_steps()           # shortcut for SKIPPED steps
plan.summary()                 # {"pending": n, "running": n, ...}

# Bulk operations
plan.reset()                   # reset every step back to PENDING

# Output
plan.render()                  # ASCII progress report
plan.to_dict()                 # JSON-serialisable dict
```

`add_step` raises `ValueError` on an empty name and `KeyError` on a
duplicate name. The other `mark_*`/`reset_step`/`get` methods raise
`KeyError` if the named step does not exist.

`summary()` always returns every status as a key (defaulting to `0`), so
it is safe to use directly in logging without guarding for missing keys:

```python
plan.summary()
# {'pending': 1, 'running': 0, 'done': 2, 'failed': 1, 'skipped': 0}
```

## PlanStep fields

| Field | Description |
|-------|-------------|
| `name` | Unique step identifier |
| `description` | Human-readable description |
| `status` | `StepStatus` enum value |
| `result` | Output from the step (if DONE) |
| `error` | Error message (if FAILED/SKIPPED) |
| `metadata` | Arbitrary key/value store |
| `is_terminal` | `True` if DONE/FAILED/SKIPPED |
| `succeeded` | `True` if DONE |
| `failed` | `True` if FAILED |
| `skipped` | `True` if SKIPPED |

## Development

The test suite uses only the Python standard library, so no third-party
packages are required to run it:

```bash
python -m unittest discover -s tests -v
```

Optional linting (requires the `dev` extra):

```bash
pip install -e ".[dev]"
ruff check src tests
```

## License

MIT
