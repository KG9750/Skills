# Godot 专用交付

## 最小有效价值

Godot 包必须比“PNG 放进文件夹”多提供至少一项真实价值：预建 `TileSet`、`SpriteFrames`、AnimationPlayer、碰撞、Y-sort/layer 设置、材质/shader、导入预设或可运行 demo。

## 推荐结构

```text
Product-Godot-4.x/
├── project.godot
├── README.md
├── LICENSE.txt
├── demo/
│   ├── Demo.tscn
│   └── demo.gd              # 仅在交互确有必要时
├── assets/                  # 原始可复用资产
├── resources/               # .tres/.res、TileSet、SpriteFrames、材质
└── scenes/                  # 可实例化场景
```

不要包含 `.godot/`、`.ctex`、导入缓存、编辑器设置或本机绝对路径。

## 2D 像素素材默认设置

- 使用 nearest filtering；
- 关闭会破坏像素边缘的 mipmap（除非用途需要并已说明）；
- 角色默认脚底中心原点，地面 props 使用接地点；
- SpriteFrames 名称与 README 动作表一致；
- 以真实 FPS 配置 speed，不凭 GIF 播放速度猜；
- demo 同时展示静态清单、动画、Y-sort/遮挡和碰撞边界；
- 为已有项目写清复制到 `res://` 的准确目录，不要求买家把整个示例工程嵌套进去。

## 碰撞策略

- 环境墙体、不可穿越大型家具、门框、平台可提供基础碰撞；
- 小装饰、地毯、桌面摆件默认不阻挡；
- 可开关门、动态角色等不要用静态碰撞冒充完整玩法；
- 同时保留无引擎绑定的 Core 包；
- 文档说明碰撞是“示例默认”还是“正式推荐”。

## Demo 场景

一个好 demo 应在几十秒内回答：有哪些资产、动画如何播放、排序/碰撞如何工作、买家如何复用。不要加入与素材无关的完整游戏框架。

推荐：

- 明确入口 `demo/Demo.tscn`；
- 屏幕上或 README 中列控制；
- 允许切换动画/方向或浏览分类；
- 用可见区域展示 collision debug 的方法；
- 标注 demo 中不随包交付的第三方素材；
- 保持脚本少且易读。

## 兼容声明

写 `Tested with Godot X.Y.Z, renderer Forward+/Mobile/Compatibility`。只验证导入可写“import tested”；只有入口场景真实运行后才写“demo tested”。Headless 适合导入和资源回归，但宣传视觉效果、GUI 操作或编辑器体验需要真实可见窗口验证。

Godot 4.x 小版本并非当然兼容。若只测一个版本，就只声明该版本；可补充“其他 4.x 版本可能可用但未测试”。
