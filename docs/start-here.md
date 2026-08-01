# 从这里开始

zimaflow 是给**个人开发者和小团队**的一套 AI Coding 工程闭环：把一次需求从 brief、规范、实现、验证到收口和经验回流，完整走完。

它不让 AI 写得更快，而是让 AI 在正确上下文、明确契约和可验证结果里行动。

> **当前状态**：已开源，正在做体验打磨。CLI 版本 `0.2.0-alpha`。

这一页把四件事收在一起：开源地址、快速开始、可复制的产物模板、完整案例。按顺序读大约 15 分钟。

---

## 1. 开源地址

仓库就是这里：<https://github.com/zima-explorer/zima-flow>

主链路的 9 个 skill 在 [`skills/`](../skills/)，跨 skill 的共同约束在 [`rules/`](../rules/)，可选 CLI 在 [`bin/zimaflow`](../bin/zimaflow)。

想让 agent 显式使用 zimaflow，让它从根入口 [`SKILL.md`](../SKILL.md) 开始读。

---

## 2. 快速开始

### 3 分钟：先看产物长什么样

```bash
git clone https://github.com/zima-explorer/zima-flow.git
cd zima-flow
examples/demo/run-demo.sh
```

这是纸面演练——从一句需求出发，把 brief、任务拆解、OpenSpec change 骨架、收口清单、handover 的产物摆出来给你看。导读见 [`examples/demo/README.md`](../examples/demo/README.md)。

### 10 分钟：跑一个真实案例

```bash
examples/demo/case-evidence-closure/run-case.sh
```

它会真实执行测试，输出 `verify passed: 6/6 checks`，然后打印本案例的全部产物路径。全程只用 bash，不依赖网络、凭证或任何外部服务。

### 装到自己项目上

```bash
scripts/install.sh --target "$HOME/.zimaflow"
```

安装脚本只复制公开仓内容，不初始化 OpenSpec、不创建项目注册表、不修改 shell profile 或 agent 配置。完整安装选项、agent skills 自动发现、环境变量说明见 [快速开始指南](getting-started.md)。

---

## 3. 可复制的产物模板

zimaflow 不发空白模板——**填过的模板比空白模板有用**。下面四份是 `case-evidence-closure` 这次真实需求产出的实际文件，可以直接复制改写：

| 产物 | 文件 | 它解决什么 |
|------|------|-----------|
| 需求 brief | [`Requirements/…-brief.md`](../examples/demo/case-evidence-closure/project-docs/docs/Requirements/2026-07-29-list-status-filter-brief.md) | 用 Given/When/Then 把「想要什么」写成可验收的契约，而不是一句话需求 |
| 任务台账 | [`Tasks/…-tasks.md`](../examples/demo/case-evidence-closure/project-docs/docs/Tasks/2026-07-29-list-status-filter-tasks.md) | 轻量拆解 first slice，不上 OpenSpec 三件套也能有计划 |
| 合规报告 | [`Reviews/…-compliance-report.md`](../examples/demo/case-evidence-closure/project-docs/docs/Reviews/2026-07-29-list-status-filter-compliance-report.md) | 让「合规检查已通过」变成一份第三方能独立复查的文件 |
| 收口清单 | [`Closing/…-closing.md`](../examples/demo/case-evidence-closure/project-docs/docs/Closing/2026-07-29-list-status-filter-closing.md) | 让「做完了」变成逐项对账：测试、git 状态、未覆盖风险、经验候选 |

**怎么用**：复制这四个文件到你自己项目的对应目录，把内容换成你的需求。不需要一次用齐——多数需求从 brief 和收口清单两份开始就够了。

---

## 4. 完整案例

[`examples/demo/case-evidence-closure/`](../examples/demo/case-evidence-closure/README.md) —— 一次小需求怎么把证据收口。

**需求**：给已有的本地 todo CLI 增加 `list --status pending|done|all`。真实缺口是渲染层的判定逻辑已经存在，缺的只是让用户选择的入口。

**它证明的事**：一次 20 多行的小改动，也能留下可复跑的验证、独立落盘的合规报告和逐项对账的收口清单——而且**不需要写 OpenSpec 三件套**。

仓库里另有一个走完整模式的案例 [`case-cross-session`](../examples/demo/case-cross-session/README.md)，载体相同、重量不同，演示怎么跨 session 用 `state` / `recall` / `handover` 接住上下文。两个放在一起，正好看清档位差别在哪。

> zimaflow 的默认动作不是把所有事流程化。只有触发 schema 变更、权限、数据写入路径或需要正式审查留痕时，才升级到完整模式。

---

## 它和 OpenSpec / Superpowers 是什么关系

zimaflow **复用**这两者，不复制也不替代它们：

```text
OpenSpec      解决「AI 开始写之前，我们是否对需求和变更达成一致」
Superpowers   解决「AI 执行过程中，是否遵循工程纪律」
zimaflow      解决「一次任务如何完整跑完，并且下一次还能继续」
```

zimaflow 的价值在编排、状态连续、证据收口和经验回流。

---

## 它不是什么

- 不是 AI IDE，也不替代 Codex / Claude Code / Cursor。
- 不是项目管理系统，不是企业级研发治理平台。
- 不是完整的 agent 框架。
- 不是 Prompt 模板合集。

如果你还没开始用 AI 写代码，zimaflow 现在帮不上忙；它解决的是「AI 写得挺快，但维护和交接变难了」之后的问题。

---

## 接下来

- 想理解整条链路怎么串：[工作流总览](workflow-overview.md)
- 想知道 CLI 能做什么：[CLI 参考](cli-reference.md)
- 想了解跨 session 怎么接上：[session 续接](session-continuity.md)
- 想知道有哪些护栏、分别在哪一环生效：[护栏说明](guardrails.md)
- 想知道公开版和内部版的边界：[开源边界](open-source-boundary.md)

用下来卡在哪一步，欢迎开 [issue](https://github.com/zima-explorer/zima-flow/issues) 告诉我们。
