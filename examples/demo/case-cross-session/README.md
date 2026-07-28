# 案例：一次跨 session 的小需求如何恢复上下文

这个案例比 [`examples/demo`](../README.md) 的纸面演练更进一步：它有**真实可跑的代码改动**、**真实的测试证据**，并演示 `state` / `recall` / `handover` 如何在两次 session 之间接住上下文。

## 需求

```text
给已有的本地 todo CLI 增加「可配置文件路径」。
```

一个真实但很小的增量：让用户能用 `--file` 或 `TODO_FILE` 指定 todo 文件位置，同时保持默认行为不变。

## 为什么要跨 session

小需求也常常不在一次对话里做完。本案例把它拆成两段：

- **Session 1**：确认 brief、拆任务、实现 `--file` / `TODO_FILE`（T1–T3），写 handover 后中断。
- **Session 2**：先 `recall` 恢复上下文，再补测试、跑 verify、收口（T4–T6）。

## 一条命令跑完

```bash
examples/demo/case-cross-session/run-case.sh
```

它会真实执行：

1. `app/test-todo.sh` —— 聚焦测试，产出 `verify passed: 7/7 checks` 证据。
2. `zimaflow state init/update` —— 在一个临时 git 仓库里写入并更新单仓状态。
3. `zimaflow recall` —— 打印跨 session 恢复视图（active change、handover 摘要、bit-rot、下一步）。
4. `zimaflow close` —— 轻量收口检查。

演示全程在临时目录进行，不会污染本仓库，也不依赖任何私有环境。

## 案例产物

按主链路顺序：

| 阶段 | 文件 |
|------|------|
| 需求 brief | [`project-docs/docs/Requirements/2026-07-24-configurable-path-brief.md`](project-docs/docs/Requirements/2026-07-24-configurable-path-brief.md) |
| 任务计划（按 session 分工） | [`project-docs/docs/Tasks/2026-07-24-configurable-path-tasks.md`](project-docs/docs/Tasks/2026-07-24-configurable-path-tasks.md) |
| OpenSpec change | [`project-docs/openspec/changes/add-configurable-todo-path/`](project-docs/openspec/changes/add-configurable-todo-path/) |
| 真实实现 | [`app/todo.sh`](app/todo.sh) |
| 验证脚本（证据） | [`app/test-todo.sh`](app/test-todo.sh) |
| Session 1 handover | [`project-docs/docs/Handover/2026-07-24-handover-session1.md`](project-docs/docs/Handover/2026-07-24-handover-session1.md) |
| review / spec 合规检查 | [`project-docs/docs/Review/2026-07-24-configurable-path-compliance-report.md`](project-docs/docs/Review/2026-07-24-configurable-path-compliance-report.md) |
| 收口检查清单 | [`project-docs/docs/Closing/2026-07-24-configurable-path-closing.md`](project-docs/docs/Closing/2026-07-24-configurable-path-closing.md) |
| 经验候选 | [`project-docs/docs/Learn/2026-07-24-configurable-path-lesson.md`](project-docs/docs/Learn/2026-07-24-configurable-path-lesson.md) |

## 你应该看到的闭环

```text
brief → task planning → state(init) → 实现 → handover → [中断]
      → recall → verify(证据) → review/compliance → state(verified) → close → learn
```

看完这条链路，你会得到一个具体结论：zimaflow 不只是概念，它能把一次真实的 AI Coding 小需求，从需求进入一直接到验证、合规审查和交接。
