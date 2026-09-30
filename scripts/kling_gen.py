#!/usr/bin/env python3
"""
Kling AI 3.0 完整版 视频生成工具（竖屏 + 原生对白 + 主体库绑定）

关键能力（实测校准）:
  主体库: POST /v1/general/advanced-custom-elements        创建主体(异步)
          GET  /v1/general/advanced-custom-elements/{id}   查询主体(拿 element_id)
  图生视频: POST /image-to-video/kling-3.0
     contents: [{type:prompt,text},{type:first_frame,url},{type:element,element_id,id}]
     settings: {multi_shot, audio:"native"|"off", resolution, duration}
  认证: Authorization: Bearer <api_key>

用法:
  python3 scripts/kling_gen.py auth
  python3 scripts/kling_gen.py element create --name 陈无敌 --desc "..." --frontal <url> [--refer <url> ...]
  python3 scripts/kling_gen.py element query <task_id>
  python3 scripts/kling_gen.py element list
  python3 scripts/kling_gen.py i2v -i <首帧图url> --element-ref chen:322705206027217 "prompt"
  python3 scripts/kling_gen.py shots shots/ep001.json [--dry-run]
  python3 scripts/kling_gen.py query <task_id> [--download]
"""

import argparse
import json
import os
import re
import sys
import time

import requests

DEFAULT_BASE = "https://api-beijing.klingai.com"
CONFIG_PATH = os.path.expanduser("~/.kling_config.json")

DEFAULT_MODEL = "kling-3.0"


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
        sys.exit("未配置 API Key，请先运行: python3 scripts/kling_gen.py auth")
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


# ---------- 主体库 ----------

def create_element(cfg, name, desc, frontal, refer_images):
    body = {
        "element_name": name,
        "element_description": desc,
        "reference_type": "image_refer",
        "element_image_list": {
            "frontal_image": frontal,
            "refer_images": [{"image_url": u} for u in refer_images],
        },
        "tag_list": [{"tag_id": "o_102"}],
    }
    data = api_post(cfg["base"], "/v1/general/advanced-custom-elements", cfg["api_key"], body)
    return data["data"]["task_id"]


def query_element(cfg, task_id):
    return api_get(cfg["base"], f"/v1/general/advanced-custom-elements/{task_id}", cfg["api_key"])["data"]


def wait_element(cfg, task_id, interval=8, timeout=900):
    start = time.time()
    while True:
        d = query_element(cfg, task_id)
        status = d.get("task_status")
        if status == "succeed":
            elems = d.get("task_result", {}).get("elements", [])
            return elems[0]["element_id"] if elems else None
        if status == "failed":
            raise RuntimeError(f"主体创建失败: {d.get('task_status_msg')}")
        if time.time() - start > timeout:
            raise TimeoutError(f"主体 {task_id} 超时")
        print(f"  主体状态 {status}，{interval}s 后重试…")
        time.sleep(interval)


def list_elements(cfg, page_num=1, page_size=30):
    data = api_get(cfg["base"], f"/v1/general/advanced-custom-elements?pageNum={page_num}&pageSize={page_size}", cfg["api_key"])
    return data.get("data", [])


# ---------- 视频生成（完整版） ----------

def submit_i2v_v3(cfg, prompt, first_frame, elements, duration, resolution, audio):
    contents = [{"type": "prompt", "text": prompt}]
    if first_frame:
        contents.append({"type": "first_frame", "url": first_frame})
    for ref, element_id in elements:
        contents.append({"type": "element", "element_id": str(element_id), "id": ref})
    body = {
        "contents": contents,
        "settings": {
            "multi_shot": True,
            "audio": audio,
            "resolution": resolution,
            "duration": int(duration),
        },
        "options": {"watermark_info": {"enabled": False}},
    }
    data = api_post(cfg["base"], f"/image-to-video/{DEFAULT_MODEL}", cfg["api_key"], body)
    return data["data"]["id"]


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
            raise TimeoutError(f"任务 {task_id} 超时")
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


def cmd_element_create(args):
    cfg = require_config()
    refer = args.refer if args.refer else [args.frontal]
    tid = create_element(cfg, args.name, args.desc, args.frontal, refer)
    print(f"已提交主体创建任务: {tid}")
    if args.wait:
        eid = wait_element(cfg, tid)
        print(f"element_id: {eid}")


def cmd_element_query(args):
    cfg = require_config()
    d = query_element(cfg, args.task_id)
    status = d.get("task_status")
    print(f"主体状态: {status}")
    if status == "succeed":
        for e in d.get("task_result", {}).get("elements", []):
            print(f"  element_id={e['element_id']}  name={e.get('element_name')}")


def cmd_element_list(args):
    cfg = require_config()
    items = list_elements(cfg)
    for item in items:
        status = item.get("task_status")
        elems = item.get("task_result", {}).get("elements", [])
        for e in elems:
            print(f"  element_id={e.get('element_id')}  name={e.get('element_name')}  status={e.get('status')}")


def cmd_i2v(args):
    cfg = require_config()
    elements = []
    for kv in args.element_ref or []:
        ref, eid = kv.split(":", 1)
        elements.append((ref, eid))
    prompt = f"镜头1, {args.duration}, {args.prompt}"
    tid = submit_i2v_v3(cfg, prompt, args.image, elements, args.duration, args.resolution, args.audio)
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
    elements_map = plan.get("elements", {})
    scene_prefix = plan.get("scene_prefix", "").rstrip("/")
    global_cfg = plan.get("global", {})
    resolution = global_cfg.get("resolution", args.resolution)
    audio = global_cfg.get("audio", args.audio)
    if args.limit:
        shots = shots[: args.limit]
    if args.dry_run:
        print(f"dry-run：共 {len(shots)} 个镜头（不提交）")
    for idx, s in enumerate(shots):
        duration = s.get("duration", args.duration)
        out_path = shot_out_path(s.get("id", ""))
        print(f"[{idx + 1}/{len(shots)}] {s.get('id', '')} ({duration}s) -> {out_path}")
        if args.dry_run:
            print(f"    element={s.get('element')}  first_frame={s.get('first_frame')}")
            print(f"    prompt: {s.get('prompt')}")
            continue
        try:
            refs = s.get("element", [])
            if isinstance(refs, str):
                refs = [refs]
            elements = [(r, elements_map[r]) for r in refs]
            ff = s.get("first_frame")
            ff_url = ff if ff.startswith(("http://", "https://")) else f"{scene_prefix}/{ff}"
            prompt = f"镜头1, {duration}, {s.get('prompt')}"
            tid = submit_i2v_v3(cfg, prompt, ff_url, elements, duration, resolution, audio)
            print(f"    提交任务: {tid}")
            if args.wait:
                print_result(wait_task(cfg, tid), tid, args.download, out_path)
        except Exception as e:
            print(f"    失败: {e}")
        if not args.wait:
            time.sleep(1)


def build_parser():
    p = argparse.ArgumentParser(description="Kling AI 3.0 完整版视频生成工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("auth", help="配置 API Key").set_defaults(func=cmd_auth)

    pe = sub.add_parser("element", help="主体库管理")
    pes = pe.add_subparsers(dest="sub", required=True)
    pec = pes.add_parser("create", help="创建主体")
    pec.add_argument("--name", required=True, help="主体名称(≤20字符)")
    pec.add_argument("--desc", required=True, help="主体描述(≤100字符)")
    pec.add_argument("--frontal", required=True, help="正面参考图 URL")
    pec.add_argument("--refer", action="append", help="其他角度参考图 URL（可多次）")
    pec.add_argument("--wait", action="store_true", help="等待完成并返回 element_id")
    pec.set_defaults(func=cmd_element_create)
    peq = pes.add_parser("query", help="查询主体")
    peq.add_argument("task_id")
    peq.set_defaults(func=cmd_element_query)
    pel = pes.add_parser("list", help="列出主体")
    pel.set_defaults(func=cmd_element_list)

    pi = sub.add_parser("i2v", help="图生视频（完整版，audio:native）")
    pi.add_argument("prompt", help="动作/对白描述（用 @ref 引用主体）")
    pi.add_argument("-i", "--image", required=True, help="首帧图 URL")
    pi.add_argument("--element-ref", action="append", help="主体绑定，格式 ref:element_id，可多次")
    pi.add_argument("--duration", default="5")
    pi.add_argument("--resolution", default="720p", choices=("720p", "1080p", "4k"))
    pi.add_argument("--audio", default="native", choices=("native", "off"))
    pi.add_argument("--wait", action="store_true")
    pi.add_argument("--download", action="store_true")
    pi.set_defaults(func=cmd_i2v)

    pq = sub.add_parser("query", help="查询视频任务")
    pq.add_argument("task_id")
    pq.add_argument("--download", action="store_true")
    pq.set_defaults(func=cmd_query)

    ps = sub.add_parser("shots", help="批量生成镜头")
    ps.add_argument("shots", help="镜头清单 JSON")
    ps.add_argument("--dry-run", action="store_true")
    ps.add_argument("--limit", type=int)
    ps.add_argument("--duration", default="5")
    ps.add_argument("--resolution", default="720p", choices=("720p", "1080p", "4k"))
    ps.add_argument("--audio", default="native", choices=("native", "off"))
    ps.add_argument("--wait", action="store_true")
    ps.add_argument("--download", action="store_true")
    ps.set_defaults(func=cmd_shots)

    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    args.func(args)
