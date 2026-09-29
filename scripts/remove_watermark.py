#!/usr/bin/env python3
"""
去除豆包/即梦右下角水印：将水印区域填充为白色背景（不裁剪、不损失画面）

水印定位依据：多张定妆图检测结果一致，位于右下角
  距右 38px、距底 26px 起，约 259x66 像素

依赖: Pillow

用法:
  python3 remove_watermark.py                 # 处理 characters/ 输出到 characters_clean/
  python3 remove_watermark.py --dry-run       # 只预览
  python3 remove_watermark.py --pad 10        # 扩大填充范围10px（更保险）
"""

import argparse
import glob
import os

from PIL import Image

# 水印区域（相对图片右下角）：距右[from_right, to_right]，距底[from_bottom, to_bottom]
# 即填充 x ∈ [w-to_right, w-from_right], y ∈ [h-to_bottom, h-from_bottom]
FROM_RIGHT = 30
TO_RIGHT = 310
FROM_BOTTOM = 20
TO_BOTTOM = 100
FILL = (255, 255, 255)


def remove_one(path, out_dir, pad):
    img = Image.open(path).convert("RGB")
    w, h = img.size
    x0 = w - TO_RIGHT - pad
    x1 = w - FROM_RIGHT + pad
    y0 = h - TO_BOTTOM - pad
    y1 = h - FROM_BOTTOM + pad
    # 在副本上涂白，避免覆盖原图
    out = img.copy()
    for y in range(y0, y1):
        for x in range(x0, x1):
            out.putpixel((x, y), FILL)
    name = os.path.basename(path)
    out_path = os.path.join(out_dir, name)
    out.save(out_path)
    print(f"  {name}: 涂白区域 x[{x0},{x1}] y[{y0},{y1}] -> {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="work/characters_raw")
    ap.add_argument("--out", default="work/characters_clean")
    ap.add_argument("--pad", type=int, default=10, help="填充范围向外扩大的像素")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(
        glob.glob(os.path.join(args.dir, "*.png"))
        + glob.glob(os.path.join(args.dir, "*.jpg"))
        + glob.glob(os.path.join(args.dir, "*.jpeg"))
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
        remove_one(f, args.out, args.pad)


if __name__ == "__main__":
    main()
