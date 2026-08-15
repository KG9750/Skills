# 响应式导航测试示例

这套样例验证 `doc-style-ch` 的三类输出：

- `output/report.html`：响应式长文，左上角目录支持 hover、点击、键盘与章节跳转。
- `output/pdf/responsive-navigation-test.pdf`：A4 打印版，不显示交互目录。
- `output/image/responsive-navigation-summary.png`：单张完整纵向长图，不显示交互目录。

完整交付使用 `source/report.json`。`source/summary.json` 保留为 4:5 精简摘要的可选示例；当前 PNG 按明确要求复用完整报告内容，并根据真实内容高度生成单张长图。

## 已验证

- HTML：320px、768px、1440px 均无页面级横向溢出；宽屏正文随视口增长；60% 深墨悬浮层只显示目录，并支持 hover、点击、Enter、Escape 与章节跳转。
- PDF：A4 纵向、3 页；主标题使用 33pt 单行排版，页脚居中显示“当前页 / 总页数”；目录控件隐藏，代码完整换行，无裁切或孤立尾页。
- PNG：1600×2773；目录控件、复制按钮与滚动条隐藏，四节完整内容位于一张图片内。
- 脚本测试：`test_render_document.py` 30/30，`test_export_artifacts.py` 10/10。

## 重新生成

从 `doc-style-ch` skill 根目录执行：

```bash
python3 scripts/render_document.py examples/responsive-navigation/source/report.json examples/responsive-navigation/output/report.html --profile document
python3 scripts/export_artifacts.py examples/responsive-navigation/output/report.html --pdf examples/responsive-navigation/output/pdf/responsive-navigation-test.pdf
python3 scripts/render_document.py examples/responsive-navigation/source/report.json examples/responsive-navigation/output/image/summary.html --profile image
python3 scripts/export_artifacts.py examples/responsive-navigation/output/image/summary.html --png examples/responsive-navigation/output/image/responsive-navigation-summary.png --viewport 1600x2773
```

若终端沙箱禁止启动浏览器，使用环境已有的浏览器自动化能力执行等价的 PDF 与 PNG 导出。
