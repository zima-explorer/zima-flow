# 文档同步矩阵

> session-close-reconciler 按此表逐项核对。
> AI 工具可直接照表执行，不需要额外判断。

---

| 改了什么 | 至少要更新的文档 | 优先级 | 说明 |
|---------|----------------|--------|------|
| 需求契约新增/变更 | 项目 `Requirements/`（brief）或 `PRDs/`（PRD）下对应文件 | 必须 | brief 或 PRD 必须落盘并标记状态（草稿/待确认/已确认），不能只存在于对话里 |
| 需求契约进入原型评审记录或 OpenSpec | OpenSpec `proposal.md` 或 `design.md`；如启用原型评审，同步评审记录 | 必须 | 后续 proposal/design 必须引用需求契约路径，确保契约结论进入可执行 spec |
| 产品功能改动（业务逻辑代码） | 项目 `PROGRESS.md` | 必须 | 记录功能状态变化：新增/修改/完成 |
| 产品定位或范围变化 | `Decisions/` 决策文档 | 必须 | 记录"为什么变、变成什么、影响范围" |
| 产品定位或范围变化 | 项目 PRD（如有） | 建议 | 回溯更新受影响的需求描述 |
| 产品原型评审记录新增/变更 | 项目 `Prototypes/` 下的评审记录（v0.1 可手动维护） | 必须 | 保留页面、状态、旁注、AI 假设和待确认问题；自动原型模块后续提供 |
| 产品原型评审完成 | OpenSpec `proposal.md` 或 `design.md` | 必须 | 引用原型评审说明，确保评审结论进入可执行 spec |
| 产品原型评审完成 | `Decisions/` 决策文档 | 建议 | 如原型评审改变 first slice、范围或 Non-goals，需回写路线决策 |
| OpenSpec 路线/切片调整 | `Decisions/` 决策文档 | 必须 | 先更新决策文档，再调整 openspec/changes/ |
| OpenSpec change 完成并 archive | 项目 `PROGRESS.md` | 必须 | 标记该 change 为已完成 |
| OpenSpec change 完成并 archive | `openspec/specs/`（自动） | 自动 | archive 命令自动合并，无需手动 |
| Skill / 工作流文件改动 | 所属套件的 `README.md` | 必须 | 更新 Skill 列表、版本记录 |
| Skill 新增 | 所属套件的 `README.md` | 必须 | 加入 Skill 表格、配套文件表格 |
| 存量项目梳理产物新增/变更（legacy-project-onboarding） | 项目 `Designs/Architecture-Overview.md` / `Interface-Inventory.md` / `Data-Model-ER.md` / `Implicit-Knowledge-QA.md` + `.zimaflow/context-index.yaml` | 建议 | 执行 `legacy-project-onboarding` 后落 baseline 文档并更新 context index |
| 存量项目梳理发现隐性坑或规则（legacy-project-onboarding） | Learn 候选扫描结果；确认后写入项目 `lessons.md` 或 `lessons-common.md` | 建议 | 人类补充的隐藏约束可能需要进入经验库 |
| Rule 文件改动 | 关联 Skill 的说明（如有） | 建议 | 确保 Skill 文档描述与 rule 行为一致 |
| config.yaml 规则变更 | Bridge Rule 引用是否仍正确 | 建议 | Bridge Rule 只指路，但要确认指的路没断 |
| 踩坑 / 调试循环 / 方向返工 | Learn 候选扫描结果；确认后写入项目 `lessons.md` 或 `lessons-common.md` | 建议 | reconciler 必须输出候选或明确"未发现高置信候选"，写入由 learn 在用户确认后执行 |
| 知识锚点映射新增/变更 | `references/knowledge-anchor-map.md` + zimaflow `README.md` | 必须 | 新锚点会改变路由前置知识加载行为，必须可发现 |
| 知识使用账本规则新增/变更 | `references/knowledge-usage-guide.md` + `learn/SKILL.md` + `session-close-reconciler/SKILL.md` | 必须 | 账本字段、事件类型、淘汰规则必须与执行 Skill 保持一致 |
| 知识使用事件产生 | `references/knowledge-usage-ledger.jsonl` | 建议 | loaded/cited/applied/challenged 只追加 JSONL，不直接改 lesson 正文 |
| lesson 稳定 ID 新增/变更 | `references/lessons-common.md` 或项目 `lessons.md` + `references/knowledge-anchor-map.md`（如被锚点引用） | 必须 | ID 是 ledger 和 handover 的稳定引用，改 ID 需同步引用方 |
| 用户纠正关键流程 / 路径 / 脱敏 / 状态判断 | Learn 候选扫描结果 | 建议 | 例如真源/runtime 路径误用、公开内容脱敏、验收环境 与上线状态修正 |
| 技术决策（选型、架构变更） | `Decisions/` 或 `design.md` | 必须 | 决策必须有文档可追溯 |
| 依赖变更（新增/升级/移除） | 项目 `PROGRESS.md` 或 `CHANGELOG` | 建议 | 记录依赖变化及原因 |
| 工时估算偏差发现 | `workload-dict.md` 或项目 `project-workload-overrides.md` | 建议 | 校准工时基准，下次更准 |
| 项目注册表变更 | `PROJECT_REGISTRY.md` | 必须 | 新项目、路径变更、状态变更 |
| zimaflow 自身改动 | zimaflow `README.md` + 版本记录 | 必须 | 更新 Skill 列表、设计决策、版本记录 |
| zimaflow 自身改动来自流程缺口或真实踩坑 | Learn 候选扫描结果 | 建议 | 规则直接回写不能替代 lesson 统计，至少输出候选供用户确认 |
| zimaflow 自身改动 | 公开路线图或 issue | 建议 | 更新待实施方案或参考资料 |
| session 收尾触发词或完成语义变更 | `session-close-reconciler/SKILL.md` + `handover-manager/SKILL.md` + zimaflow `README.md` | 必须 | git clean、tests passed、pushed 只代表工程状态完成；final response 宣布完结前必须先跑 reconciler |
| zimaflow CLI / hook 能力变更 | zimaflow `README.md` + 对应 `bin/` 或 `scripts/` 文件 | 必须 | CLI 是开源用户入口，必须记录命令、默认行为、是否阻断 git 操作 |
| zimaflow CLI / hook 能力变更 | 公开路线图或 issue | 建议 | strict hook、close report、pre-push 阻断等硬 harness 方案可先进入待办，不要求 v1 实现 |

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
