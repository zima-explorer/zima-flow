---
alwaysApply: true
---

# OpenSpec Config Awareness

当你执行任何 OpenSpec 操作（explore、propose、apply、verify、archive）时，**必须先读取** `openspec/config.yaml` 中的 `context` 和 `rules` 字段。

- `context` 包含项目通用约定（commit 格式、排除范围、文档同步规则）
- `rules` 包含各阶段产物的具体约束（proposal 必须有排除范围、tasks 不超过 15 项等）

`config.yaml` 是这些规则的 single source of truth。本文件只做指路，不复制规则内容。
