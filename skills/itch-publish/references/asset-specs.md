# 素材规格字段

只填写真实存在并已核对的内容。不适用字段写 `N/A`，未知字段写 `待确认`。

## 通用字段

- 产品名、slug、版本、发布日期候选；
- 资产类型、视觉视角、主题、目标游戏类型；
- 文件格式与可编辑源格式；
- 色彩模式、透明度、像素过滤、建议缩放；
- 文件/独立对象/动作/帧/地图数量及统计口径；
- 许可证、署名要求、允许修改/商用、禁止再分发；
- AI Disclosure 和第三方依赖；
- 已测试软件、版本、平台；
- 已知限制与不包含内容。

## 角色与逐帧动画

- 单帧画布宽高与可见像素边界；
- 原点/锚点 `(x,y)`、脚底基线 `y`、中心线；
- 方向名称和 spritesheet 顺序，如 `down,left,right,up`；
- 是否使用镜像方向，若是明确哪些方向共用；
- 动作名、每动作每方向帧数、行列布局；
- FPS 或逐帧毫秒、loop/one-shot、是否有 hold frame；
- 帧事件建议，如攻击命中帧、脚步接触帧；
- 阴影、武器、特效是否分层，是否提供无阴影版本；
- Aseprite tags 的名称、帧区间、播放方向和时长；
- Aseprite slices、九宫格区域、导出层与不导出背景层；
- 文件命名范例与切片参数。

原点优先采用玩法稳定的语义位置，而非透明画布中心：站立角色通常用脚底中心，飞行角色可用身体中心或投影点，特效用爆发中心，投射物用发射/旋转中心。说明坐标系和是否从 0 起算。

## Tileset 与场景素材

- 逻辑 tile 大小与允许越格的视觉尺寸；
- atlas 宽高、margin、spacing、列数；
- terrain/autotile 模式和 tile 变体；
- 地面、墙体、顶部、前景、装饰、阴影的层级顺序；
- 地面接触点、Y-sort 原点和遮挡规则；
- 是否有单体 sprites、整张 atlas、示例地图和 Tiled/Godot 文件；
- Aseprite slices/九宫格、导出层与 atlas 生成规则（如适用）；
- 碰撞覆盖：墙、门、家具、单向平台、水面等；
- 碰撞是示例还是建议默认值；不规则碰撞应简洁，不做逐像素描边。

## UI 与九宫格

- 基准分辨率、像素密度、最小可伸缩区域；
- nine-patch 边距、tile/stretch 模式；
- 状态：normal/hover/pressed/disabled/focus；
- 字体是否包含、授权、字号和 fallback；
- 图标画布、视觉边界、对齐基线与颜色变体。

## VFX

- 画布、原点、blend mode、背景透明度；
- 帧数、FPS、是否循环、结束空帧；
- additive/alpha/premultiplied 预期；
- Godot renderer、材质参数、局部/世界坐标；
- demo 中的灯光、后处理或外部资产依赖。

## 3D

- 单位与比例、up axis、forward axis、pivot；
- 面数/顶点数统计口径、LOD、碰撞；
- FBX/OBJ/glTF/Blend 等格式；
- 材质模型、贴图通道、贴图尺寸与颜色空间；
- 骨骼、rig、动画 clip 名、FPS、root motion；
- 引擎导入版本与 renderer。

## 音频

- WAV/OGG/MP3 格式、sample rate、bit depth/codec；
- 单声道/立体声、响度处理、峰值；
- loop 点、尾音、无缝循环验证；
- 文件数量、时长、BPM/key（音乐适用）；
- 许可证与 Content ID 状态。
