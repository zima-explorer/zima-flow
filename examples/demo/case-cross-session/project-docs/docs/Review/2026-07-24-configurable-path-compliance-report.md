# 可配置 todo 路径 · Spec Compliance Report

> 类型：spec-compliance-check 审查报告
> 依据模板：`skills/spec-compliance-check.md`
> change：add-configurable-todo-path
> 触发条件：全部 task（T1–T6）完成后的全量审查
> 审查时间：2026-07-24（Session 2 · T6）

## Spec Compliance Report

**变更**：add-configurable-todo-path
**审查时间**：2026-07-24

### 场景覆盖

对照 [需求 brief](../Requirements/2026-07-24-configurable-path-brief.md) 的 Given/When/Then 验收标准：

- ✅ 场景 1：Given 传入 `--file /path`，When 执行 `add`，Then 写入指定文件 — 已实现（`app/todo.sh` 参数解析），已测试（`app/test-todo.sh` 检查 1–2）
- ✅ 场景 2：Given 设置 `TODO_FILE`，When 未传 `--file` 执行 `add`，Then 使用该环境变量指定的文件 — 已实现，已测试（`app/test-todo.sh` 检查 5）
- ✅ 场景 3：Given 两者均缺省，When 执行任意命令，Then 沿用默认 `.todo.txt`（行为不回归）— 已实现（`app/todo.sh` 默认值逻辑），已测试（`app/test-todo.sh` 检查 6，本轮审查新增）
- ✅ 场景 4（异常路径）：Given 任务列表中没有 id `99`，When 执行 `done 99`，Then 报清晰用户错误并以非 0 退出 — 已实现，已测试（`app/test-todo.sh` 检查 4）

> 审查发现：首次实现（S1–S2）的测试脚本覆盖了场景 1、2、4，唯独场景 3（默认路径不回归）只有实现、没有对应的自动化测试。本次合规审查在补充测试后转为 ✅，测试总数从 6/6 提升为 7/7（见 `app/test-todo.sh` 检查 6 与 `verify passed: 7/7 checks`）。这属于审查过程中真实发现并修复的场景覆盖缺口，不是事后补写的既成事实。

### 架构一致性

对照 [design.md](../../openspec/changes/add-configurable-todo-path/design.md) 的决策：

- ✅ 决策 1：路径解析优先级 `--file` > `TODO_FILE` > 默认 `.todo.txt` — 与 `app/todo.sh` 实现一致（先设默认值，再被 `TODO_FILE` 覆盖，最后被 `--file` 解析覆盖）
- ✅ 决策 2：`--file` 可出现在子命令前后 — 与实现一致（参数扫描循环不依赖位置）
- ✅ 决策 3：不改动持久化格式（`id|done|title`）— 与实现一致，`cmd_add` / `cmd_list` / `cmd_done` 均未改动行式格式

### 排除范围

对照 [proposal.md](../../openspec/changes/add-configurable-todo-path/proposal.md) 的「不做什么」：

- ✅ 未触碰排除范围：未实现多文件合并、未做云同步、未提供文件迁移工具，`add` / `list` / `done` 的既有输出格式未改动

### 破坏性变更（B4）

- ✅ 无破坏性变更：未删除代码（≥5 行）、未改动被外部调用的公共接口签名、未改数据 schema／持久化格式、未涉及权限鉴权、未改变已有数据写入语义（`add` 仍是追加写，`done` 仍是原地标记）。本次唯一的公共接口变化是新增 `--file` 参数与 `TODO_FILE` 环境变量，属纯增量能力，默认行为不变。

### 沿用抽象（B5）

- ✅ 无同类现有实现：本案例仓库范围内（`examples/demo/case-cross-session/app/`）此前没有任何参数解析或路径解析的公共工具函数可供复用；新增的 `--file` 扫描逻辑是该脚本内的合理新增，不构成重复造轮子。

### 结论

- [x] 全部通过 → 可进入 close
- [ ] 有未覆盖场景 → 需要补实现（已在本轮审查中补齐，见上方"场景覆盖"备注）
- [ ] 有设计偏离 → 需要决策：更新 spec 还是修改实现
- [ ] 超出范围 → 必须回退超范围的改动
- [ ] 有破坏性变更未评估 → 补引用面排查 + 影响说明后由用户决策
- [ ] 有未沿用的现有抽象 → 由用户决定是否重构沿用

## 证据指针

- 测试脚本：[`app/test-todo.sh`](../../../app/test-todo.sh)（`verify passed: 7/7 checks`）
- 实现：[`app/todo.sh`](../../../app/todo.sh)
- 规范来源：[proposal.md](../../openspec/changes/add-configurable-todo-path/proposal.md)、[design.md](../../openspec/changes/add-configurable-todo-path/design.md)、[tasks.md](../../openspec/changes/add-configurable-todo-path/tasks.md)
