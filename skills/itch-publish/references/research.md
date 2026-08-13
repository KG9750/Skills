# itch.io 素材包研究依据

研究日期：2026-08-12。未来执行时，应重新核对易变的 itch 表单、政策和目标商品页。

## 官方规则

- [Getting started](https://itch.io/docs/creators/getting-started)：封面比例为 315:250，315×250 是最低尺寸，推荐 630×500 或同比例更大；截图建议 3–5 张；最多 10 个标签；页面初建默认为 Private，可用 Public Restricted；商品必须至少有一个 upload 才能购买。
- [Designing your page](https://itch.io/docs/creators/design)：可用单栏/双栏、主题颜色、header、背景、字体与视频；描述应包含功能、联系、状态、规格等；视频会出现在截图栏之上；需要检查移动端和未登录访问。
- [Pricing](https://itch.io/docs/creators/pricing)：价格是最低价，买家可以多付；项目最低价适合主体产品，逐文件最低价适合额外内容；提高逐文件最低价可能让旧买家失去访问资格。
- [Quality guidelines](https://itch.io/docs/creators/quality-guidelines)：首次公开前应完成图片、文件和分类；封面与截图影响发现；素材应选择正确内容类型而不是系统平台；标签必须相关；不可用页面或图片误导内容；素材页面必须准确填写 AI Disclosure；优先把文件直接上传 itch。

## 样本与可复用规律

### Modern Interiors — LimeZu

[商品页](https://limezu.itch.io/moderninteriors)

有效做法：首屏强调使用场景与规模；列出主题、动画、UI、角色生成器、独立 PNG；提供 16×16/32×32/48×48、免费版/完整版/RPG Maker/工具分层；许可证和更新日志可见。

评论暴露的摩擦：阴影与无阴影版本不够显眼、Unity 切片、Godot 墙体/terrain 用法、RPG Maker 目录、动画用法、样例地图和 metadata 说明不足。结论：海量内容不能替代导入说明和示例地图。

### Tiny Swords — Pixel Frog

[商品页](https://pixelfrog-assets.itch.io/tiny-swords)

有效做法：免费与付费区域视觉区分；角色、建筑、地形、UI、特效逐类说明；公开 tilemap guide；明确 PNG/Aseprite、64×64 grid、10 FPS/100ms、商业许可和下载层级。

结论：帧速、格子与实际 guide 是降低买家试错成本的高价值信息。

### Tiny RPG Character Asset Pack — Zerie

[商品页](https://zerie.itch.io/tiny-rpg-character-asset-pack)

有效做法：22 个角色、动作列表、100×100 切片单元、逐角色 GIF、免费样例与完整版、版本日志、明确 Allowed/Not Allowed。

评论暴露的摩擦：方向数、示例 GIF FPS、阴影/无阴影、轮廓版本、动作帧清单仍被频繁询问。结论：角色包必须写方向、帧序、FPS、原点和变体矩阵，不能只写“animated”。

### Stylized Nature MegaKit — Quaternius

[商品页](https://quaternius.itch.io/stylized-nature-megakit)

有效做法：准确的模型分类数量；FBX/OBJ/glTF 通用格式；Standard/Pro/Source 定价层级；Godot/Unity/Unreal 源工程；明确测试版本与 CC0。

结论：通用格式和引擎工程可以并存，但引擎版本必须显式。

### Godot 3D Pixelart Starter Kit — OrdinaryCicada

[商品页](https://oddpotatodev.itch.io/godot-3d-pixelart-starter-kit)

有效做法：具体列出 shader、相机、upscaler 和 demo scene；明确“包含/不包含”和计划更新。

评论暴露的摩擦：许可证缺失、文档不足、视频展示与交付范围疑似不一致、外部模型接入流程不清。结论：Godot 工程的价值是可迁移工作流，不只是一个漂亮 demo。

### Godot Effects Collection — Binbun

[商品页](https://binbun3d.itch.io/effects-collection-vol1)

有效做法：按效果类别列清单、明确 CC0、持续 devlog、部分场景内文档。

评论暴露的摩擦：整体文档位置、demo 文件、Forward+/Mobile/Compatibility 差异。结论：Godot VFX 必须写版本、renderer、平台限制、demo 与文档入口。

## 综合判断

高转化页面不是单纯“图多”，而是连续回答五个问题：

1. 这个风格适合我的游戏吗？
2. 我具体会得到什么？
3. 尺寸、方向、帧和格式能接入我的管线吗？
4. 有 demo、guide 或免费样例证明它好用吗？
5. 许可证、引擎版本和限制会不会在购买后制造风险？

专业候选包应让页面陈述、上传 ZIP、README、引擎 demo 和许可证互相印证。
