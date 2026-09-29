#!/usr/bin/env python3
"""
Kling AI 3.0 文生视频/图生视频命令行工具（已按实测 API 校准）

端点 (base 默认 https://api-beijing.klingai.com):
  提交: POST {base}/text-to-video/{model}     (文生视频)
        POST {base}/image-to-video/{model}    (图生视频)
  查询: GET  {base}/tasks?task_ids={id}

认证: Authorization: Bearer <api_key>  (从 https://klingai.com/dev/api-key 创建)

依赖: requests

用法:
  python3 scripts/kling_gen.py auth
  python3 scripts/kling_gen.py t2v "prompt" [选项]
  python3 scripts/kling_gen.py i2v -i 图片URL/路径 "prompt" [选项]
  python3 scripts/kling_gen.py query <task_id> [--download]
  python3 scripts/kling_gen.py shots shots/ep001.json [--dry-run]
  （shots 模式按镜头 id 输出到 output/ep{集数}/shot{镜头号}.mp4）
"""

import argparse
import base64
import json
import os
import re
import sys
import time

import requests

DEFAULT_BASE = "https://api-beijing.klingai.com"
CONFIG_PATH = os.path.expanduser("~/.kling_config.json")

DEFAULT_MODEL = "kling-3.0-turbo"
RATIOS = ("16:9", "9:16", "1:1")


# ---------- 配置 ----------

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.chmod(CONFIG_PATH, 0o600)


def require_config():
    cfg = load_config()
    if not cfg or not cfg.get("api_key"):
        sys.exit("未配置 API Key，请先运行: python3 kling_gen.py auth")
    return cfg


# ---------- API ----------

def api_post(base, path, api_key, body):
    url = base.rstrip("/") + path
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    r = requests.post(url, headers=headers, json=body, timeout=120)
    data = r.json()
    if isinstance(data, dict) and data.get("code") not in (0, None):
        raise RuntimeError(f"API 错误 code={data.get('code')} msg={data.get('message')}")
    return data


def api_get(base, path, api_key):
    url = base.rstrip("/") + path
    headers = {"Authorization": f"Bearer {api_key}"}
    r = requests.get(url, headers=headers, timeout=120)
    data = r.json()
    if isinstance(data, dict) and data.get("code") not in (0, None):
        raise RuntimeError(f"API 错误 code={data.get('code')} msg={data.get('message')}")
    return data


def submit_t2i(cfg, prompt, ratio, negative):
    body = {"prompt": prompt}
    if ratio:
        body["aspect_ratio"] = ratio
    if negative:
        body["negative_prompt"] = negative
    data = api_post(cfg["base"], "/v1/images/omni-image", cfg["api_key"], body)
    return data


def submit_t2v(cfg, prompt, model, negative, ratio, duration, cfg_scale, audio):
    body = {
        "prompt": prompt,
        "negative_prompt": negative,
        "cfg_scale": cfg_scale,
        "aspect_ratio": ratio,
        "duration": int(duration),
    }
    if audio:
        body["generate_audio"] = True
    data = api_post(cfg["base"], f"/text-to-video/{model}", cfg["api_key"], body)
    return data["data"]["id"]


def submit_i2v(cfg, prompt, contents, model, negative, duration, cfg_scale, audio):
    body = {
        "contents": contents,
        "prompt": prompt,
        "negative_prompt": negative,
        "cfg_scale": cfg_scale,
        "duration": int(duration),
    }
    if audio:
        body["generate_audio"] = True
    data = api_post(cfg["base"], f"/image-to-video/{model}", cfg["api_key"], body)
    return data["data"]["id"]


def build_contents(first_frame, elements=None, last_frame=None):
    items = [{"type": "first_frame", "url": first_frame}]
    for e in elements or []:
        items.append({"type": "element", "url": e})
    if last_frame:
        items.append({"type": "last_frame", "url": last_frame})
    return items


def query_task(cfg, task_id):
    data = api_get(cfg["base"], f"/tasks?task_ids={task_id}", cfg["api_key"])
    items = data.get("data", [])
    if isinstance(items, dict):
        items = [items]
    return items[0] if items else {}


def wait_task(cfg, task_id, interval=5, timeout=1800):
    start = time.time()
    while True:
        task = query_task(cfg, task_id)
        status = task.get("status")
        if status == "succeeded":
            return task
        if status in ("failed", "error"):
            raise RuntimeError(f"任务失败: {json.dumps(task, ensure_ascii=False)}")
        print(f"  状态 {status}，{interval}s 后重试…")
        if time.time() - start > timeout:
            raise TimeoutError(f"任务 {task_id} 超时未完成")
        time.sleep(interval)


def task_videos(task):
    vids = []
    for out in task.get("outputs", []) or []:
        if isinstance(out, dict) and out.get("url"):
            vids.append(out)
    return vids


def download(url, out_path):
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return out_path


# ---------- 子命令 ----------

def cmd_auth(args):
    cfg = load_config() or {}
    key = input(f"API Key [{cfg.get('api_key', '')}]: ").strip() or cfg.get("api_key", "")
    base = input(f"API Base [{cfg.get('base', DEFAULT_BASE)}]: ").strip() or cfg.get("base", DEFAULT_BASE)
    if not key:
        sys.exit("API Key 不能为空")
    cfg.update({"api_key": key, "base": base})
    save_config(cfg)
    print(f"已保存到 {CONFIG_PATH}")


def cmd_t2i(args):
    cfg = require_config()
    data = submit_t2i(cfg, args.prompt, args.ratio, args.negative)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_t2v(args):
    cfg = require_config()
    tid = submit_t2v(cfg, args.prompt, args.model, args.negative,
                     args.ratio, args.duration, args.cfg_scale, args.audio)
    print(f"已提交文生视频任务: {tid}")
    if args.wait:
        print_result(wait_task(cfg, tid), tid, args.download)


def cmd_i2v(args):
    cfg = require_config()
    contents = build_contents(args.image, args.element, args.last_frame)
    tid = submit_i2v(cfg, args.prompt, contents, args.model, args.negative,
                     args.duration, args.cfg_scale, args.audio)
    print(f"已提交图生视频任务: {tid}")
    if args.wait:
        print_result(wait_task(cfg, tid), tid, args.download)


def cmd_query(args):
    cfg = require_config()
    print_result(query_task(cfg, args.task_id), args.task_id, args.download)


def print_result(task, task_id, do_download, out_path=None):
    if not task:
        print("未查询到任务结果")
        return
    status = task.get("status")
    print(f"任务状态: {status}")
    videos = task_videos(task)
    for i, v in enumerate(videos):
        url = v.get("url")
        print(f"  视频{i}: {url}")
        if do_download and url:
            if out_path:
                out = out_path if i == 0 else out_path.replace(".mp4", f"_{i}.mp4")
                os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
            else:
                out = f"kling_out_{str(task_id)[:12]}_{i}.mp4"
            download(url, out)
            print(f"  已下载: {out}")
    billing = task.get("billing")
    if billing:
        print(f"  计费: {json.dumps(billing, ensure_ascii=False)}")
    if not videos and do_download:
        print(json.dumps(task, ensure_ascii=False, indent=2))


def build_shot_contents(shot, char_urls, scene_prefix):
    items = []
    ff = shot.get("first_frame")
    if ff:
        ff_url = ff if ff.startswith(("http://", "https://")) else f"{scene_prefix}/{ff}"
        items.append({"type": "first_frame", "url": ff_url})
    elements = shot.get("element", [])
    if isinstance(elements, str):
        elements = [elements]
    for e in elements:
        e_url = char_urls.get(e, e) if char_urls else e
        items.append({"type": "element", "url": e_url})
    return items


def shot_out_path(shot_id):
    m = re.match(r"ep(\d+)_shot(\d+)", shot_id or "")
    if not m:
        return None
    return f"output/ep{m.group(1)}/shot{m.group(2)}.mp4"


def cmd_shots(args):
    cfg = None if args.dry_run else require_config()
    with open(args.shots, encoding="utf-8") as f:
        plan = json.load(f)
    shots = plan.get("shots", [])
    char_urls = plan.get("character_urls", {})
    scene_prefix = plan.get("scene_prefix", "").rstrip("/")
    if args.limit:
        shots = shots[: args.limit]
    if args.dry_run:
        print(f"dry-run：共 {len(shots)} 个镜头（不提交）")
    for idx, s in enumerate(shots):
        stype = s.get("type", "t2v")
        prompt = s.get("prompt", "")
        duration = s.get("duration", args.duration)
        out_path = shot_out_path(s.get("id", ""))
        print(f"[{idx + 1}/{len(shots)}] {s.get('id', '')} ({stype}, {duration}s) -> {out_path}")
        if args.dry_run:
            print(f"    prompt: {prompt}")
            if stype == "i2v":
                print(f"    element={s.get('element')}  first_frame={s.get('first_frame')}")
            continue
        try:
            model = s.get("model", args.model)
            negative = s.get("negative_prompt", plan.get("global", {}).get("negative_prompt", ""))
            cfg_scale = s.get("cfg_scale", plan.get("global", {}).get("cfg_scale", args.cfg_scale))
            audio = s.get("generate_audio", args.audio)
            if stype == "i2v":
                contents = s.get("contents") or build_shot_contents(s, char_urls, scene_prefix)
                tid = submit_i2v(cfg, prompt, contents, model, negative,
                                 duration, cfg_scale, audio)
            else:
                ratio = s.get("aspect_ratio", plan.get("global", {}).get("aspect_ratio", args.ratio))
                tid = submit_t2v(cfg, prompt, model, negative,
                                 ratio, duration, cfg_scale, audio)
            print(f"    提交任务: {tid}")
            if args.wait:
                print_result(wait_task(cfg, tid), tid, args.download, out_path)
        except Exception as e:
            print(f"    失败: {e}")
        if not args.wait:
            time.sleep(1)


def build_parser():
    p = argparse.ArgumentParser(description="Kling AI 3.0 视频生成工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth", help="配置 API Key").set_defaults(func=cmd_auth)

    ptg = sub.add_parser("t2i", help="文生图（生成角色定妆图）")
    ptg.add_argument("prompt")
    ptg.add_argument("--ratio", default="9:16", choices=RATIOS)
    ptg.add_argument("--negative", default="")
    ptg.set_defaults(func=cmd_t2i)

    pt = sub.add_parser("t2v", help="文生视频")
    pt.add_argument("prompt")
    pt.add_argument("--model", default=DEFAULT_MODEL)
    pt.add_argument("--negative", default="低画质, 模糊, 变形, 文字乱码, 多余手指")
    pt.add_argument("--ratio", default="9:16", choices=RATIOS)
    pt.add_argument("--duration", default="5", help="秒数，Kling 3.0 支持 3-15")
    pt.add_argument("--cfg-scale", type=float, default=0.5)
    pt.add_argument("--audio", action="store_true", help="生成原生音频/对白")
    pt.add_argument("--wait", action="store_true")
    pt.add_argument("--download", action="store_true")
    pt.set_defaults(func=cmd_t2v)

    pi = sub.add_parser("i2v", help="图生视频")
    pi.add_argument("prompt")
    pi.add_argument("-i", "--image", required=True, help="首帧图 URL")
    pi.add_argument("--element", action="append", default=[], help="角色参考图 URL（可多次指定，用于一致性）")
    pi.add_argument("--last-frame", default=None, help="尾帧图 URL")
    pi.add_argument("--model", default=DEFAULT_MODEL)
    pi.add_argument("--negative", default="低画质, 模糊, 变形, 文字乱码, 多余手指")
    pi.add_argument("--duration", default="5")
    pi.add_argument("--cfg-scale", type=float, default=0.5)
    pi.add_argument("--audio", action="store_true")
    pi.add_argument("--wait", action="store_true")
    pi.add_argument("--download", action="store_true")
    pi.set_defaults(func=cmd_i2v)

    pq = sub.add_parser("query", help="查询任务")
    pq.add_argument("task_id")
    pq.add_argument("--download", action="store_true")
    pq.set_defaults(func=cmd_query)

    ps = sub.add_parser("shots", help="批量生成镜头")
    ps.add_argument("shots", help="镜头清单 JSON 文件")
    ps.add_argument("--dry-run", action="store_true")
    ps.add_argument("--limit", type=int)
    ps.add_argument("--model", default=DEFAULT_MODEL)
    ps.add_argument("--ratio", default="9:16", choices=RATIOS)
    ps.add_argument("--duration", default="5")
    ps.add_argument("--cfg-scale", type=float, default=0.5)
    ps.add_argument("--audio", action="store_true")
    ps.add_argument("--wait", action="store_true")
    ps.add_argument("--download", action="store_true")
    ps.set_defaults(func=cmd_shots)

    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
