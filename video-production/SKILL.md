# 微短剧视频生成 Skill

将微短剧剧本（`episodes/epNNN.md`）生成为**竖屏 9:16 + 原生对白**的视频，使用 Kling AI 3.0 **完整版**（`kling-3.0`）。

配套 `short-drama` 剧本创作 skill：先出剧本，再按本 skill 逐集生成视频。

## 触发场景

- "生成第 N 集视频"、"把剧本做成视频"、"用 Kling 生成短剧"
- 已有角色定妆图 + 主体库 + 镜头清单，继续跑剩余镜头

## 核心结论（实测校准）

| 能力 | 方案 |
|---|---|
| 竖屏 9:16 | 完整版 `kling-3.0`，由首帧图比例决定 |
| 原生对白 | `settings.audio: "native"` + prompt 写台词 |
| 人物一致性 | 主体库 `element_id` + prompt `@主体` 引用 |
| 环境音 | 默认就有（叹气、嘈杂背景） |

## 工作目录结构

```
项目目录/
├── episodes/epNNN.md          # 剧本（输入）
├── characters.md              # 角色档案（输入）
├── assets/                    # GitHub 图床资源（英文文件名）
│   ├── characters/            #   角色定妆图
│   ├── scenes/                #   场景合成图
│   ├── character-urls.md      #   角色→URL 对照表
│   └── scene-prompts.md       #   场景图 prompt 清单
├── shots/                     # 镜头清单（每集一个 JSON）
│   └── epNNN.json
├── scripts/                   # 工具脚本
│   ├── kling_gen.py           #   Kling API（auth/element/i2v/shots/query）
│   ├── remove_watermark.py    #   定妆图去水印（涂白）
│   ├── remove_watermark_scene.py  # 场景图去水印（背景填充）
│   ├── detect_watermark.py    #   检测水印
│   └── crop_watermark.py      #   裁剪水印
├── output/                    # 生成视频（gitignore）
│   └── epNNN/shotMM.mp4       #   ep{集数}_shot{镜头号}.mp4
└── work/                      # 本地临时（gitignore）
    ├── characters_raw/ characters_clean/
    ├── scenes_raw/ scenes_clean/
    └── discard/
```

## 前置条件

1. 剧本 + 角色档案
2. Kling API Key（`https://klingai.com/dev/api-key`），配到 `~/.kling_config.json`
3. `pip install requests`；`brew install ffmpeg`（后期拼接/音量用）

---

## 完整流程（七阶段）

### 阶段一：角色定妆图

每个出场角色一张定妆图（纯白背景、正面全身），用于主体库。

- 规范：**纯白背景 + 正面全身 + 影棚均匀光 + 无文字**
- 豆包生成 → `work/characters_raw/` → 去水印（`remove_watermark.py` 涂白）→ 英文名 → `assets/characters/` → GitHub
- **主体库需要 1 正面 + 1~3 其他角度图**；先用同图跑通，后续补侧面/四分之三侧优化

### 阶段二：场景合成图

每个角色 1 张主场景图（复用），关键镜头单独出图，作为 `first_frame` 首帧。

- 精简原则：同一角色多镜头复用一张主图，特写靠 prompt 推近
- 豆包「图生图」参考定妆图 → `work/scenes_raw/` → 去水印（`remove_watermark_scene.py` 背景填充）→ `assets/scenes/` → GitHub
- prompt 存 `assets/scene-prompts.md`

### 阶段三：去水印 + 图床

豆包水印固定位置：**右下角，距右约 38px、距底约 26px 起，约 260×66 像素**。

- 定妆图（白底）→ `remove_watermark.py`（涂白）
- 场景图（深色）→ `remove_watermark_scene.py`（上方背景行向下填充，不能涂白）
- 上传 GitHub，用 `raw.githubusercontent.com` URL

### 阶段四：创建主体（主体库）

**人物一致性的核心**，每个角色创建一次，得到 `element_id`。

```bash
python3 scripts/kling_gen.py element create \
  --name 陈无敌 --desc "35岁男人，胡子拉碴，旧灰T恤油腻围裙，人字拖" \
  --frontal <定妆图URL> --wait
# 输出 element_id，记下来
```

- 所有角色创建后，把 `element_id` 写进 `shots/epNNN.json` 的 `elements` 映射
- 详见 `references/kling-api.md`

### 阶段五：镜头清单设计

写 `shots/epNNN.json`：每个镜头含 `duration`、`first_frame`、`element`（ref 数组）、`prompt`（@ref + 台词）。

- 全部用 `i2v`（完整版）
- `prompt` 里 `@ref` 引用主体 + `说：台词`
- 格式详见 `references/shot-format.md`

### 阶段六：Kling 生成

```bash
python3 scripts/kling_gen.py shots shots/epNNN.json --dry-run   # 预览
python3 scripts/kling_gen.py shots shots/epNNN.json --wait --download
```

- 输出自动落到 `output/epNNN/shotMM.mp4`
- 单条测试：`python3 scripts/kling_gen.py i2v -i <场景图url> --element-ref chen:322705206027217 "prompt"`

### 阶段七：后期（音量 + 拼接）

1. **提升音量**：Kling 对白偏轻（mean -23~-34dB），需 +14dB 左右
2. **拼接**：`ffmpeg` concat 或剪映，按 shot 顺序合并
3. **BGM/音效**：可选，剪映或 ffmpeg 叠加

---

## 关键 API 要点

详见 `references/kling-api.md`。速览：

| 项 | 值 |
|---|---|
| 模型 | `kling-3.0`（完整版） |
| 认证 | `Authorization: Bearer <api_key>` |
| 图生视频 | `POST /image-to-video/kling-3.0` |
| 创建主体 | `POST /v1/general/advanced-custom-elements` |
| 查询主体 | `GET /v1/general/advanced-custom-elements/{task_id}` |
| 查询视频 | `GET /tasks?task_ids={id}` |
| 音频 | `settings.audio: "native"` |

## 常见坑（踩坑清单）

1. **必须用 `kling-3.0` 完整版**，`kling-3.0-turbo` 的 `generate_audio` 不生成对白
2. **`element` 用 `element_id`，不是 `url`**（完整版报 `Invalid element id`）
3. **prompt 在 `contents` 里**（`{"type":"prompt","text":...}`），不是顶层字段
4. **音频参数在 `settings.audio`**，不是 `generate_audio`
5. **`t2v` 无法竖屏**（aspect_ratio 失效），竖屏必须 `i2v`
6. **创建主体是异步的**（返回 task_id，需轮询拿 element_id），`refer_images` 必须 1~3 张
7. **竖屏有 rotation 元数据**：`ffprobe` 显示 716×1280，`mdls` 可能显示 1280×716，播放时自动旋转，别误判横向
8. **对白音量偏轻**，后期 +14dB
9. **环境音默认就有**（叹气、嘈杂声），对白台词才需要 `audio:native`

## 工具脚本

| 脚本 | 用途 |
|---|---|
| `kling_gen.py` | Kling API：`auth`/`element`(create/query/list)/`i2v`/`shots`/`query` |
| `remove_watermark.py` | 定妆图去水印（涂白） |
| `remove_watermark_scene.py` | 场景图去水印（背景填充） |
| `detect_watermark.py` | 检测四角水印位置 |
| `crop_watermark.py` | 裁剪水印区域 |
