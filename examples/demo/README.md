# 示例：从一句需求到 handover

示例需求：

```text
Add a tiny todo list CLI that can add, list, and complete tasks.
```

这个 demo 是一次纸面演练，用来展示用户在 v0.1 主链路中应看到的产物。

## 三个 demo 的关系

公开版有三个 demo 入口，建议按这个顺序看：

| 入口 | 看什么 | 一条命令 |
|------|--------|----------|
| **本页** `examples/demo/` | **纸面演练**：产物长什么样 | `examples/demo/run-demo.sh` |
| [`case-evidence-closure/`](case-evidence-closure/README.md) | **轻量模式**：一次小需求怎么把证据收口（可复跑的验证、独立落盘的合规报告、逐项对账的收口清单） | `examples/demo/case-evidence-closure/run-case.sh` |
| [`case-cross-session/`](case-cross-session/README.md) | **完整模式**：一次小需求怎么跨 session 用 `state` / `recall` / `handover` 接住上下文 | `examples/demo/case-cross-session/run-case.sh` |

后两个都有真实代码改动和真实测试证据，载体是同一个 todo CLI，但走的是**不同重量的路径**：

- `case-evidence-closure` 走**轻量模式**——需求小、纯读、不改持久化格式，风险低，**不写 OpenSpec 三件套**。规范的作用由 brief 的 Given/When/Then 承担，计划的作用由轻量任务台账承担。
- `case-cross-session` 走**完整模式**——需要规范和设计留痕，才生成 OpenSpec 三件套。

**zimaflow 的默认动作不是把所有事流程化。** 看到两个案例产物数量不同，那是档位不同，不是其中一个做得不完整。

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
