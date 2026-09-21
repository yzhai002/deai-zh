# Agent 指南

本文件说明如何修改去AI味（deai-zh）而不破坏包结构。

## 仓库内容

去AI味是一个 Markdown 技能。`SKILL.md` 是 agent 读取的提示词，仓库无构建步骤。保持可移植，不要写只适用于一两个 agent 工具的指令。

## 关键文件

- `SKILL.md` 是唯一的事实来源：YAML 元数据、26 个按强度编号的模式、工作方法。
- `README.md` 讲安装、用法、模式表和版本历史，必须与 SKILL.md 同步。
- `.claude-plugin/plugin.json` 描述 Claude 插件。
- `scripts/validate-package.py` 检查包文件一致性。
- `scripts/evaluate.py` 检查改写里脚本看得见的痕迹：指纹、破折号省略号、高频词、均匀句长、丢失的数字。
- `eval/cases/` 是评测集：一个目录一个用例，各含 `input.md` 和 `rewrite.md`。

## 修改规则

- **模式：** 从 1 连续编号、无空档，最强的排前面。新痕迹只有现有模式覆盖不了时才立新模式，优先并入现有模式。增删或重编号时，同步更新 README 表格、README 节标题（"N 个模式"）和所有 §引用；validator 从标题推导数量。脚本可查的新模式要在 `eval/cases/` 加用例。
- **版本：** `SKILL.md` 的 `metadata.version`、README 第一条版本条目、`.claude-plugin/plugin.json` 三处保持一致。不要在技能顶层加 `version` 字段。
- **历史：** 任何行为变化都写一条简短的 README 版本注。
- **检查：** 发布前运行 `python3 scripts/validate-package.py` 和 `python3 scripts/evaluate.py --all`。

## 写作风格

文档、提示词、校验消息都用平实中文：先说结论，用常用词和主动句，句子段落要短，同一事物用同一个叫法，要求用"必须"，删掉重复和多余的词。

## 与英文版的关系

英文版 [deai](https://github.com/yzhai002/deai) 是框架来源。结构性改动（工作方法、强弱信号分级、防误伤规则）尽量两边同步；词汇表和示例各自独立维护。
