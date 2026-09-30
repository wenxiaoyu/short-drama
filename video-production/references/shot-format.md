# 镜头清单 JSON 格式（完整版）

每集一个 `shots/epNNN.json`，是 `kling_gen.py shots` 命令的输入。

## 完整示例

```json
{
  "episode": "第1集：大佬摆摊，混混找茬",
  "global": {
    "model": "kling-3.0",
    "resolution": "720p",
    "audio": "native"
  },
  "elements": {
    "chen": "322705206027217",
    "daoba": "322706139696158",
    "wang": "322706140320157",
    "heiyiren": "322706112834152"
  },
  "scene_prefix": "https://raw.githubusercontent.com/用户名/仓库/main/assets/scenes",
  "shots": [
    {
      "id": "ep001_shot05",
      "note": "场次二·陈无敌翘二郎腿翻串",
      "duration": 5,
      "first_frame": "sc_chen_wudi_grill.png",
      "element": ["chen"],
      "prompt": "@chen 翘着二郎腿懒散地坐在烧烤摊前翻肉串，抬头说：让让，挡着我烤串了。"
    },
    {
      "id": "ep001_shot03",
      "note": "场次一·刀疤拍煎饼摊欺压王姐",
      "duration": 6,
      "first_frame": "sc_daoba_wang_stall.png",
      "element": ["daoba", "wang"],
      "prompt": "@daoba 一巴掌拍在煎饼摊上，凶狠地对 @wang 说：王秀兰，这个月的卫生费该交了。"
    }
  ]
}
```

## 字段说明

### 顶层

| 字段 | 说明 |
|---|---|
| `episode` | 集名（备注） |
| `global` | 全局默认：`model`、`resolution`、`audio` |
| `elements` | **主体引用映射**：英文短名(ref) → element_id（主体库） |
| `scene_prefix` | 场景图 URL 前缀 |
| `shots` | 镜头数组 |

### 镜头（shot）

| 字段 | 必需 | 说明 |
|---|---|---|
| `id` | ✅ | `epNNN_shotMM`，用于输出 `output/epNNN/shotMM.mp4` |
| `duration` | ✅ | 3-15 秒 |
| `first_frame` | ✅ | 场景合成图文件名（自动拼 scene_prefix） |
| `prompt` | ✅ | 中文动作/对白描述，用 `@ref` 引用主体 |
| `element` | 否 | 绑定主体的 ref 数组（对应 `elements` 映射的 key） |
| `note` | 否 | 备注 |

### prompt 写法（关键）

- **主体引用**：`@ref`（如 `@chen`、`@daoba`），对应 `element` 里绑定的主体
- **对白**：直接写 `说：台词` 或 `[角色, 语气]: "台词"`
- **多主体**：`element: ["daoba","wang"]`，prompt 里 `@daoba ... @wang ...`
- 脚本自动加前缀 `镜头1, {duration}, `

## 完整流程依赖

1. **主体先建**：`elements` 里的 element_id 来自「创建主体」接口（见 kling-api.md）
2. **场景图先备**：`first_frame` 文件名要已上传到 scene_prefix 下
3. **比例**：first_frame 是 9:16 图 → 视频 9:16 竖屏

## 命名与输出对应

镜头 `id: "ep001_shot05"` → 输出 `output/ep001/shot05.mp4`（脚本自动完成）
