---
name: doc-style-ch
description: Generate polished Chinese HTML documents, print-ready PDFs, and PNG visual reports in a reusable ink-paper and cinnabar system. Use when the user asks for doc-style-CH, 朱砂宣纸风、墨色中文长文、研究报告、方案、说明书、项目文档、可打印 PDF、图片版报告、中文海报或需要统一中文视觉格式的离线交付物。Do not use for blind testing, scoring, answer-key sealing, or evaluation workflows unless the user explicitly adds those requirements.
---

# doc-style-CH

将中文内容整理成离线可读的 HTML、可打印的 PDF 或固定画布的 PNG 视觉报告。三种格式共用内容 JSON、渲染器和朱砂宣纸视觉系统；用户提供图片时，将本地图片作为附件一同交付。

## 默认交付

1. 以用户指定的格式为准；未指定时默认交付 `.html`。PDF 或 PNG 均保留对应中间 HTML，需要可维护源文件时再保留 `.json`。
2. 使用 [assets/document-shell.html](assets/document-shell.html)，不从零重画视觉系统。长文 HTML/PDF 用 `document` profile；单幅图片用 `image` profile。
3. 使用 [scripts/render_document.py](scripts/render_document.py) 渲染结构化 JSON；不手工替换模板占位符。
4. PDF 和 PNG 使用 [scripts/export_artifacts.py](scripts/export_artifacts.py) 从已渲染 HTML 导出，保证三种格式的内容与视觉系统同源。
5. 生成后运行两组脚本测试，并对每种最终格式做一次视觉检查；不得只以“文件存在”代替渲染验收。
6. 内容默认使用中文；英文术语、代码和专名按需要保留。

## 格式选择

- **HTML**：默认 `document` profile。适合长文、悬浮目录导航、响应式阅读和离线分发。
- **PDF**：先生成 `document` profile HTML，再导出 A4 PDF。适合打印、归档、正式方案和研究报告。
- **PNG 图片**：生成 `image` profile HTML，再按目标 viewport 截图。适合单幅摘要、海报、社交分享图、封面或用户明确要求的单张完整长图。摘要默认画布 `1600x2000`（4:5）；完整长图根据内容实测高度确定画布。

用户只说“图片版”而未说明形式时，默认做一张摘要图，不把长报告静默裁成超长图。用户明确要求“所有内容放在一张 PNG”时，改用完整内容源、收紧 `image` profile 并在目标宽度下测量 `scrollHeight`，将画布高度设置为完整内容高度；高度超过 `8192px` 时不得缩成不可读小字，应说明边界并征求拆分。若要求“逐页图片”，先导出 PDF，再使用环境中可用的 PDF 页面渲染器按页转图。

## 内容工作流

1. 明确文档目的、读者和信息层级。
2. 将内容整理为标题、副标题、元信息和章节；章节数量以内容需要为准，不机械凑数。
3. 每节先给结论或主张，再给证据、解释或行动项。
4. 选择最合适的内容块：段落、项目符号、编号步骤、引言、提示框、表格、代码或分隔线。
5. 将结构写入符合 `references/input-schema.md` 的 JSON。需要起步样例时，复制并改写 `references/example-document.json`。
6. 渲染 HTML：

```bash
python3 scripts/render_document.py input.json build/report.html --profile document
```

7. 导出 PDF：

```bash
python3 scripts/export_artifacts.py build/report.html --pdf build/report.pdf
```

8. 导出 PNG 摘要图：

```bash
python3 scripts/render_document.py input.json build/summary-image.html --profile image
python3 scripts/export_artifacts.py build/summary-image.html --png build/summary.png --viewport 1600x2000
```

从其他目录调用时，将脚本路径替换为本 Skill 的绝对路径。导出脚本会自动查找 Chrome/Chromium/Edge；自动查找失败时用 `--browser /absolute/path/to/browser` 显式指定。若执行环境禁止从终端启动浏览器，使用环境已有的浏览器自动化能力执行等价的 PDF/截图导出，并照常完成文件与视觉验证；应把脚本启动失败记录为环境限制，不得误报成输出已验证。

## 视觉合同

- 宣纸暖白背景，深墨正文，朱砂作为唯一主要强调色，苔绿只用于成功状态。
- 楷体用于大标题与章节标题，宋体用于长文阅读，黑体用于界面标签和元信息；主标题、章节标题和章节数字统一使用比正文明显更重的字重。
- HTML 正文使用单列流式布局，字号、间距、边距和内容宽度随窗口平滑变化；宽屏正文必须随视口明显伸展并设置合理上限，在 320px 手机、平板、桌面和超宽屏均不得产生页面级横向溢出。
- HTML 左上角提供至少 44×44px 的深墨目录按钮；鼠标 hover 显示仅含目录结构的面板，面板使用 60% 深墨背景和轻度背景模糊，不重复主标题、副标题或元信息。点击或键盘激活可固定展开，目录项可直接跳转章节，并支持清晰的 focus 状态和 Escape 关闭。
- PDF 使用 A4 分页，不显示目录按钮或交互目录；主标题使用醒目的打印字号并避免孤字换行，页脚居中显示“当前页 / 总页数”，同时尽量避免标题、引用、图片和表格在页间断裂。
- PNG 使用目标画布构图：深墨顶栏、单列内容和紧凑章节间距；摘要使用固定 4:5 画布，明确要求完整长图时改用实测高度。不显示交互目录或滚动条，在目标 viewport 中不得被裁切。
- PNG 大标题应优先自然单行，不使用过窄的字符宽度限制制造孤字换行；内容区应接近画布有效宽度，避免窄列导致左右大面积无效留白。明确要求单张完整长图时，尽可能纳入全部章节并使用实测内容高度。
- 章节标题具有编号、细线和充足留白；正文行宽保持适合中文长文阅读。
- 主标题下不额外输出 `doc-style-CH` 品牌署名；标题区只保留实际内容需要的副标题和元信息。
- 主标题下的元信息 tag 每项只使用一层单线框，不叠加内外双框。
- 表格、引用、代码和提示框必须属于同一套纸墨语言，不使用通用 SaaS 卡片风。
- 带底色的引用说明和 note/warning/success 提示框属于辅助信息层，左右统一占满内容列宽，上下高度随实际文字自动增长，不设置固定高度；正文应明显小于普通正文，标题与出处再小一级。代码区和表头不适用这条说明字号规则。
- 代码块使用纸墨编辑器结构：取消最外层框线，以统一浅灰底色、轻微圆角和深墨等宽字形成独立区域。工具栏保持透明，不在 `<bash>` 所在行添加加深色带；语言统一显示为 `<bash>`、`<zsh>`、`<fish>`、`<python>` 这类尖括号标签，只使用朱砂文字，不添加独立底色。不要用可配置且含义不稳定的 `$`、`%`、`>` 代替语言名。HTML 可显示复制按钮，PDF/PNG 必须隐藏复制按钮。
- 不添加盲测进度、候选 A/B、评分控件、答案键指纹或任何评测安全元素。

完整设计令牌和排版规则见 `references/style-spec.md`。

## 内容约束

- 不用空泛大标题堆叠制造“高级感”。
- 不把每段都放进卡片；正文以自然文流为主。
- 表格只用于确有映射或比较关系的内容。
- 提示框只突出真正需要注意、决定或执行的内容。
- 不依赖网络字体、CDN、外部 JavaScript 或远程图片；PDF/PNG 导出期间保持离线。
- 用户提供本地图片时，只在 JSON 中使用交付目录内的相对路径，不允许 `..` 越界；交付时保持 HTML 与图片目录关系稳定。

## 验证

至少检查：

- JSON schema、字段类型、必填字段和内容块类型合法；可选字段省略时使用默认值，出现时不接受 `null`。
- 图片只引用随文档交付的相对本地路径，不引用远程 URL 或根路径。
- 模板自身不残留未解析的 `{{...}}` 占位符；用户原文中的同形字符串必须原样保留。
- 目录链接与章节 `id` 一一对应。
- 输出不含盲测、评分、A/B、答案键等模板残留。
- HTML 在无网络环境可读；至少在 320px、768px、1440px 三档验证正文、图片、代码和表格不造成页面级横向溢出，并增加一档超宽屏检查正文内容宽度确实继续增长。
- HTML 目录按钮在鼠标 hover、触屏/鼠标点击和键盘激活下可用；悬浮层计算背景透明度为 0.60、可见文字只有目录；目录链接与章节 `id` 一一对应，Escape 可关闭并将焦点返回按钮。
- PDF 文件头、页数、页面尺寸和中文字形正常；主标题字号与换行自然，每页底部居中页码与总页数正确，侧栏不遮挡正文，关键内容不被异常截断。
- PNG 文件头和像素尺寸与 `--viewport` 一致；大标题换行自然，内容区横向利用充分，文字、表格和图片在画布内完整。单张完整长图必须核对页面 `scrollHeight` 不大于画布高度，不用一张部分截图冒充完整交付。
- 依次运行 [scripts/test_render_document.py](scripts/test_render_document.py) 和 [scripts/test_export_artifacts.py](scripts/test_export_artifacts.py)。
