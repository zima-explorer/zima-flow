# Workload Estimation Baseline

> Type: public runtime reference.
> Purpose: give `task-planning` a starting estimate per task type.
>
> These are **generic medians**, not measurements from any particular team or
> project. Treat them as a starting point and calibrate against your own data.
>
> Project overrides and your calibration history belong in
> `<docs_dir>/project-workload-overrides.md`, which is your own document. This
> packaged file stays static so an upgrade never overwrites your calibration and
> packaging never publishes it.

## Backend

| Task type | Baseline | Notes |
|-----------|----------|-------|
| New standard CRUD endpoint (single table) | 3h | route + service + basic validation |
| New complex endpoint (multi-table / transactional) | 5h | transaction handling, error compensation |
| Modify an existing endpoint (field or logic change) | 1-2h | depends on blast radius |
| New middleware / interceptor | 2h | auth, logging, rate limiting |
| Database DDL change (add table or column) | 1h | includes migration script |
| Database DDL change (restructure) | 2-3h | needs a data migration plan |
| External service integration (SDK / API) | 4h | wrapper, error handling, retries |
| File upload / download (object storage) | 3h | streaming, size limits |
| Scheduled job / background worker | 3h | includes idempotency design |
| Bug fix (reproduction known) | 0.5-1h | clear repro path |
| Bug fix (needs investigation) | 2-4h | log analysis or debugging |

## Frontend

| Task type | Baseline | Notes |
|-----------|----------|-------|
| Simple UI adjustment (style / copy) | 0.5h | no logic |
| New presentational component | 1h | no complex interaction |
| New form component (with validation) | 2-3h | client validation, field linkage |
| New list page (filter and sort) | 3-4h | store plus API wiring |
| New detail page or modal | 2h | |
| New complex interactive component | 4h | drag and drop, rich text, charts |
| Information architecture rework | 4-6h | no new features, structure only |
| Wire up a new API endpoint | 1h | includes type definitions |
| Responsive adaptation | 1-2h | mobile and multi-resolution |

## Testing

| Task type | Baseline | Notes |
|-----------|----------|-------|
| Unit tests (single module) | 1h | happy path plus error paths |
| API smoke test | 1h | main flow only |
| Integration test (end to end) | 2-3h | includes data setup and teardown |
| Additional cases on an existing harness | 0.5h per case | |

## Infrastructure / DevOps

| Task type | Baseline | Notes |
|-----------|----------|-------|
| Container image build / update | 1h | |
| CI/CD configuration change | 1-2h | |
| Environment variable / config change | 0.5h | |
| Deploy to a test environment | 1h | includes verification |
| Deploy to production | 1-2h | includes rollback preparation |

## Documentation / Other

| Task type | Baseline | Notes |
|-----------|----------|-------|
| API documentation update | 0.5-1h | |
| README / getting-started update | 0.5h | |
| Technical design document | 2-3h | includes option comparison and diagrams |
| Code review | 1h | scales with change size |

## How To Use

- Baselines cover development plus self-testing. They exclude waiting time such
  as review queues or deployment slots.
- If a task clearly exceeds its baseline, say why in the estimate notes.
- Baselines are medians. Raise them 30-50% for high-complexity codebases.
- At each retrospective, compare actual against estimate. Record any entry that
  drifts more than 50% in `<docs_dir>/project-workload-overrides.md`, using the
  columns: date, entry, old baseline, actual, adjusted, reason.
