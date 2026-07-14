# 设计

## 决策

- 使用本地 JSON 文件持久化，因为它让 demo 可检查且无需依赖。
- 命令面只保留三个动词，确保 first slice 足够小。
- 未知任务 id 作为用户错误处理，并输出清晰信息。

## 数据结构

```json
{
  "tasks": [
    { "id": 1, "title": "Write README", "done": false }
  ]
}
```

## 验证

- 单元测试持久化行为。
- 用偏集成的测试覆盖 add/list/done 命令序列。
