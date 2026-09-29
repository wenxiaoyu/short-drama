#!/usr/bin/env python3
"""
检测定妆图四角水印位置（利用纯白背景：水印文字会形成角落的非白像素）

依赖: Pillow

用法:
  python3 detect_watermark.py [--dir characters] [--corner 300]
"""

import argparse
import glob
import os

from PIL import Image


def corner_nonwhite_ratio(img, corner, size):
    w, h = img.size
    x0 = 0 if "left" in corner else w - size
    y0 = 0 if "top" in corner else h - size
    region = img.crop((x0, y0, x0 + size, y0 + size)).convert("RGB")
    px = region.load()
    total = size * size
    nonwhite = 0
    for yy in range(0, size, 2):
        for xx in range(0, size, 2):
            r, g, b = px[xx, yy]
            if r < 205 or g < 205 or b < 205:
                nonwhite += 1
    return nonwhite / (total / 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work/characters_raw")
    ap.add_argument("--corner", type=int, default=300, help="检测角落区域大小")
    args = ap.parse_args()

    files = sorted(
        glob.glob(os.path.join(args.dir, "*.png"))
        + glob.glob(os.path.join(args.dir, "*.jpg"))
        + glob.glob(os.path.join(args.dir, "*.jpeg"))
    )
    for f in files:
        img = Image.open(f)
        ratios = {}
        for c in ("top-left", "top-right", "bottom-left", "bottom-right"):
            ratios[c] = corner_nonwhite_ratio(img, c, args.corner)
        # 判定：非白占比 > 2% 视为该角有水印
        suspects = [c for c, r in ratios.items() if r > 0.005]
        print(f"\n{os.path.basename(f)}  ({img.size[0]}x{img.size[1]})")
        for c in ("top-left", "top-right", "bottom-left", "bottom-right"):
            mark = " <-- 疑似水印" if c in suspects else ""
            print(f"    {c:12s} 非白占比 {ratios[c]*100:5.1f}%{mark}")


if __name__ == "__main__":
    main()
