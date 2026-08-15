---
name: doc-style-ch
description: Generate polished Chinese documents in a reusable ink-paper and cinnabar visual system. Use when the user asks for doc-style-CH, 朱砂宣纸风、墨色中文长文、研究报告、方案、说明书、项目文档或需要统一中文文档视觉格式的离线可读 HTML 文档。Do not use for blind testing, scoring, answer-key sealing, or evaluation workflows unless the user explicitly adds those requirements.
---

# doc-style-CH

将中文内容整理成离线可读、响应式、可打印的 HTML 文档。样式全部内联；用户提供图片时，将本地图片作为文档附件一同交付。固定视觉语言，允许内容结构随任务变化。

## 默认交付

1. 默认输出一个 `.html` 文件；用户需要可维护源文件时，同时保留对应 `.json`。
2. 使用 `assets/document-shell.html`，不要从零重画视觉系统。
3. 使用 `scripts/render_document.py` 渲染结构化 JSON；不要手工替换模板占位符。
4. 生成后运行 `scripts/test_render_document.py`，再检查最终 HTML 中的标题、目录、章节数和打印样式。
5. 文档默认使用中文；英文术语、代码和专名按内容需要保留。

## 内容工作流

1. 明确文档目的、读者和信息层级。
2. 将内容整理为标题、副标题、元信息和章节；章节数量以内容需要为准，不机械凑数。
3. 每节先给结论或主张，再给证据、解释或行动项。
4. 选择最合适的内容块：段落、项目符号、编号步骤、引言、提示框、表格、代码或分隔线。
5. 将结构写入符合 `references/input-schema.md` 的 JSON。需要起步样例时，复制并改写 `references/example-document.json`。
6. 执行：

```bash
python3 scripts/render_document.py input.json output.html
```

从其他目录调用时，将脚本路径替换为本 Skill 的绝对路径。

## 视觉合同

- 宣纸暖白背景，深墨正文，朱砂作为唯一主要强调色，苔绿只用于成功状态。
- 楷体用于大标题与章节标题，宋体用于长文阅读，黑体用于界面标签和元信息。
- 桌面端使用深墨侧栏目录与宽正文；窄屏自动改为顶部标题区和横向目录。
- 章节标题具有编号、细线和充足留白；正文行宽保持适合中文长文阅读。
- 表格、引用、代码和提示框必须属于同一套纸墨语言，不使用通用 SaaS 卡片风。
- 不添加盲测进度、候选 A/B、评分控件、答案键指纹或任何评测安全元素。

完整设计令牌和排版规则见 `references/style-spec.md`。

## 内容约束

- 不用空泛大标题堆叠制造“高级感”。
- 不把每段都放进卡片；正文以自然文流为主。
- 表格只用于确有映射或比较关系的内容。
- 提示框只突出真正需要注意、决定或执行的内容。
- 不依赖网络字体、CDN、外部 JavaScript 或远程图片。
- 用户提供本地图片时，只在 JSON 中使用相对路径；交付时保持 HTML 与图片目录关系稳定。

## 验证

至少检查：

- JSON schema、字段类型、必填字段和内容块类型合法；可选字段省略时使用默认值，出现时不接受 `null`。
- 图片只引用随文档交付的相对本地路径，不引用远程 URL 或根路径。
- 模板自身不残留未解析的 `{{...}}` 占位符；用户原文中的同形字符串必须原样保留。
- 目录链接与章节 `id` 一一对应。
- 输出不含盲测、评分、A/B、答案键等模板残留。
- HTML 在无网络环境可读，窄屏不横向溢出，打印时侧栏不遮挡正文。
