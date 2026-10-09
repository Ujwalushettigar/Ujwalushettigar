#!/usr/bin/env python3
"""Generate the top-to-bottom ASCII profile animation (1500 x 1500 px, exactly 120 GIF frames).

    pip install pillow numpy
    python3 scripts/generate_ascii_animation.py

Default input  : assets/profile-ascii-1500-static.png   (your finished 1500 x 1500 ASCII portrait; never modified)
Default output : assets/profile-ascii-1500-topdown-120frames.gif

The animation reveals that portrait one line of characters at a time, from the top row to the bottom row,
like a terminal writing the image. Lines already written stay on screen.

Timeline (120 frames, every frame different from the one before it):
    frames   1- 96   write rows top to bottom, 50 ms each, small cursor block on the next row
    frames  97-110   hold the finished portrait, cursor block breathes in and out, 150 ms each
    frames 111-120   clear the screen top to bottom, 50 ms each, so the loop restarts from a blank terminal

To rebuild the portrait itself from a new photo instead of animating the existing render:
    python3 scripts/generate_ascii_animation.py --photo assets/profile-source.jpg --write-static
This converts the photo with a real luminance-to-character mapping (see render_from_photo). The glyphs come from
Roboto Mono and will not be pixel-identical to the existing PNG; keep the default mode to keep today's look.
"""
import argparse
import math
import pathlib
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SIZE, CELL = 1500, 8                       # canvas and character cell (187 x 187 characters)
WRITE, HOLD, ERASE = 96, 14, 10            # frame allocation, must add up to 120
TOTAL = WRITE + HOLD + ERASE
MS_WRITE, MS_HOLD, MS_ERASE = 50, 150, 50
CURSOR_RGB = (150, 158, 170)
BG = (7, 9, 12)

# photo mode only
RAMP = " .:-=+*#%@"
BLACK_POINT, GAMMA, CUTOFF = 0.16, 0.95, 2
FOCUS_X, FOCUS_Y = 0.5, 0.42
INK = (214, 214, 216)


def render_from_photo(path):
    """Real image-to-ASCII conversion: crop square, average to 187x187 cells, map brightness to RAMP."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    s = min(img.size)
    left = min(max(int(FOCUS_X * img.width - s / 2), 0), img.width - s)
    top = min(max(int(FOCUS_Y * img.height - s / 2), 0), img.height - s)
    g = ImageOps.autocontrast(ImageOps.grayscale(img.crop((left, top, left + s, top + s))), cutoff=CUTOFF)
    n = SIZE // CELL
    lum = np.asarray(g.resize((n, n), Image.BOX), dtype=np.float32) / 255.0
    lum = np.clip((lum - BLACK_POINT) / (1 - BLACK_POINT), 0, 1) ** GAMMA
    idx = np.rint(lum * (len(RAMP) - 1)).astype(int)
    fontfile = ASSETS / "fonts" / "RobotoMono-400.ttf"
    font = ImageFont.truetype(str(fontfile), 11) if fontfile.exists() else ImageFont.load_default()
    out = Image.new("RGB", (SIZE, SIZE), BG)
    d = ImageDraw.Draw(out)
    for r in range(n):
        for c in range(n):
            if idx[r, c]:
                d.text((c * CELL + CELL / 2, r * CELL + CELL / 2 + 1), RAMP[idx[r, c]], font=font, fill=INK, anchor="mm")
    return out


def row_edges(final):
    """Row boundaries, aligned to the gap line between rows of characters so no glyph is cut in half."""
    ink = (final.max(axis=2) > 60).sum(axis=1)
    gap = int(np.argmin([ink[r::CELL].sum() for r in range(CELL)]))
    edges = [0] + [y for y in range(gap, SIZE, CELL) if y >= CELL // 2] + [SIZE]
    if SIZE - edges[-2] < CELL // 2:
        edges.pop(-2)
    return edges


def build_frames(final, edges):
    rows = len(edges) - 1
    if rows < WRITE:
        sys.exit(f"only {rows} character rows; need at least {WRITE} to advance every frame")
    bg = np.zeros_like(final) + np.array(BG, np.uint8)
    cur = np.array(CURSOR_RGB, np.float32)
    frames, durs = [], []

    def block(img, row, alpha):
        y0, y1 = edges[row], edges[row + 1]
        reg = img[y0:y1, 0:CELL].astype(np.float32)
        img[y0:y1, 0:CELL] = np.clip(reg * (1 - alpha) + cur * alpha, 0, 255).astype(np.uint8)

    for f in range(WRITE):                                   # 1. write, top to bottom
        n = int(round(rows * (f + 1) / WRITE))
        img = bg.copy()
        img[:edges[n]] = final[:edges[n]]
        if n < rows:
            block(img, n, 0.85)
        frames.append(img); durs.append(MS_WRITE)
    for k in range(HOLD):                                    # 2. hold, cursor breathes (never equal twice in a row)
        a = 0.15 + 0.60 * (1 - math.cos(2 * math.pi * (k + 0.3) / HOLD)) / 2     # 0.15 .. 0.75, never 0
        img = final.copy()
        block(img, rows - 1, a)
        frames.append(img); durs.append(MS_HOLD)
    for e in range(ERASE):                                   # 3. clear, top to bottom
        m = int(round(rows * (e + 1) / ERASE))
        img = final.copy()
        img[:edges[m]] = bg[:edges[m]]
        frames.append(img); durs.append(MS_ERASE)
    for i in range(1, len(frames)):
        if np.array_equal(frames[i], frames[i - 1]):
            sys.exit(f"frame {i + 1} equals frame {i}; the GIF writer would merge them")
    if np.array_equal(frames[-1], frames[0]):
        sys.exit("last frame equals first frame")
    return frames, durs


def count_gif_frames(path):
    """Independent count: walk the GIF block structure and count image descriptors."""
    b = pathlib.Path(path).read_bytes()
    assert b[:6] in (b"GIF87a", b"GIF89a")
    flags = b[10]
    p = 13 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)
    n = 0
    skip = lambda p: next(i for i in range(p, len(b)) if b[i] == 0) + 1 if False else p
    while p < len(b):
        t = b[p]
        if t == 0x3B:
            break
        if t == 0x21:                                        # extension: label, then sub-blocks
            p += 2
            while b[p]:
                p += b[p] + 1
            p += 1
        elif t == 0x2C:                                      # image descriptor
            n += 1
            lf = b[p + 9]
            p += 10 + (3 * 2 ** ((lf & 7) + 1) if lf & 0x80 else 0)
            p += 1                                           # LZW minimum code size
            while b[p]:
                p += b[p] + 1
            p += 1
        else:
            raise ValueError(f"bad GIF block 0x{t:02x} at {p}")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ascii-image", default=str(ASSETS / "profile-ascii-1500-static.png"))
    ap.add_argument("--photo", help="convert this photo to ASCII instead of using --ascii-image")
    ap.add_argument("--write-static", action="store_true", help="with --photo: save the render as the static PNG")
    ap.add_argument("--out", default=str(ASSETS / "profile-ascii-1500-topdown-120frames.gif"))
    args = ap.parse_args()

    if args.photo:
        im = render_from_photo(args.photo)
        if args.write_static:
            im.save(args.ascii_image, optimize=True)
            print("wrote", args.ascii_image)
    else:
        im = Image.open(args.ascii_image).convert("RGB")
    if im.size != (SIZE, SIZE):
        sys.exit(f"expected a {SIZE}x{SIZE} image, got {im.size}")
    final = np.asarray(im)
    edges = row_edges(final)
    frames, durs = build_frames(final, edges)

    pal = im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)   # one palette for all frames
    pframes = [Image.fromarray(f).quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    pframes[0].save(args.out, save_all=True, append_images=pframes[1:], duration=durs, loop=0, optimize=False)

    # ---- verify what was actually written
    g = Image.open(args.out)
    n_pillow, n_raw = g.n_frames, count_gif_frames(args.out)
    ok = (g.size == (SIZE, SIZE), n_pillow == TOTAL, n_raw == TOTAL, g.info.get("loop") == 0)
    same = 0
    for i in range(g.n_frames):
        g.seek(i)
        same += np.array_equal(np.asarray(g.convert("RGB")), np.asarray(pframes[i].convert("RGB")))
    got = []
    for i in range(g.n_frames):
        g.seek(i); got.append(g.info["duration"])
    print(f"character rows : {len(edges) - 1}")
    print(f"size           : {g.size[0]} x {g.size[1]}")
    print(f"frames         : {n_pillow} (Pillow) / {n_raw} (raw GIF block count), expected {TOTAL}")
    print(f"loop           : {g.info.get('loop')} (0 = forever)")
    print(f"decoded frames identical to intended frames: {same}/{TOTAL}")
    print(f"duration       : {sum(got) / 1000:.2f} s  (write {MS_WRITE} ms x {WRITE}, hold {MS_HOLD} ms x {HOLD}, clear {MS_ERASE} ms x {ERASE})")
    print(f"file size      : {pathlib.Path(args.out).stat().st_size / 1024 / 1024:.2f} MB")
    if not (all(ok) and same == TOTAL and got == durs):
        sys.exit("VERIFICATION FAILED")
    print("verification passed")


if __name__ == "__main__":
    main()
