# Knowledge Anchor Guide

> Type: public runtime reference.
> Purpose: define how an Agent decides which knowledge to load before routing,
> planning, or implementation.
>
> This file is a **schema and rule set with generic examples**. It is not an
> anchor table. Your own anchors live in your own knowledge base and are never
> shipped with the runtime, so upgrading Zimaflow never overwrites them and
> packaging never publishes them.

## Anchor Rules

- Match by meaning, not exact wording.
- Load at most 3 mapped entries unless the user explicitly asks for broader research.
- If the matched area is high-risk but no knowledge exists, record a learn
  candidate instead of inventing a rule.
- When an entry is only loosely related, record `event_type: "loaded"` but do not
  count it as promotion evidence unless it was truly applied.
- Record every load through `zimaflow knowledge-record`. Never append runtime
  events to the capability root.

## Anchor Entry Schema

Each anchor is one row with four fields:

| Field | Meaning |
|-------|---------|
| `Anchor` | The trigger phrases or situation, written the way it shows up in a request or a diff. |
| `Load` | One or more stable knowledge IDs (`kf-YYYYMMDD-short-slug`). |
| `Stage` | Where the anchor fires: `routing`, `planning`, `implementation`, `verification`. |
| `Why` | How the loaded knowledge changes a decision. Not a summary of the lesson. |

## Generic Example

These two rows are illustrative only. Replace them; do not treat them as
Zimaflow's recommended knowledge.

| Anchor | Load | Stage | Why |
|--------|------|-------|-----|
| third-party payload shape / frontend-backend contract / double-encoded JSON | `kf-YYYYMMDD-contract-before-ui` | routing, planning | A contract consumer should not absorb a dirty provider payload before the owning layer is diagnosed. |
| generated markup is unstable / layout drifts between runs | `kf-YYYYMMDD-prompt-constraints` | planning | Generated structured output needs explicit constraints and lower single-pass complexity. |

## Where Your Anchor Table Lives

Keep your own anchor table with the knowledge it points at, not inside the
installed runtime:

- project scope: `<docs_dir>/lessons.md` plus a project anchor section;
- cross-project scope: `ZIMAFLOW_DATA_HOME/lessons-common.md` (default
  `~/.zimaflow/data/lessons-common.md`), which you
  create on first use and which packaging never provides or overwrites.

## Adding Anchors

Add an anchor only when:

- the mapped knowledge has a stable `ID`;
- the trigger is specific enough to avoid broad over-loading;
- the reason explains how the knowledge changes a decision.

If an anchor repeatedly fires but the mapped entry is not useful, record a
`challenged` event and propose an anchor update during session closure.
