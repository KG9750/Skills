# AGENTS.md instructions

所有回答默认使用中文，必要时可保留英文术语、命令、路径和接口名。

## 渐进式披露入口

进入 `{{PROJECT_NAME}}` 时，优先从少量入口获取上下文：

- `CONTEXT.md`：项目背景、边界和当前事实。
- `PLANS.md`：计划入口，指向活跃计划与历史计划。
- `DESIGN.md`：设计与产品体验入口。
- `FRONTEND.md`：前端实现与界面约定入口。
- `docs/generated/project-directory.md`：自动生成的目录索引。

## 工作方式

- 先明确假设和成功标准，再修改文件。
- 只做完成当前请求必须做的改动。
- 不覆盖已有用户内容。
- 多步骤任务要验证结果。
