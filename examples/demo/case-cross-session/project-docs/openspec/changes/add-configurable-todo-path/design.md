# 设计

## 决策

- 路径解析优先级：`--file` > `TODO_FILE` > 默认 `.todo.txt`。理由：显式参数应压过环境变量，环境变量应压过硬编码默认值。
- `--file` 允许出现在子命令前后，降低使用者的记忆负担。
- 不改动持久化格式（行式 `id|done|title`），本次只增加「写到哪个文件」这一维度，属非破坏性变更（spec-compliance 的 B4 门槛：未删码、未改公共输出、未改 schema）。

## 数据结构

持久化保持不变，每行一个任务：

```text
1|0|Write README
2|1|Ship v0.2
```

`0` 表示待办，`1` 表示已完成。

## 验证

- 用聚焦测试覆盖：`--file` 写入指定路径、`TODO_FILE` 回退、默认行为不回归、未知 id 错误路径。
- 测试脚本自带断言并输出 `verify passed`，作为 handover 与 state 的 evidence。
