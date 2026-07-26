# 可配置 todo 路径 · Session 1 Handover

> 类型：handover
> 日期：2026-07-24
> 当前阶段：实现进行中（S1 结束）
> 工作模式：完整模式案例
> change：add-configurable-todo-path

## 本轮做了什么

- 确认 brief 与验收标准（Given/When/Then）。
- 拆出 T1–T6，并按 session 分工（S1 做 T1–T3，S2 做 T4–T6）。
- 实现 `--file` 参数解析与 `TODO_FILE` 回退（T1–T3）。

## 决策

- 路径优先级 `--file` > `TODO_FILE` > `.todo.txt`。
- 不改持久化格式，保持非破坏性变更。

## 遗留与下一步

- [ ] T4：补默认路径不回归的测试
- [ ] T5：补未知 id 错误路径测试
- [ ] T6：跑 verify 并记录证据，然后收口

## Guardrail 承接

- secrets：本轮无密钥改动，无需 rotate。
- 破坏性变更（B4）：无，未删命令、未改既有输出。
- 下次恢复入口：先运行 `zimaflow recall`，再打开本 handover。
