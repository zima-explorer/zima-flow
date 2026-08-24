---
name: zimaflow
description: "Use for zimaflow development workflow tasks: route new work, continue active changes, close with evidence, run doctor, or invoke a listed specialist capability."
---

# zimaflow

This is a generated Codex Plugin wrapper. Its source of truth is the internal zimaflow source; do not edit this generated package.

Use the following packaged Skills for workflow behavior. They remain the shared capability source for Codex and WorkBuddy; do not create host-specific routing rules here.

| Situation | Packaged Skill |
| --- | --- |
| New feature, task, bugfix, or routing | `sdd-router/SKILL.md` |
| Requirement brief or PRD contract | `requirement-contract/SKILL.md` |
| Full-mode route decision | `route-decision-recorder/SKILL.md` |
| Task breakdown and estimates | `task-planning/SKILL.md` |
| Existing project onboarding | `legacy-project-onboarding/SKILL.md` |
| Handover or continuation | `handover-manager/SKILL.md` |
| Session closeout reconciliation | `session-close-reconciler/SKILL.md` |
| Spec compliance review | `spec-compliance-check/SKILL.md` |
| Experience candidate handling | `learn/SKILL.md` |
| OpenSpec implementation handoff | `openspec-superpowers-bridge/SKILL.md` |
| OpenSpec propose/explore/apply/archive | `.claude/skills/` |

The included CLI is `bin/zimaflow`. Before a host action needs diagnostic evidence, use `bin/zimaflow doctor codex --json`; it only reports readiness and never installs or repairs.

Read `references/Codex-Packaging-External-Dependencies.md` before assuming OpenSpec or Superpowers is installed. Project initialization, dependency installation and marketplace registration are outside this package. The packaged CLI may run `runtime` lifecycle only with an explicitly injected safe temporary install root; it never targets a real host runtime.
