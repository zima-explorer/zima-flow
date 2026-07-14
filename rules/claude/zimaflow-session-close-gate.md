---
alwaysApply: true
---

# Zimaflow Session Close Gate

当出现工程完成信号时，不要直接宣布任务完成或 session 完结，必须先执行 zimaflow 收尾对账。

工程完成信号包括但不限于：

- OpenSpec `tasks.md` 全部勾选完成
- targeted tests / build / verify 全部通过
- `git diff --check` 通过
- commit 已完成
- push 已完成
- `git status` 显示工作区干净
- 用户说“完成了”“已 push”“push 完了”“提交完成”“收尾”“结束”“本 session 完结”“还有没有遗漏”

触发后必须按以下顺序输出：

1. `session-close-reconciler` 收口检查清单
   - ✅ 已完成
   - 📝 建议补充
   - ❌ 明确缺失
   - 🧠 Learn 候选
2. 等用户确认是否补文档或记录遗留。
3. 如需交接，再生成或更新 handover。

注意：

- git clean、tests passed、commit/push 成功只代表工程状态完成，不代表 zimaflow session 已收口。
- 如果本轮有产品功能改动，应检查项目知识库 `PROGRESS.md`、handover、OpenSpec tasks、必要的 Decisions/Drafts 是否同步。
- 如果本轮产生流程教训或用户纠正，应列出 learn 候选，但不要自动写入 lesson。
- 在收口检查清单输出前，不要说“本轮完整结束”“session 可以完结”。
