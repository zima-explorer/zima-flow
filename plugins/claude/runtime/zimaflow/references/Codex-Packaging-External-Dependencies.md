# Codex Plugin External Dependencies

> 类型：运行时参考
>
> 适用：Codex Packaging Adapter first slice

## 插件自带

生成的 Codex Plugin 包含 zimaflow 的入口 wrapper、允许列表中的嵌套 Skill、`bin/zimaflow`、OpenSpec 配置和运行时 references。它不包含 tests、生成 runtime、个人 marketplace、项目产品文档或宿主安装路径。

## 外部依赖

| 依赖 | 本切片行为 | 缺失时的边界 |
| --- | --- | --- |
| zimaflow CLI | 作为包内 `bin/zimaflow` 的确定性内核随包复制 | Doctor 的 `cli_missing` / `cli_version_incompatible` 可见；adapter 不安装。 |
| OpenSpec | 不 vendor、不安装；包内只保留 zimaflow 对其的 Skill 指引与配置 | 项目未初始化时由 Doctor 报告 `project_not_initialized`；正式 setup/installer 留后续。 |
| Superpowers | 不 vendor、不安装；由宿主已有能力或团队配置提供 | 本切片只声明使用前提，不伪造可用性或生成替代规则。 |

`installer/` 不进入本 first slice：它含内部开发环境引导，且正式 install / upgrade / repair 语义尚未决策。用户可先通过 Doctor 取得缺口和 `resume_intent`；后续 installer slice 再定义修复操作与授权边界。

## 开发期验证依赖

Plugin creator 的 `validate_plugin.py` 使用 PyYAML。它只在开发 / CI 验证时运行，不属于生成包或宿主运行时。执行测试时可设置 `ZIMAFLOW_PLUGIN_VALIDATOR_PYTHON` 指向已有、带 PyYAML 的 Python；若没有该解释器，验证应明确失败，不自动下载或安装依赖。
