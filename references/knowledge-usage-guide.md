# 知识使用指南

本指南定义 zimaflow 使用的个人规模知识闭环：

1. 从 `knowledge-anchor-map.md` 加载相关知识。
2. 在 `knowledge-usage-ledger.jsonl` 记录加载或应用行为。
3. 在 session 收口时复核使用情况。
4. 只有在用户确认后，才升级、更新或废弃知识。

## Knowledge ID 格式

每条参与账本的可复用经验都必须包含：

```markdown
- **ID**：kf-YYYYMMDD-short-slug
```

规则：

- ID 应保持稳定，不因标题调整而改变。
- 新增 ID 前，先搜索已有 lessons 和 ledger，避免重复。
- 项目级 `lessons.md` 可以使用同样格式。

## 账本事件类型

`knowledge-usage-ledger.jsonl` 每行写一个 JSON object。

| Event type | 含义 | 升级权重 |
|------------|------|----------|
| `loaded` | Agent 因锚点或 Skill 要求读取了该条目。 | 低 |
| `cited` | Agent 在计划、review 或 handover 中引用了该条目。 | 中 |
| `applied` | 该条目改变了实现、路由或 review 决策。 | 高 |
| `challenged` | 该条目可能过期、误导，或被当前证据反驳。 | 负向 / 需复核 |
| `stale_review` | 周期性复核将该条目标记为复核窗口内不活跃。 | 仅复核 |

最小字段：

```json
{"event_id":"use-YYYYMMDD-NNN","knowledge_id":"kf-YYYYMMDD-short-slug","event_type":"loaded","project":"project-name","session":"short task summary","stage":"routing","trigger":"anchor or reason","reason":"why this knowledge was read or used","timestamp":"YYYY-MM-DDTHH:MM:SS+08:00"}
```

## 人工复核规则

- 账本证据可以建议调整 `出现次数`、升级级别或清理条目。
- `learn` 在修改 lesson 正文、级别或 Skill 规则前必须询问用户。
- 单独的 `loaded` 事件不足以支撑知识升级。
- 跨 session 或跨项目的 `applied` 事件是较强的升级证据。
- `challenged` 事件应先触发复核，再考虑继续升级。

## 过期复核 / 废弃

过期复核可以手动执行，也可以在未来 `zimaflow close` 增强中执行。

当知识条目满足以下条件时，可成为清理候选：

- 最近 90 天没有 `cited` 或 `applied` 事件；
- 级别不是 `rule`，除非用户明确将 rules 纳入清理；
- 不是当前复核窗口中新建的条目。

清理流程：

1. 为每个候选追加一条 `stale_review` 账本事件。
2. 将候选及最近使用证据展示给用户。
3. 用户确认后，将 lesson 标记为 deprecated，或移动到 archive 小节/文件。
4. 如果用户拒绝清理，追加一条 `cited` 事件，reason 使用 `user-kept`。

没有用户明确要求时，绝不物理删除 lesson。
