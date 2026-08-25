---
name: zimaflow
description: "Use for zimaflow development workflow tasks: route new work, continue active changes, close with evidence, run doctor, or invoke a listed specialist capability."
---

# zimaflow

This is the generated Claude Code entry adapter. The packaged shared runtime is the workflow truth; do not edit this wrapper or add Claude-specific routing logic.

For this Plugin, the logical `<zimaflow-root>` is `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow`. Before acting on a situation below, read the corresponding packaged `SKILL.md` completely.

| Situation | Packaged Skill |
| --- | --- |
| New feature, task, bugfix, or routing | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/sdd-router/SKILL.md` |
| Requirement brief or PRD contract | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/requirement-contract/SKILL.md` |
| Full-mode route decision | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/route-decision-recorder/SKILL.md` |
| Task breakdown and estimates | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/task-planning/SKILL.md` |
| Existing project onboarding | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/legacy-project-onboarding/SKILL.md` |
| Handover or continuation | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/handover-manager/SKILL.md` |
| Session closeout reconciliation | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/session-close-reconciler/SKILL.md` |
| Spec compliance review | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/spec-compliance-check/SKILL.md` |
| Experience candidate handling | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/learn/SKILL.md` |
| OpenSpec implementation handoff | `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/openspec-superpowers-bridge/SKILL.md` |
| OpenSpec propose/explore/apply/archive | model-only wrappers backed by `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/.claude/skills/` |

The Plugin CLI entry is `${CLAUDE_PLUGIN_ROOT}/bin/zimaflow`. Use `doctor claude-code --json` only for read-only readiness evidence.

Read `${CLAUDE_PLUGIN_ROOT}/runtime/zimaflow/references/Codex-Packaging-External-Dependencies.md` before assuming OpenSpec or Superpowers is installed. Project initialization, dependency installation and marketplace registration remain outside this adapter.
