# 可配置 todo 路径 · 收口检查清单

> 阶段：Session 2 结束，change 已 verified

| 检查项 | 状态 | 说明 |
|--------|------|------|
| 需求契约已确认 | done | brief 与 Given/When/Then 验收标准已确认。 |
| 任务计划边界清晰 | done | 六个任务，跨两个 session，低于任务上限。 |
| OpenSpec change 已存在 | done | proposal/design/tasks 均已存在。 |
| spec 合规检查 | done | 见 [Spec Compliance Report](../Review/2026-07-24-configurable-path-compliance-report.md)：场景覆盖、架构一致性、排除范围均通过；无破坏性变更（B4）；沿用既有持久化抽象（B5），未新造。 |
| 验证已完成 | done | `app/test-todo.sh` 输出 `verify passed: 7/7 checks`。 |
| Guardrail 收口 | done | 本轮无 hotfix / rewind / secrets 风险项。 |
| handover 已写入 | done | 见 S1 handover；S2 完成后 state 更新为 verified。 |
| 经验候选已审查 | done | 见 learn 文档。 |

## 证据指针

- 测试脚本：`examples/demo/case-cross-session/app/test-todo.sh`
- Spec Compliance Report：`examples/demo/case-cross-session/project-docs/docs/Review/2026-07-24-configurable-path-compliance-report.md`
- state 快照：`add-configurable-todo-path` 的 `.zimaflow-state.yaml`（由 `run-case.sh` 实时生成）
