#!/usr/bin/env python3
"""
批量裁剪图片右下角/底部水印（豆包/即梦水印通常在右下角）

依赖: Pillow  (pip install Pillow)

用法:
  python3 crop_watermark.py                          # 处理 characters/ 下所有 png/jpg
  python3 crop_watermark.py --bottom 80 --right 120  # 裁底部80px、右侧120px
  python3 crop_watermark.py --dry-run                # 只列出会处理的文件，不裁剪
"""

import argparse
import glob
import os

from PIL import Image

DEFAULT_DIR = "work/characters_raw"
DEFAULT_OUT = "work/characters_clean"


def crop_one(path, bottom, right, out_dir):
    img = Image.open(path)
    w, h = img.size
    box = (0, 0, w - right, h - bottom)
    cropped = img.crop(box)
    name = os.path.basename(path)
    out_path = os.path.join(out_dir, name)
    cropped.save(out_path)
    print(f"  {name}: {w}x{h} -> {cropped.width}x{cropped.height} -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=DEFAULT_DIR, help="输入目录")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出目录")
    ap.add_argument("--bottom", type=int, default=0, help="裁掉底部像素")
    ap.add_argument("--right", type=int, default=0, help="裁掉右侧像素")
    ap.add_argument("--dry-run", action="store_true", help="只预览不裁剪")
    args = ap.parse_args()

    files = sorted(
        glob.glob(os.path.join(args.dir, "*.png"))
        + glob.glob(os.path.join(args.dir, "*.jpg"))
        + glob.glob(os.path.join(args.dir, "*.jpeg"))
        + glob.glob(os.path.join(args.dir, "*.webp"))
    )
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
        crop_one(f, args.bottom, args.right, args.out)


if __name__ == "__main__":
    main()
