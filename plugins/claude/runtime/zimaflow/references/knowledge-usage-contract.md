# Knowledge Usage Contract

> Type: public runtime reference.
> Purpose: define the knowledge loop, the ledger event contract, and the human
> review rules that govern promotion and cleanup.

The loop is:

1. **Load** relevant knowledge, using `knowledge-anchor-guide.md` for the rules.
2. **Record** the load or application through `zimaflow knowledge-record` into the
   user-level global ledger.
3. **Review** usage during session close.
4. **Promote, update, or deprecate** only after user confirmation.

## Knowledge ID Format

Every reusable lesson that participates in the ledger must include:

```markdown
- **ID**：kf-YYYYMMDD-short-slug
```

Rules:

- IDs are stable and do not change when headings are edited.
- Before adding a new ID, search existing lessons and the ledger for duplicates.
- Project-level `lessons.md` uses the same format.

## Where Events Live

Real events live in `ZIMAFLOW_DATA_HOME/knowledge-usage-ledger.jsonl` (default
`~/.zimaflow/data/knowledge-usage-ledger.jsonl`). The capability root is
immutable: Skills call `zimaflow knowledge-record` and never append to a file
inside the installed runtime.

`references/knowledge-usage-ledger.schema.jsonl` is the packaged schema and
example artifact. It contains only `schema-example-` events and no real usage.

## Ledger Event Types

| Event type | Meaning | Promotion weight |
|------------|---------|------------------|
| `loaded` | The Agent read the entry because an anchor or Skill required it. | Low |
| `cited` | The Agent referenced the entry in a plan, review, or handover. | Medium |
| `applied` | The entry changed an implementation, routing, or review decision. | High |
| `challenged` | The entry looked stale, misleading, or contradicted by current evidence. | Negative / review |
| `stale_review` | A periodic review marked the entry as inactive in the review window. | Review only |

Minimum fields:

```json
{"event_id":"use-YYYYMMDD-NNN","knowledge_id":"kf-YYYYMMDD-short-slug","event_type":"loaded","project":"project-name","session":"short task summary","stage":"routing","trigger":"anchor or reason","reason":"why this knowledge was read or used","timestamp":"YYYY-MM-DDTHH:MM:SS+08:00"}
```

Record them with the CLI so field validation, timestamps, IDs, permissions and
locking stay host-independent:

```bash
zimaflow knowledge-record \
  --knowledge-id kf-YYYYMMDD-short-slug --event-type loaded \
  --project project-name --session "short task summary" --stage routing \
  --trigger "anchor or reason" --reason "why this knowledge was read or used" \
  --json
```

## Human Review Rules

- Ledger evidence can suggest an occurrence count, level promotion, or cleanup.
- `learn` must ask before changing lesson content, level, or Skill rules.
- A `loaded` event alone is not enough to promote knowledge.
- `applied` events across separate sessions or projects are strong promotion evidence.
- `challenged` events trigger review before further promotion.

## Stale Review and Deprecation

```bash
zimaflow stale-review
zimaflow stale-review --json
```

The command only lists candidates. It does not append ledger events, mark
lessons deprecated, move files, or delete anything.

A knowledge entry becomes a cleanup candidate when:

- it has no `cited` or `applied` events in the last 90 days;
- it is not level `rule`, unless the user explicitly includes rules in cleanup;
- it is not newly created during the current review window.

Cleanup flow:

1. Present candidates to the user with last usage evidence.
2. After user confirmation, append a `stale_review` event with
   `zimaflow knowledge-record` for each accepted candidate.
3. If confirmed, mark the lesson as deprecated or move it to an archive section.
4. If rejected, append a `cited` event with reason `manual keep`.

Never physically delete a lesson without an explicit user request.
