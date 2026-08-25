---
name: zimaflow
description: "Use for zimaflow development workflow tasks: route new work, continue active changes, close with evidence, run doctor, or invoke a listed specialist capability."
---

# zimaflow

This is the generated host-agnostic Zimaflow runtime. It is the portable form of
the shared workflow source and is the workflow truth for any host that has no
dedicated Zimaflow Plugin. Do not edit this generated runtime and do not add
host-specific routing rules here.

The logical `<zimaflow-root>` is this directory. Before acting on a situation
below, read the corresponding packaged `SKILL.md` completely.

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

The included CLI is `bin/zimaflow`; use `bin/zimaflow doctor <host> --json` only
for read-only readiness evidence.

Read `references/Codex-Packaging-External-Dependencies.md` before assuming
OpenSpec or Superpowers is installed. Project initialization, dependency
installation and marketplace registration are outside this runtime. The packaged
CLI may run `runtime` lifecycle only with an explicitly injected safe temporary
install root; it never targets a real host runtime.

Licensing for this runtime is in `LICENSE`; third-party attribution for the
packaged OpenSpec helper Skills is in `THIRD_PARTY_NOTICES`.
