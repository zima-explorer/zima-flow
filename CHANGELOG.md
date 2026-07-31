# Changelog

本文件记录 zimaflow 公开发行版的显著变更。

格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 文档

- `examples/demo/case-cross-session` 增加独立的 `Spec Compliance Report`（`docs/Reviews/`），把 review/compliance 从收口清单里的一行状态变成可链接、贴合 `spec-compliance-check.md` 输出格式的真实审查产物。
- 审查中发现「默认路径不回归」场景缺自动化测试，随即在 `app/test-todo.sh` 补齐（`verify passed` 由 6/6 提升为 7/7），并同步更新 README / getting-started / workflow-overview / 案例 README / 收口清单中的引用与计数。
- 案例的合规审查目录统一为 `docs/Reviews/`（原 `docs/Review/`），与项目文档分层规范中的「规范合规审查 → `Reviews/`」一致；同步更新案例 README、收口清单与 `docs/workflow-overview.md` 中的链接。
- 上述 `Spec Compliance Report` 补充「验证证据匹配度」小节：如实标注本次变更命中「新增 / 扩展 CLI 参数或入口行为」1 类，期望证据为契约测试与兼容性检查，并指向 `app/test-todo.sh` 的对应检查项；其余变更类型标注为不涉及。
- 新增公开案例 `examples/demo/case-evidence-closure`：给 demo 用的 todo CLI 增加 `list --status pending|done|all` 状态筛选，带真实代码改动与可复跑的验证证据（`run-case.sh` 输出 `verify passed: 6/6 checks`），演示轻量模式下证据如何收口——独立落盘的 `Spec Compliance Report`（含验证证据匹配度）、把「本轮无适用项」折叠成一行的收口清单，以及标注为「未写入公共经验库」的经验候选。
- 该案例**不写 OpenSpec 三件套**：需求纯读、不改持久化格式 `id|done|title`、不涉及 schema / 权限 / 数据写入路径，风险低。规范的作用由 brief 的 Given/When/Then 承担，计划的作用由轻量任务台账承担；README 中写明什么时候才需要升级到完整模式。
- 三个 demo 入口的职责区分写进 `examples/demo/README.md`、`README.md`、`docs/getting-started.md` 与 `docs/workflow-overview.md`：`examples/demo/` 是纸面演练（产物长什么样），`case-evidence-closure/` 是轻量模式（证据收口），`case-cross-session/` 是完整模式（跨 session）。两个真实案例载体相同、重量不同，产物数量的差别来自档位判断。
- `docs/workflow-overview.md` 增加「轻量模式的链路长什么样」一节，并把 `spec-compliance-check` 的报告示例扩为两份（轻量 / 完整各一）。

### 测试

- 新增 `tests/context-check.sh` 并串入 `tests/smoke.sh`，覆盖 context index 缺失、baseline 指针缺失、全部指针存在、从子目录向上查找四类边界。
- 新增 `tests/skill-rules.sh`：grep 型公开规则守护测试，核对已发布的四条规则文本（Reviews 报告落盘、验证证据匹配度、`not_applicable` 折叠、验证失败/证据不完整上浮）是否仍在场，并守护三项结构性不变量（合规审查目录统一为 `Reviews/`、公开版 skill 行数上限、两个真实案例的 verify 计数与产物文档引用一致）。只断言章节标题、表格枚举值与边界短句，不断言完整散文句；由 `tests/smoke.sh` 串接。

### 变更

- `bin/zimaflow` 新增只读 `context-check` / `context-check --json`：从当前目录向上寻找 `.zimaflow/context-index.yaml`，检查 baseline / workflow 指针是否仍存在，输出 `ok` / `refresh_baseline` / `create_context_index`；不创建 index、不刷新 baseline、不读取项目注册表、不阻断需求。
- `spec-compliance-check` 增加「验证证据匹配度」核对步骤：按六类变更类型对照期望证据（契约测试 / migration / producer-consumer 兼容性 / 逆向流程与异常分支 / 越权与审计 / 测试安全网），并要求把「不涉及」与「未覆盖」区分开。这是提醒清单式的 soft check，不阻断流程；矩阵未覆盖的类型标注为建议人工判断。
- `spec-compliance-check` 增加全量审查报告的落盘要求：全部 task 完成后的审查须产出 `Reviews/` 下的独立报告文件，收口清单与 handover 链接该路径，不能只写一行状态；每个 task 后的轻量检查不强制落盘。`doc-sync-matrix` 同步新增对应行。
- `session-close-reconciler` 增加两条收口清单格式规则：结论为「本轮无适用项」的分节合并成一行显示（仅合并显示，不减少检查项，Learn 候选不参与合并）；验证失败必须写入「明确缺失」、验证未跑或证据不完整必须写入「建议补充」，即使归因为环境问题也要显示，只在条目中标注归因。两条规则均为 soft check，不自动阻断、不自动改测试。

## [0.2.0-alpha] — 2026-07-25

### 新增

- 根目录新增 `SKILL.md`，作为开源用户显式指定给 agent 的 zimaflow 入口 router。
- `scripts/install.sh` 增加 `--adapter-dir <dir>`，可重复生成 `zimaflow-<name>/SKILL.md` 扁平 adapter；保留 `--claude-code` 作为项目级 Claude Code adapter 快捷方式（默认不改动任何 agent 配置）。
- `bin/zimaflow` 新增单仓 `state` / `recall` first slice，用 `.zimaflow-state.yaml` 汇总 active change、handover 指针和 bit-rot 提醒；跨项目 `--all` / `--project` 暂不开放。
- 新增 `tests/state.sh` 和 `tests/recall.sh`，并接入 `tests/smoke.sh`。

### 修复

- 统一 skill 内引用的环境变量：`session-close-reconciler`、`sdd-router` 中未定义的 `$ZIMAFLOW_DIR` 更正为文档中已定义的 `$ZIMAFLOW_HOME`。
- 统一 skill 内 `references/` 引用为 `$ZIMAFLOW_HOME/references/`（原先的裸相对路径和 `zimaflow/references/` 前缀在 skill 被移入独立文件夹后会失效）。
- 自动发现结构生成的 `zimaflow-<name>/SKILL.md` 同步把 frontmatter `name` 改写为 `zimaflow-<name>`，与目录名保持一致；否则 Claude Code 会因 name 与目录名不匹配而校验报错、无法加载。

### 文档

- 强化首页 README 的低记忆入口、工作流概览图、可靠性机制和学习要点说明，让 v0.1 主链路更容易快速理解。
- README 与 `docs/getting-started.md` 补充通用源文件优先、Claude Code 自动发现 adapter、`--adapter-dir` 目录结构要求，以及 `ZIMAFLOW_HOME` 与 `$ZIMAFLOW_HOME/references/` 的对应关系。
- 新增 `docs/session-continuity.md`、`docs/guardrails.md` 和 `docs/v0.2-alpha-plan.md`，把后续公开方向整理为跨 session 续接、CLI 读取端和 soft guardrails，而不是同步维护者完整工作区。
- 新增 `docs/cli-reference.md` 说明 `close`、单仓 `state` / `recall` 和 reminder-only hooks。
- 更新 `docs/open-source-boundary.md` 和 `docs/workflow-overview.md`，明确 v0.2 alpha 候选范围和暂不公开内容。
- 将项目注册表和知识使用账本改写为可选进阶上下文，避免公开主链路依赖维护者工作区约定。
- 对齐 `references/workload-dict.md` 中生产环境部署的措辞。

## [0.1.0] — 2026-07-15

首次公开发行。包含一条经过发行审查的主链路（从一句粗略需求到可追踪的实现闭环），以及一层贯穿主链路的工程护栏。

### 纳入

- **主链路 skills**：`sdd-router`、`requirement-contract`、`task-planning`、`route-decision-recorder`、`openspec-superpowers-bridge`、`spec-compliance-check`、`session-close-reconciler`、`handover-manager`、`learn`。
- **老项目认知底座**：`legacy-project-onboarding`，为存量代码库建立架构总览、模块地图、接口清单、数据模型/ER、测试入口、关键链路和隐性知识问答，并产出 thin context index。
- **工程护栏**：
  - `requirement-contract` 验收标准优先 Given/When/Then 三段式，反问上限（最多 2 轮）与假设默认值。
  - `spec-compliance-check` 破坏性变更门槛（B4：删码≥5行 / 改公共接口 / 改 schema / 改权限 / 改写库路径先排查引用面）与沿用现有抽象检查（B5）；均为审查标记，不自动回滚或改代码。
  - `sdd-router` 问题排障 / 故障定位路径、P1/P2/P3 需求变更影响分级、纠偏 / rewind 识别、thin context-index 读取和未关闭 state 检测。
  - `session-close-reconciler` hotfix / rewind / secrets 三类 Guardrail 收口核对与 `.zimaflow-state.yaml` 状态对账。
  - `handover-manager` Guardrail 承接段落、Zimaflow State 与 Context Index 读写。
- **参考表**：`references/` 下已脱敏的通用字典、矩阵与设计说明（工时字典、知识锚点映射、知识使用指南、文档同步矩阵、`Design-Context-Intelligence-Baseline.md`、`Design-Zimaflow-State.md`、`lessons-common.md` 通用经验库种子）。
- **agent 规则**：`rules/`（Claude、Codex）下面向公开使用的最小规则片段。
- **最小 CLI**：`bin/zimaflow`，提供 `close`、JSON 输出和 reminder-only git hook。
- **基础安装脚本**：`scripts/install.sh`，仅复制公开仓内容，不做 OpenSpec 初始化、项目注册或项目文档目录创建。
- **文档**：`docs/getting-started.md`、`docs/workflow-overview.md`、`docs/open-source-boundary.md`；面向维护者的 `RELEASING.md`。
- **端到端 demo**：`examples/demo/`，无网络、无凭证，`run-demo.sh` 走通"需求 → handover"全过程。
- **工程配置**：`LICENSE`（MIT）、`.gitignore`、`AGENTS.md`、`tests/smoke.sh`。

### 后续规划（计划提供）

- `proto-review`：产品原型评审，需公开原型模板和示例资产后开放。
- 一键初始化器与完整 CLI（per-change 状态、知识淘汰复查、artifact 漂移检查）。
- 知识使用闭环：留痕账本加淘汰复查。

[Unreleased]: https://github.com/zima-explorer/zima-flow/compare/v0.2.0-alpha...HEAD
[0.2.0-alpha]: https://github.com/zima-explorer/zima-flow/compare/v0.1.0...v0.2.0-alpha
[0.1.0]: https://github.com/zima-explorer/zima-flow/releases/tag/v0.1.0
