# Guardrails

zimaflow 的 guardrails 默认是软约束：它们提醒、核对和要求说明，但不自动替用户做决定，也不默认阻断 git 操作。

## 已公开的护栏

| 护栏 | 作用 | 当前形态 |
|------|------|----------|
| 需求契约 | 规划前先确认目标、范围、Non-goals 和验收标准 | `requirement-contract` |
| 破坏性变更检查 | 删除较多代码、改公共接口、改 schema、改权限或写库路径前先说明影响面 | `spec-compliance-check` |
| 沿用现有抽象 | 新增实现前先查已有工具、组件、接口和模式 | `spec-compliance-check` |
| hotfix / rewind 识别 | 区分紧急修复、普通变更和纠偏回退 | `sdd-router` |
| secrets 收口 | 只报告疑似敏感配置的 `path:line`，不输出密钥值 | `bin/zimaflow close` 与收口流程 |
| 发布前就绪检查 | 发布前汇总 scope、verification、rollback、communication 四类人工确认问题 | `bin/zimaflow release-check` |

## 后续公开方向

| 方向 | 说明 |
|------|------|
| Guardrail Catalog | 给高风险规则分配稳定 ID，方便在 review、handover 和 CLI 输出里引用。 |
| Context Drift Check | 检查 context index 指向的 baseline 文档是否还存在。 |
| Optional Hard Hooks | 只有在真实项目里反复出现同类高风险问题时，才考虑可选阻断式 hook。 |

## 明确边界

- secrets 报告只输出位置，不复制 secret 值。
- 破坏性变更检查只要求引用面和影响说明，不自动回滚。
- hard hooks 不默认启用，也不作为安装脚本的隐藏副作用。
- 类比只能用于扩大搜索词，不能凭类比扩大需求范围；范围决策必须来自用户确认、契约文本、设计说明或代码事实。
