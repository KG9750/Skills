# 页面与包装规范

## 列表页三件套

### 标题

格式建议：`独特产品名 — 类型 [关键规格]`，例如 `Ming Hearths — Top-Down Interior Tileset [32x32]`。避免全大写、关键词堆叠或未经证明的 “Ultimate”。

### 短描述

一句话写用途、视角和差异点，例如：`Modular 32x32 interiors, animated props and a tested Godot demo for top-down RPGs.` 不重复标题。

### 封面

- 315:250 比例；输出 630×500 或同比例更大；
- 主题、素材类型和关键规格缩小后仍可识别；
- 不用未包含的第三方主角抢占画面；
- 动态 GIF 可提高注意力，但避免闪烁和过快循环。

## 商品页结构

```markdown
# 一句话价值主张

适合谁 + 关键规格 + 最强内容事实。

## What's included
按买家理解的类别和数量列出。

## Technical specifications
格子、画布、原点、方向、帧、FPS、格式、过滤。

## Formats and engine support
通用包、Godot 包、实际测试版本、renderer、导入入口。

## Demo / import quick start
解压、切片/实例化和打开 demo 的最短路径。

## Free vs full contents
明确内容边界。

## License
允许、禁止、署名、AI/NFT/再分发等。

## AI Disclosure / provenance
准确披露生成式 AI 使用、第三方素材来源与许可证，以及实际完成的人工审核/编辑；没有使用时也明确写 `none`。

## Known limitations
方向缺失、无 autotile、demo 外部资产等。

## Version and support/contact
版本、更新、联系渠道。
```

许可证摘要不能取代 ZIP 内完整许可证。营销文案优先具体名词和数字，少用“amazing”“everything you need”等无法验证的形容词。

## 图片叙事

itch 官方基础建议是 3–5 张截图；本 skill 为专业素材包采用 **8–10 张主预览** 的更高标准，封面另计。静态图、动画 GIF 或视频封面各占 1 张预览位。每张只承担一个任务：Hero 场景、内容总览、分类/变体、动画、技术规格、细节近景、实际组合、引擎证明、版本/层级对照或导入工作流。所有图加简短说明，避免同图换色或局部裁切凑数，也避免买家把 demo 外部素材误认为包含内容。

## 定价与上传

- 免费样例应足以验证画风、规格和导入质量；
- 主产品使用项目最低价；
- Source/Bonus 可作为更高付款层级，但先考虑旧买家访问规则；
- 不通过常年 sale 制造虚假原价；
- 文件名包含产品、版本、层级、引擎大版本；
- 直接上传 itch，避免让买家跳转不稳定第三方网盘。

## 页面状态

- `Private`：制作与内部预览；
- `Public Restricted`：可展示但不能购买，适合发布前外部检查；
- `Public`：正式进入发现与购买。

首次 Public 才是发布行为。本地文件完成、浏览器预览通过或 restricted 页面存在都不等于已发布。

## 最终买家视角检查

- 列表页缩略图是否能读；
- 首屏是否在滚动前说清类型、规格和价值；
- 手机宽度是否可读；
- 未登录/隐私窗口能否看到公开视频和图片；
- Download 区每个文件的用途、版本和价格门槛是否清楚；
- 页面数量与 ZIP 实际清单是否一致；
- README 是否在解压根目录；
- 联系方式和版本记录是否可找到。
