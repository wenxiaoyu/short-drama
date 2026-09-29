# 镜头清单 JSON 格式

每集一个 `shots/epNNN.json`，是 `kling_gen.py shots` 命令的输入。

## 完整示例

```json
{
  "episode": "第1集：大佬摆摊，混混找茬",
  "global": {
    "aspect_ratio": "9:16",
    "model": "kling-3.0-turbo",
    "cfg_scale": 0.5,
    "negative_prompt": "低画质, 模糊, 变形, 文字乱码, 多余手指, 畸变"
  },
  "character_urls": {
    "陈无敌": "https://raw.githubusercontent.com/用户名/仓库/main/assets/characters/chen_wudi.png",
    "王姐": "https://raw.githubusercontent.com/用户名/仓库/main/assets/characters/wang_xiulan.png"
  },
  "scene_prefix": "https://raw.githubusercontent.com/用户名/仓库/main/assets/scenes",
  "shots": [
    {
      "id": "ep001_shot01",
      "type": "i2v",
      "note": "场次一·夜市全景",
      "duration": 5,
      "first_frame": "sc_night_market_panorama.png",
      "prompt": "Camera slowly pans across the bustling night market, ..."
    },
    {
      "id": "ep001_shot02",
      "type": "i2v",
      "note": "场次一·刀疤带小弟穿行",
      "duration": 5,
      "element": "刀疤",
      "first_frame": "sc_daoba_walk.png",
      "prompt": "Camera tracks the thug as he walks arrogantly..."
    },
    {
      "id": "ep001_shot03",
      "type": "i2v",
      "note": "场次一·刀疤拍煎饼摊欺压王姐",
      "duration": 6,
      "element": ["刀疤", "王姐"],
      "first_frame": "sc_daoba_wang_stall.png",
      "prompt": "The thug slams his hand down on the pancake stall..."
    }
  ]
}
```

## 字段说明

### 顶层

| 字段 | 说明 |
|---|---|
| `episode` | 集名（备注用） |
| `global` | 全局默认参数（镜头未指定时继承） |
| `character_urls` | 角色名 → 定妆图 URL 映射（`element` 用角色名引用） |
| `scene_prefix` | 场景图 URL 前缀（`first_frame` 文件名自动拼接） |
| `shots` | 镜头数组 |

### 镜头（shot）

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | ✅ | 格式 `epNNN_shotMM`，用于输出命名 `output/epNNN/shotMM.mp4` |
| `type` | ✅ | `i2v`（图生视频）或 `t2v`（文生视频）。**竖屏一律用 `i2v`** |
| `duration` | ✅ | 3-15 秒 |
| `prompt` | ✅ | 动作/运镜描述（英文更稳）。i2v 时不重新描述人物外观 |
| `note` | 否 | 备注（场次说明） |
| `element` | i2v 可选 | 绑定角色名（字符串或数组），对应 `character_urls` 的 key |
| `first_frame` | i2v 必需 | 场景合成图文件名，自动拼 `scene_prefix` |
| `model` | 否 | 覆盖 `global.model` |
| `aspect_ratio` | t2v 用 | 但实测 t2v 比例失效，见常见坑 |

## 命名与输出对应

- 镜头 `id: "ep001_shot05"` → 输出 `output/ep001/shot05.mp4`
- 脚本自动完成命名，无需手动处理

## 设计规则

1. **全部用 `i2v`**：Kling 3.0 的 `t2v` 无法竖屏（aspect_ratio 失效）
2. **element 绑定角色**：保证跨镜头人物一致；纯场景/群像镜头可省略
3. **first_frame 复用**：同一角色多镜头复用一张主场景图，特写靠 prompt 加运镜词（`camera pushes in to a close-up`）推近
4. **duration 按节奏**：建立镜头 5-6s、冲突/动作 5s、特写/反应 4s、悬念 5-6s
5. **element 值用中文角色名**，映射到 `character_urls`；`first_frame` 用英文文件名
