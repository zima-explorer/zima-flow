# 案例：一次小需求怎么把证据收口

## 一条命令跑完

```bash
examples/demo/case-evidence-closure/run-case.sh
```

它会真实执行 `app/test-todo.sh`，输出 `verify passed: 6/6 checks`，然后打印本案例的全部产物路径。全程只用 bash，不依赖网络、凭证或任何外部服务。

## 这个案例展示什么

**轻量模式下，证据怎么收口。**

"测试通过"不等于"验证充分"，"合规检查 done"也不等于有人能复查。这个案例把三样东西摆出来给你看：

- **可复跑的验证证据**：6 条断言，一条命令重跑，输出可核对——不是一句「测过了」。
- **独立落盘的合规报告**：[Spec Compliance Report](project-docs/docs/Reviews/2026-07-29-list-status-filter-compliance-report.md) 是一份能被第三方独立复查的文件，不是收口清单里的一行状态。
- **逐项对账的收口清单**：[收口清单](project-docs/docs/Closing/2026-07-29-list-status-filter-closing.md) 里能看到 `not_applicable` 分节被折叠成一行——以及为什么折叠不等于没检查。

## 需求

```text
给已有的本地 todo CLI 增加 list 状态筛选：--status pending|done|all。
```

真实缺口：`cmd_list` 本来就按 done 位分两区渲染，**判定逻辑已经存在**，缺的只是让用户选择「只看其中一区」的入口。这是「入口层未透传已有判定逻辑」的典型样子——不是底层 API 已就绪，是渲染层的判定已就绪。

## 为什么这个案例没有 OpenSpec

因为不需要。

本需求纯读、约 25 行改动、**不改持久化格式**（仍是 `id|done|title`）、不涉及 schema / 权限 / 数据写入路径，也不需要留正式的方案审查记录。这种规模的需求走**轻量模式**就够：

- 规范的作用，由 [brief 的 Given/When/Then](project-docs/docs/Requirements/2026-07-29-list-status-filter-brief.md) 承担
- 计划的作用，由[轻量任务台账](project-docs/docs/Tasks/2026-07-29-list-status-filter-tasks.md)承担

省掉的是文档形态，不是判断。什么时候该升级到**完整模式**并写 OpenSpec 三件套？触发 schema 变更、权限、数据写入路径，或需要正式审查留痕时——本需求都不触发。

**zimaflow 的默认动作不是把所有事流程化。**

## 和 case-cross-session 的区别

同一个 todo CLI，两个真实需求，两条不同重量的路径：

| 案例 | 看什么 | 模式 |
|------|--------|------|
| **本案例** `case-evidence-closure` | **证据收口**：验证证据、合规报告落盘、收口对账 | 轻量模式，无 OpenSpec 三件套 |
| [`case-cross-session`](../case-cross-session/README.md) | **跨 session**：`state` / `recall` / `handover` 如何在两次对话之间接住上下文 | 完整模式，有 OpenSpec 三件套 |

两者互不替代：跨 session 恢复由 `case-cross-session` 演示，本案例不重复；本案例专注证据收口。

本案例的 `app/todo.sh` 起点就是 `case-cross-session` 的交付物（已支持 `--file` / `TODO_FILE`），本轮只叠加 `--status` 增量——上一个案例的交付物，是这个案例的起点。

## 案例产物

按主链路顺序：

| 阶段 | 文件 |
|------|------|
| 需求 brief（含意图锁与 Given/When/Then） | [`project-docs/docs/Requirements/2026-07-29-list-status-filter-brief.md`](project-docs/docs/Requirements/2026-07-29-list-status-filter-brief.md) |
| 轻量任务台账 | [`project-docs/docs/Tasks/2026-07-29-list-status-filter-tasks.md`](project-docs/docs/Tasks/2026-07-29-list-status-filter-tasks.md) |
| 真实实现 | [`app/todo.sh`](app/todo.sh) |
| 验证脚本（证据） | [`app/test-todo.sh`](app/test-todo.sh) |
| review / spec 合规检查 | [`project-docs/docs/Reviews/2026-07-29-list-status-filter-compliance-report.md`](project-docs/docs/Reviews/2026-07-29-list-status-filter-compliance-report.md) |
| 收口检查清单 | [`project-docs/docs/Closing/2026-07-29-list-status-filter-closing.md`](project-docs/docs/Closing/2026-07-29-list-status-filter-closing.md) |
| 经验候选 | [`project-docs/docs/Learn/2026-07-29-list-status-filter-lesson.md`](project-docs/docs/Learn/2026-07-29-list-status-filter-lesson.md) |

需求进入这一环没有单独建文件，就在本页上方的「需求」与「为什么这个案例没有 OpenSpec」两节里——为凑齐产物而造一份三行的文档，恰好是本案例要反对的。

## 三个细节，值得单独看一眼

### 1. 负向断言：防的是假绿灯

筛选类断言如果只写「目标项存在」，那么即使 `--status` 被完全忽略、两个分区照常全渲染，测试依然会通过。所以 6 条断言里有 3 条带「结果中**不含**另一类」的负向条件。

判据很简单：把过滤条件改成恒真，测试必须变红。

### 2. 兼容性检查是被验证矩阵提醒才立的

「不传 `--status` 的输出与 `--status all` 一致」这条（检查 4），不是顺手多写的。`spec-compliance-check` 的[验证证据匹配度](project-docs/docs/Reviews/2026-07-29-list-status-filter-compliance-report.md)把「兼容性检查」与「契约测试」并列为「新增 / 扩展 CLI 入口」这类变更的期望证据——对照矩阵时才发现默认行为缺一条锁定用例。

矩阵管「该看哪类证据」，不管「证据本身准不准」，后者仍需人工判断。

### 3. 折叠不等于没检查

收口清单末尾有一行：

```markdown
*本轮无适用项：Guardrail 收口、Knowledge Usage*
```

这是显示合并，不是减少检查项。每一项都逐项检查过，只是结论为「不适用」才折叠。没检查过的项不能计入这一行。Learn 候选不参与折叠，未命中时也要单独写明。

## 如果验证没通过会怎样

本案例测试全绿，所以收口清单的 ❌ 与 📝 两栏是空的。但这不代表它们只是摆设——规则是这样的：

- 本轮测试 / 验证**存在失败** → 必须写入 ❌ 明确缺失
- 验证**未跑**，或证据不完整（说不清跑了什么、结果如何）→ 必须写入 📝 建议补充
- **即使失败已归因为环境问题、隔离副作用或与本轮改动无关的既有失败，仍然必须上浮**，只在条目中标注归因

原因很直接：验证结果只写在正文里而不进入顶部三级状态，只看顶部的人会得到「没有缺失」的错误印象。

这仍是 soft check——上浮只要求必须显示，不自动阻断流程、不自动改测试。这里用文字说明，而不是在案例里人为造一次失败。
