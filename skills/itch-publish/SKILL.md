---
name: itch-publish
description: 将已经完成或接近完成的游戏美术、像素素材、角色动画、Tileset、UI、VFX、音频或 3D 素材包，整理成专业、可信且有购买吸引力的 itch.io 待发布商品。用于素材盘点、规格补全、帧序列与原点说明、许可证和版本整理、通用包与免费样例/完整版分层、Godot 专用包及演示场景决策、ZIP 构建与解压验证、封面/截图/GIF/预告片规划、itch 商品页文案和元数据、Private/Public Restricted 发布前检查；也用于审查现有 itch 素材商品是否缺少买家所需信息。默认只做到本地 release candidate 和可复制的页面草稿，不登录、上传、定价生效或公开发布，除非用户另行明确授权。
---

# Itch Publish

把“素材文件”转化为买家可理解、可评估、可导入的商品。先证明交付物真实可用，再制作营销表达；不要让漂亮页面掩盖缺失的规格、文档或演示。

## 开始前

1. 读取目标项目的 `AGENTS.md`、现有 README、许可证、构建脚本和版本记录。
2. 检查工作树；保留用户的未提交修改，只改本任务直接需要的文件。
3. 明确输入目录、当前版本、素材类型、目标买家、授权来源、是否免费/付费以及当前发布状态。无法确认的事实标为 `待确认`，不要猜。
4. 对输入目录运行：

```bash
python3 <skill-dir>/scripts/audit_asset_pack.py <asset-root> --markdown
```

5. 若要落盘审计结果，追加 `--output <path>`；此时完整报告只写入指定文件，stdout 保持为空。默认拒绝覆盖已有报告，确认覆盖时再加 `--force`。脚本不覆盖输入，也不把报告写入正在审计的目录。

## 成功标准

任务完成时应同时具备：

- 有保存的构建命令/最小构建脚本和排除规则，可重复生成并通过解压检查的上传 ZIP；
- 买家能在 30 秒内理解内容、风格、规格、格式、引擎支持和许可证的商品页草稿；
- 对尺寸、格子、原点/基线、方向、帧顺序、FPS、循环、透明度、过滤方式和层级规则的明确说明；
- 能证明页面宣传画面来自实际交付物；
- Godot 声明与真实包内容、测试版本和演示场景一致；
- `release-checklist.md` 清楚区分已验证、待用户确认和未执行；
- 当前状态准确写成 `local candidate`、itch `Private`、`Public Restricted` 或 `Public`，绝不把本地 QA 写成已发布。

## 工作流

### 1. 盘点并分类

建立真实清单：源文件、导出文件、动画、瓦片、地图、字体、音频、第三方依赖、预览素材、文档、引擎工程和缓存。统计数量时说明口径，例如“独立角色数”与“PNG 文件数”不能混写。

按交付层分组：

- `Core/Universal`：PNG、SVG、WAV/OGG、FBX/GLTF、Aseprite/PSD 等通用素材；
- `Engine Integration`：Godot/Unity/Unreal/RPG Maker 等真实可导入工程；
- `Source/Editable`：有权再分发的源文件；
- `Demo/Sample`：免费样例、演示场景或示例地图；
- `Marketing`：只用于商品页，不混入买家主包。

不要擅自删除用户源素材。正式 ZIP 不得包含 `.godot/`、导入缓存、临时文件、系统垃圾、测试日志或无关历史版本；通过新建 staging 目录排除它们。只有任务产生了确认无用的临时/孤儿文件时才删除。

### 2. 冻结产品规格

复制并填写 `assets/release-candidate/PRODUCT-SPEC.template.md`。详细字段见 [asset-specs.md](references/asset-specs.md)。至少确认：

- 逻辑格子/单位尺寸与实际画布尺寸；
- 透明背景、色彩空间和像素过滤；
- 原点或锚点坐标、脚底/地面基线、可见边界；
- 角色方向数和明确顺序，不用“全方向”代替列表；
- 每个动作的帧数、spritesheet 行列顺序、FPS/每帧时长、是否循环；
- Tileset 的 atlas 间距、margin、terrain/autotile 规则、遮挡层与可行走层；
- 碰撞是否包含、包含在哪个包、用于哪些对象；
- 支持的格式、软件/引擎版本、渲染器及已测试范围。

规格必须描述已有素材。发现不一致时先修复或在限制中准确披露，不为凑齐表格虚构兼容性。

### 3. 决定是否制作 Godot 专用包

读取 [godot-delivery.md](references/godot-delivery.md)，然后作出明确结论：`制作`、`不制作` 或 `后续版本`。

优先制作 Godot 包的条件：

- 商品主张“Godot-ready”或主要买家使用 Godot；
- TileSet、SpriteFrames、材质/VFX、碰撞、多层场景或导入设置能显著节省买家时间；
- 能维护一个明确 Godot 版本，并能实际导入和运行验证。

通常不必制作的条件：

- 只是少量独立 PNG/音频，导入没有实质配置价值；
- 无法提供或测试演示工程；
- 引擎绑定会让通用包更混乱。

若制作，Godot 包至少包括 `project.godot`、可打开的入口场景、真实素材资源、一个展示核心用途的 demo、版本/渲染器说明和现有项目集成步骤。碰撞以玩法无关的基础边界为主；小装饰默认不阻挡，并在文档中说明。不要把单纯复制 PNG 的目录标成“Godot 专用包”。

### 4. 设计上传包层级

根据产品选择最少且清晰的上传项：

- `Product-vX.Y-Core.zip`：通用主包；
- `Product-vX.Y-Godot-4.x.zip`：经过真实测试时才提供；
- `Product-vX.Y-Free-Sample.zip`：能独立体验质量的小样，不是残缺随机文件；
- `Product-vX.Y-Source.zip`：仅当许可与定价允许；
- 可选 `Product-vX.Y-Demo.zip`，但若 demo 已在 Godot 包内不要重复。

避免同时保留多个未标注的旧版付费 ZIP。若保留旧版，明确写 `Legacy` 和用途。不要用逐文件最低价拆主产品；主体产品使用项目最低价，单文件最低价用于真正的额外内容，并在调整前检查旧买家的访问影响。

每个买家 ZIP 根目录应直接看到 README、LICENSE、CHANGELOG（如有历史）和内容目录，不要嵌套三层同名文件夹。

### 5. 制作演示与预览证据

为每个 itch 商品页（覆盖 Core、Sample、Source、Godot 等全部层级包）规划 **8–10 张主预览**。这里的“张”按独立预览位计数：静态图、动画 GIF 或视频封面各占 1 张；封面单独计算，不占 8–10 张主预览名额。

先单独制作封面：一眼识别主题和资产类型，文字在缩略图仍可读。然后按“吸引—证明—消除疑虑”制作以下 8 个无条件主预览角色：

1. Hero 场景：用实际资产组成接近成品游戏的画面；
2. 内容总览：展示总体规模与统计口径，不靠夸张数字；
3. 分类/变体矩阵：拆分主要类别、角色、道具、材质或状态；
4. 动画/状态演示：用真实 FPS 展示方向、循环或交互状态；静态包则展示关键状态/角度/尺寸对照；
5. 技术规格卡：格子、画布、原点、方向、帧数、格式；
6. 细节/变体近景：证明像素、材质、角色或道具的一致性；
7. 实际组合示例：展示模块如何形成完整房间、场景、角色阵容或效果组合；
8. 工作流/边界图：展示图层、切片、导入步骤、许可证摘要或不包含内容。

再按实际产品从以下条件角色增加 0–2 张，使总数达到 8–10：

- 引擎 demo：只有宣传 Godot-ready 或其他引擎专用支持时，展示编辑器/运行场景和关键资源；
- 免费版与完整版对照：只有存在免费/付费或 Standard/Source 分层时，明确内容边界；
- 第二个独立 use case、类别拆分或技术示例：仅当提供新信息时使用。

8–10 张是本 skill 对独立专业商品页的固定标准，不设“小包少图”例外。若素材规模小到无法诚实完成八个必选角色，不要用裁切、换色或重复画面凑数：应把它与相关素材合并成更完整的商品、补足真实可展示的规格/示例/工作流价值，或保留为免费附加内容而不单独发布。多个独立商品页分别满足本标准；同一商品页内的 Core/Sample/Godot 等下载层级共用一套预览，不重复计算。

官方要求封面采用 315:250 比例，315×250 为最低，优先输出 630×500 或同比例更大图；官方基础建议是 3–5 张截图且尺寸不限。本 skill 对专业素材商品采用更高标准：准备 8–10 张互不重复、各自承担明确任务的主预览，不把同一画面换色、局部裁切或微小变化凑数。营销预览建议统一画幅，像素素材使用整数倍缩放和最近邻插值。

页面图只展示交付物实际能复现的内容。外部模型、字体或背景仅用于演示时必须明确标注“不包含”。

### 6. 写商品页与买家文档

复制并填写 `assets/release-candidate/ITCH-PAGE.template.md`、`README.template.md`、`metadata.template.md`、`preview-plan.template.md`、`upload-manifest.template.md` 和 `release-checklist.template.md`。构建时填写 `build-evidence.template.md`，并随步骤 7 的每项验证持续更新 `release-checklist.md`。页面写作与元数据规则见 [page-and-packaging.md](references/page-and-packaging.md)。

商品页首屏必须包含：一句价值主张、适用视角/类型、核心规格、最强内容事实和明确 CTA。随后按顺序写：

- What’s included；
- Technical specifications；
- Formats and engine support；
- Demo / import quick start；
- Free vs full contents；
- License；
- AI Disclosure / provenance；
- Known limitations；
- Version and support/contact。

标题和短描述服务于列表页：标题带素材类型与关键规格；短描述讲用途与差异点，不堆关键词。图形素材项目的类型选择 Graphical Assets，不要因为 PNG 可在 Windows 打开就标 Windows 可执行。

每次配置或修改 itch.io 标签时，强制执行以下规则：

1. 最终标签必须恰好为 10 个，不少于 10 个，也不保留第 11 个；
2. 只选择 itch.io 标签控件下拉列表中实际存在的标签；必须点击对应的平台候选项，不用回车把输入文字创建为自定义标签；
3. 十个标签都必须准确描述交付物、素材类型、视觉风格或真实用途，不为凑数添加不相干标签；
4. 只有存在真实引擎包、配置价值和相应证据时，才选择 `Godot`、`Ren'Py`、`Unity` 等引擎标签；
5. AI 相关标签必须与商品的实际 AI Disclosure 一致，禁止给 AI-assisted 商品选择 `no-ai`；
6. 若预定词不在平台候选中，改选一个事实准确的现有候选，不能退回自定义标签；
7. 保存商品页后重新加载，回读并记录恰好 10 个平台标签；没有完成回读时，只能写“标签待验证”，不能写“标签已保存”。

只制作本地候选、尚未操作 itch.io 时，也要在 `metadata.md` 中准备恰好 10 个标签，并明确标记它们需要在实际页面下拉候选中逐项验证。

### 7. 构建并验证真实候选包

构建到项目的 `dist/` 或用户指定目录，不覆盖唯一源文件。完成以下验证：

1. 对每个 ZIP 运行 `unzip -t`；
2. 解压到新的临时目录，从买家视角检查根目录和文档；
3. 对每个上传 ZIP 和对应的新解压目录分别重跑 `audit_asset_pack.py` 做结构盘点：ZIP 模式核对 CRC 与条目级读取错误，目录模式核对真实解压树；两者都盘点扩展名、PNG 画布尺寸、文档、Godot 文件，以及缓存、版本控制/编辑器目录、符号链接和临时条目；它不验证命名规律、alpha、方向矩阵、Aseprite tags、帧顺序或 FPS；
4. 独立检查代表性 PNG/源文件，并把命名规律、alpha、方向/动作矩阵、Aseprite tags、帧顺序和 FPS 记录到 evidence；不要用审计脚本退出码代替素材 QA；
5. 对 Godot 包在声明版本执行全新导入、入口场景和 demo；需要证明视觉效果时使用真实 GUI 窗口，不用 headless 代替；
6. 核对商品页的所有数量、版本、文件名、价格层级、“包含/不包含”，以及是否已从 itch.io 平台候选中保存并回读恰好 10 个准确标签；
7. 核对 `page/previews/` 中封面和 8–10 张主预览均存在、可打开、源自实际交付物，并与 `itch-page.md`、`metadata.md` 和 `preview-plan.md` 的引用/说明一致；
8. 在 evidence 中保存构建命令或最小构建脚本、staging 布局和排除规则；把命令、结果、未执行项写入 `release-checklist.md`。

没有实际运行的引擎不要写“兼容”；可写“通用 PNG，可按说明导入，未提供专用工程”。没有真人买家测试时不要写“buyer-tested”。

### 8. 形成待发布交付

推荐输出：

```text
dist/itch-release-candidate/
├── uploads/                 # 将来上传 itch 的最终 ZIP
├── product-spec.md          # 已冻结的产品规格
├── page/
│   ├── itch-page.md         # 可复制到编辑器的商品页
│   ├── metadata.md          # 分类、标签、价格建议、AI disclosure
│   ├── upload-manifest.md   # 每个上传文件及最低价/免费样例标记
│   ├── preview-plan.md      # 封面、截图、GIF、视频清单
│   └── previews/            # 最终封面与 8–10 张主预览成品
├── evidence/                # 构建/解压/引擎验证与 build-evidence.md
└── release-checklist.md
```

最终汇报说明：生成了什么、真实验证通过什么、Godot 决策、仍需用户确认什么，以及当前仍未上传/未公开。除非用户明确要求并授权网页操作，否则停在本地候选状态。

## 发布闸门

以下条件有任一未满足时，不建议转为 Public：

- 权利或许可证未确认；
- 页面预览与下载包不一致；
- 主 ZIP 未通过新目录解压检查；
- 标注 Godot-ready 却没有在声明版本完成实际导入与 demo；
- 缺少封面；
- 缺少 8–10 张有效且不重复的主预览；
- 缺少核心规格；
- AI 辅助素材未按 itch 的 AI Disclosure 准确披露；
- 标签不是恰好 10 个、含自定义或不相关标签，或尚未在保存后重新加载回读；
- 免费/付费内容、价格或旧版访问规则不清楚。

可先创建 Private 或 Public Restricted 页面供人工检查。公开页面可能进入 itch 的发现/最新内容入口，因此应在执行时重新核对当前规则，并只在页面和文件准备完成后转为 Public。

## 资源导航

- 研究依据与页面样本：[research.md](references/research.md)
- 2D/动画/Tileset/3D/音频规格：[asset-specs.md](references/asset-specs.md)
- Godot 包与 demo 标准：[godot-delivery.md](references/godot-delivery.md)
- itch 页面、图片、定价和 ZIP 结构：[page-and-packaging.md](references/page-and-packaging.md)
- 只读盘点脚本：`scripts/audit_asset_pack.py`
- 脚本回归测试：`python3 -B -m unittest discover -s <skill-dir>/tests -v`（`-B` 避免把 `__pycache__` 写入 skill）
- 可复制模板：`assets/release-candidate/`
