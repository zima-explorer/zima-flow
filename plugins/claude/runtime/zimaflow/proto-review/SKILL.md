---
name: proto-review
description: >
  Use when a product-facing requirement needs a visual review prototype before
  OpenSpec, especially for new pages, multi-step flows, multi-state UI, or ideas
  without a complete PRD.
sync: false
sync_reason: 有意不同步：套件内部子 Skill，由 Zimaflow 主入口路由；宿主 adapter 从独立源码仓生成或注入同一能力根
---

# Proto Review — 产品原型评审

## 职责

你负责把想法、PRD、路线决策或零散需求整理成可评审的 HTML 原型上下文。目标不是生成生产前端代码，而是在进入 OpenSpec propose 之前，让人和 Agent 对页面、状态、交互旁注、数据来源和待确认问题形成同一份可追溯依据。

## 适用场景

优先使用：

- 新页面、新一级菜单、新流程向导
- 多状态 UI：空态、异常态、处理中态、权限态、已发布/已下架等
- 涉及权限、计费、敏感信息、数据安全或用户可见状态机
- 需要产品、设计、研发、测试共同评审
- 用户明确说"缺原型"、"先看页面"、"PRD 不直观"、"只有想法没有 PRD"

通常不使用：

- 纯后端接口、批处理、CLI、内部脚本
- 小 bugfix、文案或样式微调
- 已有稳定设计稿且本轮不改变产品理解

## 前置 Gate：需求契约

除紧急热修复外，产品原型评审必须基于已确认的需求契约：

- PRD-driven：读取已确认的 PRD / brief / Decisions，并在 `review-notes.md` 的"输入来源"中引用需求契约路径
- Idea-driven：如果只有想法或零散描述，先交给 `requirement-contract` 生成并确认 brief/PRD，再进入原型评审
- 契约仍是"草稿/待确认"或路径缺失时，暂停，不生成 `prototype.html`

`proto-review` 可以帮助澄清页面和状态，但不能替代需求契约。AI 假设必须留在 review-notes 的"AI 假设/待确认问题"，不能当作已确认需求进入 OpenSpec。

## 输入模式

### PRD-driven

已有 PRD、设计文档、Decisions 或 OpenSpec 草稿时：

1. 读取需求来源，提取页面、流程、状态、业务规则、Non-goals
2. 读取项目设计规范或同类页面规范
3. 生成原型时只表达本轮范围，不吞掉后续迭代内容

### Idea-driven

只有想法、零散描述或对话上下文时：

1. 先补一份轻量需求骨架
2. 把 AI 推断内容明确标为"假设"
3. 把必须由用户拍板的内容放入"待确认问题"
4. 原型状态标记为"探索原型 / 待评审"，不得当作已确认 PRD

## 输出位置

默认输出到项目文档目录：

```text
<docs_dir>/Prototypes/YYYY-MM-DD · <需求名> prototype.html
<docs_dir>/Prototypes/YYYY-MM-DD · <需求名> review-notes.md
```

如果项目已有原型目录或 PRD 预览机制，优先沿用项目约定，但必须保证文件可被 OpenSpec proposal/design 引用。

## prototype.html 结构

推荐使用三栏结构契约：

```text
左侧：页面 / 状态导航
中间：可视化原型
右侧：PRD 旁注
```

约束：

1. 左侧导航全文件唯一，每个 section 一条入口
2. 中间原型和右侧旁注一一对应
3. 一个 section 只表达一个页面、弹窗、抽屉或关键状态
4. 不把多个业务状态塞进同一个旁注面板
5. 不为纯 hover/focus 等常规组件态单独开 section，除非它改变业务理解

### section 命名

section 命名应可被评审者和后续 Agent 直接引用：

- 应用广场 - Web 页面卡片
- 我的应用 - 空态
- 创建流程 Step 2 - 上传失败
- 管理员管理 - 已发布未上线

推荐编号方式：

| 形态 | 写法 | 用途 |
|------|------|------|
| 主页面 / 主流程 | `应用广场-01`、`创建流程-02` | 评审者按主序号顺读即可理解主流程 |
| 同页变体 | `创建流程-02-上传失败`、`详情页-01-删除确认` | 同一页面的错误态、弹窗态、确认态 |
| 空态 / 权限态 | `我的应用-01（空态）`、`管理页-02（无权限）` | 与主页面同结构，但业务含义不同 |

主序号代表新页面或新视图；变体编号代表同一页面的另一种形态。同一主序号下变体超过 3 个时，应回头判断是否需要拆成独立页面或独立 slice。

### 旁注写法

右侧旁注按视觉顺序描述：

- 页面元素
- 数据来源
- 点击行为
- 状态差异
- 权限与敏感信息
- 本期不做
- 待确认问题

规则：

- 一个可感知元素一条说明
- 用产品语言，不写代码语言
- 描述必须包含“是什么”和“点击后 / 状态变化后发生什么”
- 重复结构只在第一个 section 完整描述，后续 section 只写差异
- 改动型原型只写本次新增或改变的元素，不复述既有页面所有功能
- 失败、异常、权限不足、数据为空等业务状态要独立说明

推荐句式：

```markdown
- **{元素名}**：展示「{文案或内容}」，数据来源：{静态 / 后端 / 用户输入 / 配置}，点击后{行为}
- **{状态名}**：当{条件}时展示{状态表现}，用户可{恢复路径或下一步}
- **{按钮名}**：展示「{文案}」按钮，点击后{跳转 / 弹窗 / 提交 / 禁止原因}
```

### 评审脚手架

`data-comp` / `data-target`、PRD ↔ 原型 hover 高亮、主题 token、组件库和注入脚本暂不作为 v0.1 必选能力。

如果某次原型需要临时加入高亮脚手架，必须在 `review-notes.md` 中注明：

- 这些属性和脚本只用于评审
- 研发实现时必须剥离
- 不得进入生产前端代码

## review-notes.md 结构

```markdown
# <需求名> 原型评审说明

> 状态：探索原型 / 待评审 / 已评审
> 输入模式：PRD-driven / Idea-driven
> 原型文件：<prototype.html 路径>

## 一、输入来源

## 二、已确认结论

## 三、原型中的 AI 假设

## 四、待用户确认问题

## 五、建议进入 OpenSpec 的范围

## 六、暂不进入本期的内容

## 七、页面与状态清单
```

## 评审规则

- 不把 `prototype.html` 当生产代码
- 不把 AI 假设当已确认需求
- 不把后续迭代内容混进本期 OpenSpec
- 评审后必须更新 `review-notes.md` 状态和结论
- 进入 OpenSpec propose 时，proposal 或 design 必须引用原型文件和评审说明

## 移交给 zimaflow

评审完成后：

1. 如果需求范围仍未拍板，回到 `route-decision-recorder`
2. 如果 first slice 已确认，进入 OpenSpec explore/propose
3. 如果评审发现需求过大，先拆子项目或多个 slice

如果本轮 OpenSpec change 名称已确定，同时更新：

```text
openspec/changes/<change>/.zimaflow-state.yaml
```

写入内容遵循 `references/Design-Zimaflow-State.md`：

- `phase: prototype_reviewed`
- `prototype.enabled`
- `prototype.prototype_path`
- `prototype.review_notes_path`
- `prototype.status`

输出给下一阶段的最小上下文：

- 原型文件路径
- 评审说明路径
- 已确认结论
- 待确认问题
- 本期 OpenSpec 范围

## 后续参考

外部 `proto-gen` 有一套更重的 HTML 原型资产和结构契约，包括三栏布局、section 编号、PRD 旁注写法、PRD ↔ 原型双向高亮、主题 token 和组件库。当前 `proto-review` 只吸收流程思想，不安装、不复制外部资产。

需要增强原型生成能力时，先阅读 `references/proto-gen-reference.md`，再决定是否进入 v0.2 设计。
