# Kling AI 3.0 API 要点

> 本文档记录实测确认的 Kling AI 3.0 API 细节（2026-09 实测）。

## 认证

- 方式：`Authorization: Bearer <api_key>`
- API Key 创建：`https://klingai.com/dev/api-key`（国际版）
- **注意**：Kling 3.0 已弃用旧版 AK/SK + JWT。用 JWT 会报 `code:1002 "The current API does not support AK/SK"`

## 端点

| 功能 | 端点 | 说明 |
|---|---|---|
| 文生视频 | `POST /text-to-video/{model}` | model 直接拼 URL，如 `kling-3.0-turbo` |
| 图生视频 | `POST /image-to-video/{model}` | 竖屏短剧主要用这个 |
| 文生图 | `POST /v1/images/omni-image` | 生成定妆图/场景图 |
| 查询任务 | `GET /tasks?task_ids={id}` | 返回数组 |
| 账户余额 | 无独立端点 | 余额不足报 `code:1102` |

## 文生视频（text-to-video）

请求体：
```json
{
  "prompt": "...",
  "negative_prompt": "低画质, 模糊, 变形, 文字乱码, 多余手指",
  "cfg_scale": 0.5,
  "aspect_ratio": "9:16",
  "duration": 5
}
```

- `cfg_scale` 0-1，默认 0.5（0.3-0.4 创作自由，0.7-1.0 严格贴合 prompt）
- `duration` 3-15 秒
- `generate_audio` bool，可选（原生音频/对白）

**⚠️ 实测：`aspect_ratio` 参数被忽略，一律生成 16:9（1280×720）。竖屏必须走 i2v。**

## 图生视频（image-to-video）— 短剧主力

请求体：
```json
{
  "contents": [
    {"type": "first_frame", "url": "场景合成图URL"},
    {"type": "element", "url": "角色定妆图URL"},
    {"type": "last_frame", "url": "尾帧图URL"}
  ],
  "prompt": "只写动作和运镜，不重新描述人物外貌",
  "negative_prompt": "...",
  "cfg_scale": 0.5,
  "duration": 5
}
```

### contents 数组（关键）

| type | 必需 | 作用 |
|---|---|---|
| `first_frame` | ✅ | 首帧图，视频从这张图开始 |
| `element` | 否 | **角色主体绑定**，锁定脸/服装/体型（人物一致性核心） |
| `last_frame` | 否 | 尾帧图，控制结束画面 |

- 字段名是 `url`（不是 `image`），只接受公网 URL（GitHub raw 可用），**base64 本地图不行**
- `element` 直接放角色定妆图 URL 即可，无需先创建"元素ID"
- 比例由 `first_frame` 图片决定（9:16 图 → 9:16 视频）

### 人物一致性

- 用 `element` 传角色定妆图，锁定角色
- 多角色场景：多个 `element` 项（每角色一张定妆图）
- `prompt` 只描述动作/运镜，不重新描述外观（避免和定妆图冲突）

## 查询任务

`GET /tasks?task_ids={id}` 返回：
```json
{
  "code": 0,
  "data": [
    {
      "id": "...",
      "status": "submitted|processing|succeeded|failed",
      "outputs": [{"type": "video", "url": "...", "duration": "5.041"}],
      "billing": [{"charge_type": "unit", "amount": "4", "package_type": "video"}]
    }
  ]
}
```

- `data` 是**数组**，取 `data[0]`
- 结果在 `data[0].outputs[].url`
- 计费 `billing[].amount`，视频每条约 4 unit

## 提交响应

```json
{"code": 0, "message": "SUCCEED", "data": {"id": "任务ID", "status": "submitted", ...}}
```

- 任务 ID 在 `data.id`

## 文生图（omni-image）

请求体：`{"prompt": "...", "aspect_ratio": "9:16", "negative_prompt": "..."}`
- 需要 `prompt` 字段
- 返回结构待实测确认（本次余额不足未完成验证）

## 错误码

| code | 含义 |
|---|---|
| 1002 | 认证错误（用了 AK/SK 而非 API Key） |
| 1102 | 账户余额不足 |
| 1201 | 参数错误（如 `prompt is required`、`contents cannot be empty`） |
| 1202 | HTTP 方法不支持 |

## 模型

- `kling-3.0-turbo`（本次使用，速度/价格档，1080p，3-15s，支持多镜头+原生音频+唇形同步）
- 其他：`kling-3.0`、`kling-3.0-omni`（参考/编辑旗舰，4K，元素库）
- 模型名以控制台可选列表为准
