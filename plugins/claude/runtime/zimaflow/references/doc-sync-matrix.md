# 文档同步矩阵

> session-close-reconciler 按此表逐项核对。
> AI 工具可直接照表执行，不需要额外判断。

---

| 改了什么 | 至少要更新的文档 | 优先级 | 说明 |
|---------|----------------|--------|------|
| 需求契约新增/变更 | 项目 `Requirements/`（brief）或 `PRDs/`（PRD）下对应文件 | 必须 | brief 或 PRD 必须落盘并标记状态（草稿/待确认/已确认），不能只存在于对话里 |
| 需求契约进入 proto-review 或 OpenSpec | OpenSpec `proposal.md` 或 `design.md`；如启用原型评审，同步 `Prototypes/review-notes.md` | 必须 | 后续 proposal/design 必须引用需求契约路径，确保契约结论进入可执行 spec |
| 契约关联规划发生实质性变更 | 需求契约中的 `意图锁` + `Decisions/` / tasks / OpenSpec 对照说明 | 必须 | 如果 Decision、任务或 OpenSpec 范围偏离已确认意图锁，必须回到 requirement-contract 重新确认，或把超出范围项标为后续迭代 / 需求变更；不新增 execution-contract，不自动回退 |
| 产品功能改动（业务逻辑代码） | 项目 `PROGRESS.md` | 必须 | 记录功能状态变化：新增/修改/完成 |
| 产品定位或范围变化 | `Decisions/` 决策文档 | 必须 | 记录"为什么变、变成什么、影响范围" |
| 产品定位或范围变化 | 项目 PRD（如有） | 建议 | 回溯更新受影响的需求描述 |
| 产品原型评审产物新增/变更 | 项目 `Prototypes/` 下的 `prototype.html` + `review-notes.md` | 必须 | 保留可评审页面、状态、旁注、AI 假设和待确认问题 |
| 产品原型评审完成 | OpenSpec `proposal.md` 或 `design.md` | 必须 | 引用原型和评审说明，确保评审结论进入可执行 spec |
| 产品原型评审完成 | `Decisions/` 决策文档 | 建议 | 如原型评审改变 first slice、范围或 Non-goals，需回写路线决策 |
| OpenSpec 路线/切片调整 | `Decisions/` 决策文档 | 必须 | 先更新决策文档，再调整 openspec/changes/ |
| OpenSpec change 完成并 archive | 项目 `PROGRESS.md` | 必须 | 标记该 change 为已完成 |
| OpenSpec change 完成并 archive | `openspec/specs/`（自动） | 自动 | archive 命令自动合并，无需手动 |
| OpenSpec change 已 archive 但 state 未 closed | 项目 closing checklist + handover + `.zimaflow-state.yaml` | 必须 | archive 后自动进入 reconciler / handover / finalize；`archive_state_not_closed` 必须通过 `zimaflow finalize` 解决，不能笼统写成 `need_docs_sync` |
| archive / finalize / close 完成语义变更 | `openspec-archive-change` + `session-close-reconciler` + `handover-manager` + `Design-Zimaflow-State.md` + zimaflow `README.md` | 必须 | 唯一完成门是 `zimaflow close --json` 返回 `next_action=can_close`；同步状态矩阵、blocker 与命令示例 |
| spec-compliance-check 全量审查完成（全部 task 完成后） | 项目 `Reviews/` 下的独立 Spec Compliance Report 文件；closing checklist 对应行链接该文件路径 | 必须 | 审查报告必须落盘为独立可链接文件，不能只在 closing 清单里写一行"合规检查：done"；每个 task 后的轻量检查不强制落盘 |
| OpenSpec tasks 状态漂移（存在 Superpowers plan / 代码改动 / 测试证据，但 `tasks.md` 未勾选或状态滞后） | `openspec/changes/<name>/tasks.md`；同步依据记入 handover"遗留与下一步"或 closing checklist | 必须 | verify/archive 或对外交接前必须标记漂移并由人工确认是否同步，记录同步依据（文件路径 / 测试结果 / handover 记录 / 用户确认）；`openspec-superpowers-bridge` Step 5.5 与 reconciler 只标记，**不自动勾选 tasks.md**、不自动改 spec |
| Skill / workflow 文件改动 | 所属套件的 `README.md` | 必须 | 更新 Skill 列表、版本记录 |
| Reviewer–Executor Loop 契约、生命周期或守卫变更 | `references/Reviewer-Executor-Loop.md` + `sdd-router` + `spec-compliance-check` + `handover-manager` + `session-close-reconciler` + `references/Design-Zimaflow-State.md` + zimaflow `README.md` | 必须 | Brief / Report 的唯一正文真源只在 reference；既有 owner 只承接各自阶段，state 持有 opt-in profile 指针与 event head，matrix/receipts 留在 validation；review-ready 必须同时验证 delta-spec 全集、精确 diff/Report 链接、source-tree freshness、evidence-only dirty set 与 event/state 一致性；三宿主生成包与默认/opt-in 行为 parity 必须同轮验证 |
| Skill 新增 | 所属套件的 `README.md` | 必须 | 加入 Skill 表格、配套文件表格 |
| legacy-project-onboarding 产物新增/变更 | 项目 `Designs/Architecture-Overview.md` / `Module-Map.md` / `Interface-Inventory.md` / `Data-Model-ER.md` / `Test-Entry-Points.md` / `Key-Flows.md` / `Implicit-Knowledge-QA.md` | 必须 | 存量项目 code-intelligence baseline 必须落文档，不能只留在对话里 |
| legacy-project-onboarding 产物新增/变更 | 项目 `.zimaflow/context-index.yaml` | 必须 | context index 只记录 baseline 路径、短 metadata、常用命令、风险锚点、active change 和最新 handover，不复制正文 |
| handover 生成或更新且项目已有 context index | 项目 `.zimaflow/context-index.yaml` | 建议 | 只更新 `workflow.latest_handover`、必要时更新 `workflow.latest_state` 和 `updated_at`，不复制 handover 正文 |
| legacy-project-onboarding 发现隐性坑或规则 | Learn 候选扫描结果；确认后写入项目 `lessons.md` 或 `lessons-common.md` | 建议 | 人类补充的隐藏约束可能需要进入经验库 |
| Rule 文件改动 | 关联 Skill 的说明（如有） | 建议 | 确保 Skill 文档描述与 rule 行为一致 |
| config.yaml 规则变更 | Bridge Rule 引用是否仍正确 | 建议 | Bridge Rule 只指路，但要确认指的路没断 |
| 踩坑 / 调试循环 / 方向返工 | Learn 候选扫描结果；确认后写入项目 `lessons.md` 或 `lessons-common.md` | 建议 | reconciler 必须输出候选或明确"未发现高置信候选"，写入由 learn 在用户确认后执行 |
| 知识锚点映射新增/变更 | 你自己的锚点表 + 能力 `README.md`；规则见 `references/knowledge-anchor-guide.md` | 必须 | 新锚点会改变路由前置知识加载行为，必须可发现 |
| 知识使用账本规则新增/变更 | `references/knowledge-usage-contract.md` + `learn/SKILL.md` + `session-close-reconciler/SKILL.md` + 能力 `README.md` | 必须 | 账本字段、事件类型、全局 data home、淘汰规则必须与 CLI 和执行 Skill 保持一致；能力根只读，不保存真实事件 |
| 经验质量判断标准新增/变更 | `references/experience-quality-criteria.md` + `learn/SKILL.md` | 必须 | 三镜头判定、九类垃圾特征、去重否决规则、升级自检四问是 learn 的筛选依据，标准变了执行步骤要同步 |
| 知识使用事件产生 | 用户级 `ZIMAFLOW_DATA_HOME/knowledge-usage-ledger.jsonl` | 建议 | 通过 `zimaflow knowledge-record` 追加 loaded/cited/applied/challenged；能力根只读，不直接改 lesson 正文 |
| lesson 稳定 ID 新增/变更 | `ZIMAFLOW_DATA_HOME/lessons-common.md` 或项目 `lessons.md` + 你的锚点表（如被锚点引用） | 必须 | 用户级跨项目 lessons 是公开 runtime 的唯一写入位置；私有源旧文件只读兼容 |
| 用户纠正关键流程 / 路径 / 脱敏 / 状态判断 | Learn 候选扫描结果 | 建议 | 例如真源/runtime 路径误用、公开内容脱敏、UAT 与上线状态修正 |
| 技术决策（选型、架构变更） | `Decisions/` 或 `design.md` | 必须 | 决策必须有文档可追溯 |
| 依赖变更（新增/升级/移除） | 项目 `PROGRESS.md` 或 `CHANGELOG` | 建议 | 记录依赖变化及原因 |
| 工时估算偏差发现 | 项目 `project-workload-overrides.md`；基准见 `references/workload-baseline.md` | 建议 | 校准工时基准，下次更准；基准文件本身保持静态，不在其中累积校准记录 |
| 项目上下文配置变更 | 仓库 `.zimaflow/project.yaml`；如为本机覆盖则用户级 `~/.zimaflow/projects.yaml` | 必须 | 可移植项目名/默认文档根提交到仓库；个人绝对路径只留用户配置，不进入共享提交 |
| zimaflow 自身改动 | zimaflow `README.md` + 版本记录 | 必须 | 更新 Skill 列表、设计决策、版本记录 |
| zimaflow 自身改动来自流程缺口或真实踩坑 | Learn 候选扫描结果 | 建议 | 规则直接回写不能替代 lesson 统计，至少输出候选供用户确认 |
| 能力自身改动 | 能力自己的路线与待办记录（如涉及 harness 讨论） | 建议 | 更新待实施方案或参考资料 |
| zimaflow state 文件规则变更 | `references/Design-Zimaflow-State.md` + zimaflow `README.md` + 相关 Skill | 必须 | `.zimaflow-state.yaml` 字段、phase 或读写责任变化会影响跨工具恢复和收口判断 |
| P0/P1 紧急热修复完成 | 项目 `INCIDENT/` 事故记录（如无独立 INCIDENT 文档，写入 handover"遗留与下一步"或 `PROGRESS.md`） | 必须 | 记录事故现象、根因、修复摘要、验证结果，以及 24h 内待补的 CHANGE/SUMMARY/tests/LESSONS 项；hotfix 严重度 P0/P1 不能只止血不留痕 |
| rewind / 需求纠偏（回退了 contract / Decision / OpenSpec / tasks / implementation） | 被回退产物所在文档（`Requirements/` `PRDs/` `Decisions/` `openspec/changes/`）+ handover"遗留与下一步" | 必须 | 记录"被回退的产物、回退原因、当前有效版本"，避免废弃版本与有效版本混淆；就地修订不新建平行产物 |
| secrets_scan 命中或敏感配置风险 | handover"遗留与下一步"或 `PROGRESS.md`（**禁止记录密钥值**） | 必须 | 只记命中事实（`path:line`）、处理动作、是否需要 revoke/rotate、是否已补 `.env.example` / `.gitignore`；密钥原文不得写入任何文档 |
| 准备发布 / 上线 / 发版 / 交付 / 打 tag | handover"遗留与下一步"或 `PROGRESS.md`；建议先跑 `zimaflow release-check` | 必须 | 记录 release-check 的 `next_action`；若非 `ready`，记录缺口类别（verify / archive / handover / secret review / manual confirmation）；四问（scope / verification / rollback / communication）只记"待人工确认 / 已确认"，不替用户回答；**不记录任何发布 token / secret 值** |
| session 收尾触发词或完成语义变更 | `session-close-reconciler/SKILL.md` + `handover-manager/SKILL.md` + zimaflow `README.md` | 必须 | git clean、tests passed、pushed 只代表工程状态完成；reconciler/handover 后仍须运行最终 close gate，只有 `next_action=can_close` 才能宣布完结 |
| zimaflow CLI / hook 能力变更 | zimaflow `README.md` + 对应 `bin/` 或 `scripts/` 文件 | 必须 | CLI 是开源用户入口，必须记录命令、默认行为、是否阻断 git 操作 |
| CLI / hook 能力变更 | 能力自己的路线与待办记录（如涉及 strict / 阻断模式设计） | 建议 | strict hook、close report、pre-push 阻断等硬 harness 方案可先进入待办，不要求 v1 实现 |

---

## 使用方式

1. session-close-reconciler 的 Step 2 读取此表
2. 根据 Step 1 识别的改动类型，查出对应行
3. 检查"至少要更新的文档"是否已更新
4. 优先级为"必须"的未更新 → 标为 ❌ 明确缺失
5. 优先级为"建议"的未更新 → 标为 📝 建议补充
6. 优先级为"自动"的 → 验证自动操作是否已执行

## 维护规则

- 新增改动类型时，同步加行
- 不要把同一份文档在多行中重复列为"必须"——如果一次改动同时命中多行，去重后只检查一次
