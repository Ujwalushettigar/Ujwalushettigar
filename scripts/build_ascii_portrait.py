#!/usr/bin/env python3
"""Turn a photograph into an animated ASCII terminal portrait for the GitHub README.

    pip install pillow numpy
    python3 scripts/build_ascii_portrait.py                 # writes the GIF and both PNGs into assets/
    python3 scripts/build_ascii_portrait.py --text          # also prints the ASCII portrait in this terminal

Input : assets/profile-source.jpg   (or .jpeg / .png / .webp). It is only ever READ, never modified.
Output: assets/profile-ascii.gif         animated loop: photo -> pixel mosaic -> ASCII, hold, back to photo
        assets/profile-ascii-static.png  the finished ASCII frame (reduced-motion / fallback)
        assets/profile-photo-static.png  the photograph inside the same terminal window

How the ASCII is made (a real image-to-ASCII conversion, nothing pre-written):
  1. crop the photo to a 4:5 portrait around (FOCUS_X, FOCUS_Y) and resize to the character grid area
  2. average the grayscale image into one brightness value per character cell
  3. stretch contrast, drop everything under BLACK_POINT to empty space, apply GAMMA, map brightness
     to RAMP (light-on-dark: brighter = denser glyph, so the face glows out of a dark terminal)
  4. draw each glyph with Roboto Mono; the 6x10 px cell matches a terminal's tall character aspect
  5. every cell then goes photo -> mosaic -> scrambled glyphs -> final glyph, top to bottom with
     per-cell jitter; the reverse runs bottom to top. All frames share one 256-colour palette so the
     GIF stores only the cells that change between frames.
"""
import argparse
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SOURCES = ["profile-source.jpg", "profile-source.jpeg", "profile-source.png", "profile-source.webp"]

# ---- tuning ----------------------------------------------------------------
COLS = 88                 # characters per row
CW, CH = 6, 10            # cell size in px (Roboto Mono 10 px has a 6 px advance)
ASPECT = 4 / 5            # portrait crop, width / height
FOCUS_X, FOCUS_Y = 0.5, 0.42   # crop centre as a fraction of the photo (smaller y = higher up)
RAMP = " .:-=+*#%@"       # sparse -> dense
BLACK_POINT = 0.16        # brightness below this becomes empty space (keeps a dark background clean)
GAMMA = 0.95              # < 1 brightens mid-tones
CUTOFF = 2                # % of the darkest / brightest pixels clipped when stretching contrast
INVERT = False            # True flips the ramp (use if the photo has a bright background)
W = 560                   # GIF width in px
FRAME_MS = 80
SEED = 7

# ---- palette (GitHub dark, same as the other README graphics) --------------
BG, BAR, LINE = (13, 17, 23), (22, 27, 34), (48, 54, 61)
TEXT, DIM, WHITE = (201, 209, 217), (139, 148, 158), (230, 237, 243)
BLUE, GREEN = (88, 166, 255), (63, 185, 80)

PHOTO, MOSAIC, SCRAMBLE, ASCII = 0, 1, 2, 3


def find_font(size, bold=False):
    name = f"RobotoMono-{700 if bold else 400}.ttf"
    for p in (ASSETS / "fonts" / name, pathlib.Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")):
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def load_source():
    for n in SOURCES:
        p = ASSETS / n
        if p.exists():
            print("source photo:", p.relative_to(ROOT))
            return ImageOps.exif_transpose(Image.open(p)).convert("RGB"), False
    print("note: no assets/profile-source.* found; using a neutral placeholder image instead of a photo")
    im = Image.new("RGB", (800, 1000), (40, 46, 56))
    d = ImageDraw.Draw(im)
    for y in range(1000):
        v = int(30 + 60 * (1 - abs(y - 420) / 600))
        d.line([(0, y), (800, y)], fill=(v, v + 4, v + 12))
    d.text((400, 470), "US", font=find_font(300, True), fill=(225, 230, 238), anchor="mm")
    return im, True


def crop_portrait(im, w, h):
    iw, ih = im.size
    cw_, ch_ = (iw, int(iw / ASPECT)) if iw / ih < ASPECT else (int(ih * ASPECT), ih)
    left = min(max(int(FOCUS_X * iw - cw_ / 2), 0), iw - cw_)
    top = min(max(int(FOCUS_Y * ih - ch_ / 2), 0), ih - ch_)
    return im.crop((left, top, left + cw_, top + ch_)).resize((w, h), Image.LANCZOS)


class Portrait:
    def __init__(self):
        src, self.placeholder = load_source()
        self.cols = COLS
        self.rows = round(COLS * CW / ASPECT / CH)
        self.rw, self.rh = self.cols * CW, self.rows * CH
        photo = crop_portrait(src, self.rw, self.rh)
        self.rx, self.ry = (W - self.rw) // 2, 70
        self.H = self.ry + self.rh + 58

        # --- brightness per character cell -> glyph index
        g = ImageOps.autocontrast(ImageOps.grayscale(photo), cutoff=CUTOFF)
        g = g.resize((self.cols, self.rows), Image.BOX)
        lum = np.clip((np.asarray(g, dtype=np.float32) / 255.0 - BLACK_POINT) / (1 - BLACK_POINT), 0, 1) ** GAMMA
        if INVERT:
            lum = 1 - lum
        self.lum = lum
        self.idx = np.rint(lum * (len(RAMP) - 1)).astype(int)

        # --- palette shared by every frame: photo colours + grays + UI colours
        pq = photo.quantize(190, method=Image.Quantize.MEDIANCUT)
        pal = pq.getpalette()[:190 * 3]
        grays = [v for v in np.linspace(BG[0], 240, 50).astype(int) for _ in range(3)]
        ui = [c for col in (BG, BAR, LINE, TEXT, DIM, WHITE, BLUE, GREEN) for c in col]
        flat = (pal + grays + ui)[:768]
        flat += [0] * (768 - len(flat))
        self.pal_img = Image.new("P", (1, 1))
        self.pal_img.putpalette(flat)
        self.photo = np.asarray(
            photo.quantize(palette=self.pal_img, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB"))
        self.photo_clean = photo

        # --- layers: mosaic, final ASCII, scrambled "decoding" glyphs
        small = np.asarray(photo.resize((self.cols, self.rows), Image.BOX), dtype=np.float32)
        self.mosaic = np.kron(small, np.ones((CH, CW, 1))).astype(np.uint8)
        self.tiles = self._glyph_tiles()
        self.ascii = self._draw_ascii(self.idx, self.lum, 1.0)
        rng = np.random.default_rng(SEED)
        self.scr = []
        for _ in range(3):
            j = np.clip(self.idx + rng.integers(-3, 4, self.idx.shape), 1, len(RAMP) - 1)
            self.scr.append(self._draw_ascii(j, self.lum, 0.62))
        self.rng = rng

    def _glyph_tiles(self):
        font = find_font(10)
        asc, desc = font.getmetrics()
        base = asc + (CH - (asc + desc)) // 2
        tiles = []
        for ch in RAMP:
            m = Image.new("L", (CW, CH), 0)
            if ch != " ":
                ImageDraw.Draw(m).text((0, base), ch, font=font, fill=255, anchor="ls")
            tiles.append(np.asarray(m, dtype=np.float32) / 255.0)
        return tiles

    def _draw_ascii(self, idx, lum, strength):
        out = np.zeros((self.rh, self.rw, 3), np.float32) + np.array(BG, np.float32)
        gray = (95 + lum * 145) * strength + BG[0] * (1 - strength)
        for r in range(self.rows):
            for c in range(self.cols):
                k = idx[r, c]
                if k:
                    a = self.tiles[k][:, :, None]
                    box = out[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
                    box += a * (gray[r, c] - box)
        return np.clip(out, 0, 255).astype(np.uint8)

    # ---- frame assembly --------------------------------------------------------
    def schedule(self, span, jitter, bottom_up):
        rows = np.arange(self.rows)[:, None] * np.ones((1, self.cols))
        if bottom_up:
            rows = (self.rows - 1) - rows
        j = self.rng.integers(0, jitter + 1, (self.rows, self.cols))
        return np.floor(rows / (self.rows - 1) * span).astype(int) + j

    def phases(self, start, f, reverse):
        t = f - start
        if not reverse:   # photo -> mosaic -> scramble -> ascii
            return np.select([t < 0, t < 1, t < 3], [PHOTO, MOSAIC, SCRAMBLE], ASCII)
        return np.select([t < 0, t < 1, t < 2], [ASCII, SCRAMBLE, MOSAIC], PHOTO)

    def region(self, ph, f):
        px = lambda m: np.repeat(np.repeat(m, CH, 0), CW, 1)[:, :, None]
        out = self.photo.copy()
        out = np.where(px(ph == MOSAIC), self.mosaic, out)
        out = np.where(px(ph == ASCII), self.ascii, out)
        sel = (np.arange(self.rows)[:, None] + np.arange(self.cols)[None, :] + f) % 3
        for k in range(3):
            out = np.where(px((ph == SCRAMBLE) & (sel == k)), self.scr[k], out)
        return out

    def canvas(self, region, status, bar, cursor):
        im = Image.new("RGB", (W, self.H), BG)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W - 1, 27], fill=BAR)
        d.line([(0, 28), (W, 28)], fill=LINE)
        d.text((14, 14), "ujwal@github: ~", font=find_font(12), fill=DIM, anchor="lm")
        f12 = find_font(12)
        x = 24
        for txt, col in (("ujwal@github", BLUE), (":", DIM), ("~", BLUE), ("$ ", GREEN),
                         ("./render_profile --ascii", WHITE)):
            d.text((x, 50), txt, font=f12, fill=col, anchor="lm")
            x += f12.getlength(txt)
        if cursor:
            d.rectangle([x + 2, 43, x + 8, 56], fill=TEXT)
        im.paste(Image.fromarray(region), (self.rx, self.ry))
        d.line([(0, self.ry + self.rh + 16), (W, self.ry + self.rh + 16)], fill=LINE)
        ys = self.ry + self.rh + 37
        d.text((24, ys), status, font=f12, fill=TEXT if "COMPLETE" not in status else GREEN, anchor="lm")
        d.text((W - 24, ys), bar, font=f12, fill=DIM, anchor="rm")
        d.rectangle([0, 0, W - 1, self.H - 1], outline=LINE)
        return im

    def bar(self, frac):
        n = int(round(frac * 20))
        return f"[{'#' * n}{'-' * (20 - n)}] {int(round(frac * 100)):3d}%"

    def build(self):
        shots, dur = [], []

        def add(region, status, bar, cursor, ms):
            shots.append(self.canvas(region, status, bar, cursor).quantize(palette=self.pal_img, dither=Image.Dither.NONE))
            dur.append(ms)

        photo_ph = np.full((self.rows, self.cols), PHOTO)
        ascii_ph = np.full((self.rows, self.cols), ASCII)
        add(self.photo, "[ READY ] profile loaded", self.bar(0), True, 500)
        add(self.photo, "[ READY ] profile loaded", self.bar(0), False, 500)
        add(self.photo, "[ READY ] profile loaded", self.bar(0), True, 300)

        start = self.schedule(span=20, jitter=4, bottom_up=False)
        nf = int(start.max()) + 4
        for f in range(nf):
            ph = self.phases(start, f, False)
            frac = float((ph != PHOTO).mean())
            add(self.region(ph, f), "[ PROCESSING PROFILE... ]", self.bar(frac), False, FRAME_MS)

        for i in range(4):
            add(self.ascii, "ASCII PROFILE RENDER COMPLETE", self.bar(1), i % 2 == 0, 500)

        start = self.schedule(span=11, jitter=3, bottom_up=True)
        nf = int(start.max()) + 3
        for f in range(nf):
            ph = self.phases(start, f, True)
            frac = float((ph != PHOTO).mean())
            add(self.region(ph, f), "[ RESTORING PHOTO... ]", self.bar(frac), False, FRAME_MS)
        self.statics = (
            self.canvas(self.ascii, "ASCII PROFILE RENDER COMPLETE", self.bar(1), True),
            self.canvas(self.photo, "[ READY ] profile loaded", self.bar(0), True),
        )
        return shots, dur

    def ascii_text(self):
        return "\n".join("".join(RAMP[k] for k in row) for row in self.idx)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--text", action="store_true", help="also print the ASCII portrait as plain text")
    ap.add_argument("--out", default=str(ASSETS), help="output directory (default: assets/)")
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    p = Portrait()
    shots, dur = p.build()
    gif = out / "profile-ascii.gif"
    shots[0].save(gif, save_all=True, append_images=shots[1:], duration=dur, loop=0, optimize=False)
    p.statics[0].quantize(palette=p.pal_img, dither=Image.Dither.NONE).save(out / "profile-ascii-static.png", optimize=True)
    p.statics[1].quantize(palette=p.pal_img, dither=Image.Dither.NONE).save(out / "profile-photo-static.png", optimize=True)
    total = sum(dur) / 1000
    print(f"grid {p.cols}x{p.rows} characters, {len(shots)} frames, loop {total:.1f} s")
    print(f"wrote {gif} ({gif.stat().st_size // 1024} KB), profile-ascii-static.png, profile-photo-static.png")
    if args.text:
        print(p.ascii_text())


if __name__ == "__main__":
    sys.exit(main())
