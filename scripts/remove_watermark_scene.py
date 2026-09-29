#!/usr/bin/env python3
"""
去除合成图（深色场景）右下角水印：用水印区域上方紧邻一行的背景色向下填充

水印位置与定妆图一致（豆包水印固定）：距右 30~310px，距底 20~100px
不同于定妆图的"涂白"，这里用"上方背景行"填充，适配深色夜景场景

依赖: Pillow

用法:
  python3 remove_watermark_scene.py                 # scenes/ -> scenes_clean/
  python3 remove_watermark_scene.py --dry-run
"""

import argparse
import glob
import os

from PIL import Image

FROM_RIGHT = 30
TO_RIGHT = 310
FROM_BOTTOM = 20
TO_BOTTOM = 100


def remove_one(path, out_dir):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    x0, x1 = w - TO_RIGHT, w - FROM_RIGHT
    y0, y1 = h - TO_BOTTOM, h - FROM_BOTTOM
    out = img.copy()
    px = out.load()
    # 参考行：水印区域上方紧邻的一行（干净背景）
    ref_y = y0 - 1
    ref_row = [px[x, ref_y] for x in range(x0, x1)]
    for y in range(y0, y1):
        for i, x in enumerate(range(x0, x1)):
            px[x, y] = ref_row[i]
    name = os.path.basename(path)
    out_path = os.path.join(out_dir, name)
    out.save(out_path)
    print(f"  {name}: 填充水印区域 x[{x0},{x1}] y[{y0},{y1}] -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work/scenes_raw")
    ap.add_argument("--out", default="work/scenes_clean")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.dir, "*.png")) + glob.glob(os.path.join(args.dir, "*.jpg")))
    if not files:
        print(f"{args.dir} 下未找到图片")
        return
    print(f"找到 {len(files)} 张图")
    if args.dry_run:
        for f in files:
            print("  ", os.path.basename(f))
        return
    os.makedirs(args.out, exist_ok=True)
    for f in files:
        remove_one(f, args.out)


if __name__ == "__main__":
    main()
