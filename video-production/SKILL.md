# 微短剧视频生成 Skill

将微短剧剧本（`episodes/epNNN.md`）生成为竖屏（9:16）视频，使用 Kling AI 3.0 API。

配套 `short-drama` 剧本创作 skill：先出剧本，再按本 skill 逐集生成视频。

## 触发场景

- "生成第 N 集视频"、"把剧本做成视频"、"用 Kling 生成短剧"
- 已有角色定妆图 + 镜头清单，继续跑剩余镜头

## 工作目录结构

```
项目目录/
├── episodes/epNNN.md          # 剧本（输入）
├── characters.md              # 角色档案（输入）
├── assets/                    # GitHub 图床资源（已上传，英文文件名）
│   ├── characters/            #   角色定妆图
│   ├── scenes/                #   场景合成图
│   ├── character-urls.md      #   角色→URL 对照表
│   └── scene-prompts.md       #   场景图 prompt 清单
├── shots/                     # 镜头清单（每集一个 JSON）
│   └── epNNN.json
├── scripts/                   # 工具脚本
│   ├── kling_gen.py           #   Kling API 视频生成（核心）
│   ├── remove_watermark.py    #   定妆图去水印（纯白背景涂白）
│   ├── remove_watermark_scene.py  # 场景图去水印（深色背景填充）
│   ├── detect_watermark.py    #   检测水印位置
│   └── crop_watermark.py      #   裁剪水印
├── output/                    # 生成视频（按集分目录，gitignore）
│   └── epNNN/
│       └── shotNN.mp4         #   命名：ep{集数}_shot{镜头号}.mp4
└── work/                      # 本地临时（gitignore）
    ├── characters_raw/        #   豆包定妆图原图（带水印）
    ├── characters_clean/      #   去水印定妆图
    ├── scenes_raw/            #   豆包场景图原图（带水印）
    ├── scenes_clean/          #   去水印场景图
    └── discard/               #   废弃版本
```

## 前置条件

1. 剧本：`episodes/epNNN.md`（含分镜/场次/台词）
2. 角色档案：`characters.md`（角色外观描述）
3. Kling API Key（`https://klingai.com/dev/api-key` 创建，配到 `~/.kling_config.json`）
4. 依赖：`pip install requests`（Python 3）

---

## 完整流程（六阶段）

### 阶段一：角色定妆图

**目标：** 每个出场角色一张定妆图（纯白背景、正面全身），用于 `element` 绑定保证人物一致性。

1. 从 `characters.md` 提取角色外观，写定妆图 prompt（豆包/即梦）
   - 规范：**纯白背景 + 正面全身 + 影棚均匀光 + 无文字**
   - 示例：`角色定妆照，35岁男人，胡子拉碴，旧灰T恤油腻围裙，人字拖，正面站立全身照，纯白背景，影棚均匀柔光，高清`
2. 豆包生成 → 保存到 `work/characters_raw/`（中文名可，后续统一改英文）
3. 去水印（豆包水印在右下角）：
   ```bash
   python3 scripts/remove_watermark.py          # 涂白右下角水印
   # 输出 work/characters_clean/
   ```
4. 重命名为英文文件名，复制到 `assets/characters/`
5. 上传 GitHub，更新 `assets/character-urls.md`

### 阶段二：镜头清单设计

**目标：** 把剧本拆成镜头，写成 `shots/epNNN.json`。

- 每个镜头：`id`（`epNNN_shotMM`）、`type`、`duration`（3-15秒）、`prompt`、`element`（绑定角色）、`first_frame`（场景合成图文件名）
- **关键规则：所有镜头都用 `i2v`（图生视频）**，因为 Kling 3.0 的 `t2v` 无法指定竖屏（见「常见坑」）
- 纯场景镜头（全景、群像）也用 `i2v`，`first_frame` 用场景图，`element` 可省略
- 格式详见 `references/shot-format.md`

### 阶段三：场景合成图

**目标：** 每个角色 1 张主场景图（复用），关键镜头单独出图。

1. 按镜头清单归纳需要的场景图（角色+场景，作为 `first_frame` 首帧）
2. 精简原则：同一角色多镜头复用一张主图，特写靠 prompt 推近
3. 写 prompt（建议豆包「图生图」参考定妆图，保证角色一致）→ 存 `assets/scene-prompts.md`
4. 豆包生成 → `work/scenes_raw/` → 去水印 → `work/scenes_clean/` → 复制到 `assets/scenes/`
5. 上传 GitHub

### 阶段四：去水印 + 图床

**豆包水印固定位置：右下角，距右约 38px、距底约 26px 起，约 260×66 像素。**

- 定妆图（纯白背景）→ `remove_watermark.py`（涂白填充）
- 场景图（深色背景）→ `remove_watermark_scene.py`（上方背景行向下填充）
- 上传 GitHub：`assets/` 下英文文件名，`git add/commit/push`，用 `raw.githubusercontent.com` URL

### 阶段五：Kling 生成

```bash
# 1. 配置 API Key（首次）
python3 scripts/kling_gen.py auth

# 2. 预览镜头清单（不扣费）
python3 scripts/kling_gen.py shots shots/epNNN.json --dry-run

# 3. 批量生成（逐条提交+等待+下载，自动命名）
python3 scripts/kling_gen.py shots shots/epNNN.json --wait --download
```

- 单条测试：`python3 scripts/kling_gen.py t2v "..."` / `i2v -i 图URL "..." --wait --download`
- 查询：`python3 scripts/kling_gen.py query <task_id> --download`

### 阶段六：命名归档

脚本按 `ep{集数}_shot{镜头号}.mp4` 自动输出到 `output/epNNN/`，一一对应镜头清单，无需手动改名。

---

## 关键 API 要点

详见 `references/kling-api.md`。速览：

| 项 | 值 |
|---|---|
| Base | `https://api-beijing.klingai.com` |
| 认证 | `Authorization: Bearer <api_key>`（**非** AK/SK JWT） |
| 文生视频 | `POST /text-to-video/{model}` |
| 图生视频 | `POST /image-to-video/{model}` |
| 文生图 | `POST /v1/images/omni-image` |
| 查询 | `GET /tasks?task_ids={id}` |
| 默认模型 | `kling-3.0-turbo` |

## 常见坑（踩坑清单）

1. **`t2v` 无法竖屏**：`aspect_ratio` 参数被忽略，一律生成 16:9。→ 竖屏必须用 `i2v`（图片比例决定视频比例）
2. **认证已变**：Kling 3.0 用 API Key，不是旧版 AK/SK + JWT
3. **i2v 请求体是 `contents` 数组**（不是 `image` 字段）：`[{"type":"first_frame","url":...},{"type":"element","url":...}]`
4. **人物一致性靠 `element`**：把角色定妆图作为 `element` 传入，锁定脸/服装/体型
5. **豆包水印在右下角**，定妆图涂白、场景图填充（不能涂白，深色背景突兀）
6. **图生视频 `image` 字段已废弃**，用 `contents[].url`，且只接受公网 URL（GitHub raw 可用，base64 本地图不行）
7. **`element` 的 url 直接放图片 URL 即可**（无需先创建"元素ID"）

## 工具脚本

| 脚本 | 用途 |
|---|---|
| `kling_gen.py` | Kling API 生成/查询/批量（auth/t2v/i2v/query/shots） |
| `remove_watermark.py` | 定妆图去水印（涂白） |
| `remove_watermark_scene.py` | 场景图去水印（背景填充） |
| `detect_watermark.py` | 检测四角水印位置 |
| `crop_watermark.py` | 裁剪水印区域 |
