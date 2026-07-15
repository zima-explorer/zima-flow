# 示例：从一句需求到 handover

示例需求：

```text
Add a tiny todo list CLI that can add, list, and complete tasks.
```

这个 demo 是一次纸面演练，用来展示用户在 v0.1 主链路中应看到的产物。

## 1. 需求 brief

打开 `project-docs/demo-cli/docs/Requirements/2026-07-11-todo-cli-brief.md`。

brief 会记录：

- 目标
- 范围
- 不做什么
- 验收标准（优先 Given / When / Then 三段式，便于下游派生测试）
- 假设与默认值
- 风险

## 2. 任务计划

打开 `project-docs/demo-cli/docs/Tasks/2026-07-11-todo-cli-tasks.md`。

任务计划会把 first slice 控制在一次实现 session 可处理的范围内。

## 3. OpenSpec change 骨架

打开 `project-docs/demo-cli/openspec/changes/add-todo-cli/`。

骨架包含：

- `proposal.md`
- `design.md`
- `tasks.md`

## 4. 收口和 handover

打开：

- `project-docs/demo-cli/docs/Closing/2026-07-11-todo-cli-closing.md`
- `project-docs/demo-cli/docs/Handover/2026-07-11-handover-todo-cli.md`

这些文件展示下一次 session 开始前应该保存的上下文。
