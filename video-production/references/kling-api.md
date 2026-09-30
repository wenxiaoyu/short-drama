# Kling AI 3.0 API 要点（完整版）

> 本文档记录实测确认的 Kling AI 3.0 **完整版** API 细节（2026-09 实测）。
> 模型用 `kling-3.0`（非 `kling-3.0-turbo`），完整版才支持原生对白 + 主体库。

## 认证

- 方式：`Authorization: Bearer <api_key>`
- API Key 创建：`https://klingai.com/dev/api-key`
- **注意**：Kling 3.0 已弃用旧版 AK/SK + JWT（用 JWT 报 `code:1002`）

## 端点总览

| 功能 | 端点 | 说明 |
|---|---|---|
| 图生视频（短剧主力） | `POST /image-to-video/kling-3.0` | 竖屏 + 对白 + 主体绑定 |
| 文生视频 | `POST /text-to-video/{model}` | 横向 16:9，aspect_ratio 失效 |
| 创建主体 | `POST /v1/general/advanced-custom-elements` | 异步，返回 task_id |
| 查询主体 | `GET /v1/general/advanced-custom-elements/{task_id}` | 拿 element_id |
| 主体列表 | `GET /v1/general/advanced-custom-elements?pageNum=1&pageSize=30` | |
| 删除主体 | `POST /v1/general/delete-advanced-elements` | body: element_id |
| 查询视频任务 | `GET /tasks?task_ids={id}` | 返回数组 |

## 主体库（人物一致性核心）

### 创建主体

`POST /v1/general/advanced-custom-elements`，请求体：
```json
{
  "element_name": "陈无敌",
  "element_description": "35岁男人，胡子拉碴，旧灰T恤油腻围裙，人字拖",
  "reference_type": "image_refer",
  "element_image_list": {
    "frontal_image": "正面图URL",
    "refer_images": [{"image_url": "其他角度图URL"}]
  },
  "tag_list": [{"tag_id": "o_102"}]
}
```

- `element_name` ≤20字符，`element_description` ≤100字符
- `reference_type`: `image_refer`（多图）或 `video_refer`（视频，仅限 o3 及之后模型）
- `element_image_list.refer_images`：**必须 1~3 张**（不能为空），需与正面图有差异（不同角度/特写）
- 返回 `data.task_id`（**异步任务**）

### 查询主体（拿 element_id）

`GET /v1/general/advanced-custom-elements/{task_id}`，轮询直到 `task_status=succeed`：
```json
{"data": {"task_status": "succeed", "task_result": {"elements": [{"element_id": 322705206027217, ...}]}}}
```

- 关键字段：`data.task_result.elements[0].element_id`
- 创建主体处理时间较长（约 1-2 分钟）

## 图生视频（完整版，短剧主力）

请求体：
```json
{
  "contents": [
    {"type": "prompt", "text": "镜头1, 5, @chen 抬头懒洋洋地说：关我屁事。"},
    {"type": "first_frame", "url": "场景合成图URL"},
    {"type": "element", "element_id": "322705206027217", "id": "chen"}
  ],
  "settings": {
    "multi_shot": true,
    "audio": "native",
    "resolution": "720p",
    "duration": 5
  },
  "options": {"watermark_info": {"enabled": false}}
}
```

### contents 数组

| type | 说明 |
|---|---|
| `prompt` | 提示词，字段 `text`（不是顶层的 prompt 字段！） |
| `first_frame` | 首帧图，字段 `url` |
| `last_frame` | 尾帧图，字段 `url`（可选） |
| `element` | 主体绑定，字段 `element_id`（主体ID）+ `id`（素材索引，用于 @ 引用） |

- **element 不接受 `url`**，必须用 `element_id`（报错 `Invalid element id`）
- `id` 是 @xxx 里的 xxx，同一任务内不重复
- 最多 3 个主体

### settings

| 字段 | 说明 |
|---|---|
| `multi_shot` | 是否多镜头（默认 true） |
| `audio` | **`native`（含对白+唇形同步）或 `off`（无声）** |
| `resolution` | `720p`/`1080p`/`4k` |
| `duration` | 3-15 秒 |

### 竖屏

- **由 `first_frame` 图片比例决定**（9:16 图 → 9:16 视频）
- 生成的视频有 rotation 元数据，`ffprobe` 显示 `width=716,height=1280`，但 `mdls` 可能显示原始像素序（1280×716），播放时自动旋转为竖屏——**不是横向，别误判**

### 多镜头 + 对白

- 多镜头格式：`镜头1, 5, words; 镜头2, 5, words;`（半角分号分隔，n=序号，m=时长，words=提示词）
- 单镜头也写成 `镜头1, {duration}, words`
- **主体引用**：`@主体id`（对应 element 的 id 字段），如 `@chen`
- **对白**：直接在 words 里写 `说：台词` 或 `[角色, 语气]: "台词"`，配合 `audio:"native"` 生成对白+唇形同步

## 对白实测结论

| 声音层次 | 内容 | 生成方式 |
|---|---|---|
| 环境音 | 叹气、嘈杂背景声 | **默认就有**（无需参数） |
| 对白台词 | 人说话 + 唇形同步 | 仅完整版 `audio:"native"` + prompt 写台词 |

- `kling-3.0-turbo` 的 `generate_audio` **不生效**（只出环境音，无台词）
- **对白音量偏轻**：mean 约 -23~-34 dB，后期需 `+14dB` 左右提升

## 提交/查询响应

提交返回：`{"code":0,"data":{"id":"任务ID","status":"submitted"}}`

查询返回：
```json
{"code":0, "data":[{"id":"...","status":"succeeded","outputs":[{"type":"video","url":"...","duration":"5.04"}],"billing":[{"amount":"4.5","package_type":"video"}]}]}
```

- `data` 是数组，取 `data[0]`；结果在 `outputs[].url`

## 错误码

| code | 含义 |
|---|---|
| 1002 | 认证错误（用了 AK/SK 而非 API Key） |
| 1102 | 账户余额不足 |
| 1201 | 参数错误（如 `Invalid element id`、`refer images must be between 1 and 3`） |

## 计费参考

- 完整版 720p：约 4.5 unit / 5s，5.4 unit / 6s
- Turbo 版：约 4 unit / 5s
