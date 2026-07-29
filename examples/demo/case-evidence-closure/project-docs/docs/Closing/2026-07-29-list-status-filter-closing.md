# todo list 状态筛选 · 收口检查清单

> 类型：session-close-reconciler 收口对账
> 依据模板：`skills/session-close-reconciler.md`（当前公开版的收口清单格式）
> 变更名：list-status-filter
> 日期：2026-07-29

## 收口检查清单

### ✅ 已完成

- **Verification Evidence**：`bash app/test-todo.sh` 输出 `verify passed: 6/6 checks`，退出码 0。命令可复跑，6 条断言覆盖 brief 的 5 个场景，其中 3 条带负向条件。
- **Spec Compliance / Reviews**：全量审查已独立落盘 → [`Reviews/2026-07-29-list-status-filter-compliance-report.md`](../Reviews/2026-07-29-list-status-filter-compliance-report.md)。场景覆盖、范围一致性、排除范围均通过；B4 无破坏性变更；B5 沿用 `cmd_list` 既有的 done 位分区判定；验证证据匹配度命中 1 类（新增 / 扩展 CLI 入口），契约测试与兼容性检查证据齐备。
- **意图锁对照**：brief 的意图锁是「只加入口，不改数据」。实收改动限于参数解析循环与 `cmd_list` 渲染分区，持久化格式 `id|done|title` 未动，未跑偏。
- **需求与计划产物已落盘**：[需求 brief](../Requirements/2026-07-29-list-status-filter-brief.md)、[轻量任务台账](../Tasks/2026-07-29-list-status-filter-tasks.md)。本轮走轻量模式，不写 OpenSpec 三件套——规范由 Given/When/Then 承担，计划由台账承担。
- **文档同步**：案例 README 与仓库入口文档已补入本案例的运行命令与职责说明。

### 📝 建议补充

- 本轮无建议补充项。

### ❌ 明确缺失

- 本轮无明确缺失项。

> 关于三级状态的一条规则：验证若存在失败，必须写入 ❌ 明确缺失；验证未跑或证据不完整，必须写入 📝 建议补充。**即使失败被归因为环境问题或与本轮改动无关的既有失败，仍然必须上浮**，只在条目中标注归因。本轮测试全绿，因此这两栏为空——不是省略，是确实没有。

### 🧠 Learn 候选

- 候选 1：过滤类功能的测试必须包含负向断言 —— 见 [经验候选](../Learn/2026-07-29-list-status-filter-lesson.md)
- 候选 2：入口层未透传已有判定逻辑是常见缺口，动手前先查已有实现 —— 同上
- 状态：**候选，未写入公共经验库**。reconciler 只输出候选，写入需用户确认后交由 `learn` 执行。

*本轮无适用项：Guardrail 收口、Knowledge Usage*

> **折叠只是显示合并，不代表没检查。** 上面这一行里的每一项都按各自的 Step 逐项检查过，只是结论为「不适用」才折叠成一行：本轮无 hotfix / rewind / secrets 风险项；本轮未读取或应用带 ID 的 lesson/pattern。没检查过的项不能计入这一行。🧠 Learn 候选不参与折叠，因此即使未命中也要单独成节写明。
>
> 折叠行只列当前公开版收口清单实际包含的分节。本轮同样不适用但清单中没有对应分节的维度（如 OpenSpec tasks 状态同步、跨 session 交接续接），不在这里虚列——案例不领先于规则。

---

**结论**：本轮收口完整。0 项明确缺失，0 项建议补充，2 项 Learn 候选待用户确认。

## 证据指针

- 实现：`examples/demo/case-evidence-closure/app/todo.sh`
- 测试脚本：`examples/demo/case-evidence-closure/app/test-todo.sh`（`verify passed: 6/6 checks`）
- Spec Compliance Report：`examples/demo/case-evidence-closure/project-docs/docs/Reviews/2026-07-29-list-status-filter-compliance-report.md`
- 可执行入口：`examples/demo/case-evidence-closure/run-case.sh`
