#!/usr/bin/env python3
"""Generate hero.svg, about.svg, learning.svg and architecture.svg into assets/.

Edit the CONTENT section, then run:  python3 scripts/build_assets.py
Standard library only. Roboto Mono (subset, ASCII + a few symbols) is embedded
as base64 so the SVGs render in Roboto Mono without any external request.
"""
import base64
import pathlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
FONTS = OUT / "fonts"

# ---- palette (GitHub dark, restrained) -------------------------------------
BG, BAR, LINE = "#0d1117", "#161b22", "#30363d"
TEXT, DIM, WHITE = "#c9d1d9", "#8b949e", "#e6edf3"
BLUE, GREEN, MUTED = "#58a6ff", "#3fb950", "#484f58"
STACK = "'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
ADV = 0.6  # Roboto Mono advance width in em


def b64(name):
    return base64.b64encode((FONTS / name).read_bytes()).decode()


def css(extra=""):
    return (
        "<style>"
        f"@font-face{{font-family:'Roboto Mono';font-weight:400;"
        f"src:url(data:font/woff2;base64,{b64('RobotoMono-400.woff2')}) format('woff2')}}"
        f"@font-face{{font-family:'Roboto Mono';font-weight:700;"
        f"src:url(data:font/woff2;base64,{b64('RobotoMono-700.woff2')}) format('woff2')}}"
        f"text{{font-family:{STACK};fill:{TEXT};white-space:pre}}"
        f".d{{fill:{DIM}}}.b{{fill:{BLUE}}}.g{{fill:{GREEN}}}.w{{fill:{WHITE}}}.bold{{font-weight:700}}"
        f"{extra}</style>"
    )


def window(w, h, title, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'xml:space="preserve" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
        f'aria-label="{escape(title)}">\n<title>{escape(title)}</title>\n'
        f"<defs>{css()}{defs}</defs>\n"
        f'<rect width="{w}" height="{h}" rx="4" fill="{BG}"/>\n'
        f'<path d="M0 4a4 4 0 0 1 4-4H{w-4}a4 4 0 0 1 4 4V28H0z" fill="{BAR}"/>\n'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="4" fill="none" stroke="{LINE}"/>\n'
        f'<path d="M0 28.5H{w}" stroke="{LINE}"/>\n'
        f'<text x="14" y="18" font-size="12" class="d">{escape(title)}</text>\n'
        f"{body}\n</svg>\n"
    )


def prompt(x, y, cmd, size=14, extra=""):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}"{extra}>'
        f'<tspan class="b">ujwal@github</tspan><tspan class="d">:</tspan>'
        f'<tspan class="b">~</tspan><tspan class="g">$ </tspan>'
        f'<tspan class="w">{escape(cmd)}</tspan></text>'
    )


def blink(x, y, w, h):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{TEXT}" opacity=".85">'
        f'<animate attributeName="opacity" values=".85;0" keyTimes="0;.5" dur="1.2s" '
        f'calcMode="discrete" repeatCount="indefinite"/></rect>'
    )


# =============================== CONTENT ====================================
NAME = "Ujwal Shettigar"
SUBTITLE = "CSE Student · Full-Stack Developer · Systems & Technology Explorer"
TYPED = [
    "Building things that actually work.",
    "C++ / DSA / Full-Stack Development",
    "Exploring Linux, AI and Cybersecurity",
    "Learning systems and graphics programming",
    "Turning ideas into software.",
]
ABOUT = [
    ("whoami", ["Ujwal Shettigar"]),
    ("cat about.txt", [
        "CSE Engineering student", "Full-stack developer", "C++ / DSA learner",
        "Linux enthusiast", "AI / cybersecurity explorer",
        "Game development / graphics explorer"]),
    ("currently", [
        "-> Building full-stack applications", "-> Improving DSA with C++",
        "-> Exploring AI and cybersecurity", "-> Learning systems and graphics"]),
]
LEARN_LEFT = [
    ("C++", ["Data Structures", "Algorithms"]),
    ("JavaScript", ["React", "Node.js"]),
    ("Linux", ["Shell", "Systems"]),
]
LEARN_RIGHT = [
    ("AI / ML", ["Applied AI"]),
    ("Cybersecurity", ["Network & application security"]),
    ("Graphics", ["OpenGL", "Vulkan"]),
]


# ================================= HERO =====================================
def hero():
    w, h, fs = 720, 210, 16
    cw = fs * ADV                      # 9.6 px per character
    x0, ytype = 150 + 2 * cw, 178      # typed text starts after "$ "
    type_s, erase_s, hold, gap = 0.07, 0.025, 1.7, 0.35

    t, per = 0.0, []
    for s in TYPED:
        n, ev = len(s), [(t, 0)]
        ev += [(t + k * type_s, k) for k in range(1, n + 1)]
        t += n * type_s + hold
        ev += [(t + k * erase_s, n - k) for k in range(1, n + 1)]
        t += n * erase_s + gap
        per.append(ev)
    total = t

    def anim(attr, events, scale, base=0.0):
        evs = [(0.0, 0)] + events if events[0][0] > 0 else list(events)
        evs.append((total, 0))
        ded, last = [], None
        for tm, v in evs:                      # drop repeated values (discrete hold)
            if v != last or tm == total:
                ded.append((tm, v)); last = v
        kt = ";".join(f"{tm/total:.5f}" for tm, _ in ded)
        vs = ";".join(f"{base + v*scale:.1f}" for _, v in ded)
        return (f'<animate attributeName="{attr}" dur="{total:.2f}s" repeatCount="indefinite" '
                f'calcMode="discrete" keyTimes="{kt}" values="{vs}"/>')

    clips, texts = [], []
    for i, s in enumerate(TYPED):
        clips.append(
            f'<clipPath id="c{i}"><rect x="{x0:.1f}" y="{ytype-18}" width="0" height="26">'
            f'{anim("width", per[i], cw)}</rect></clipPath>')
        texts.append(
            f'<text x="{x0:.1f}" y="{ytype}" font-size="{fs}" clip-path="url(#c{i})" '
            f'textLength="{len(s)*cw:.1f}" lengthAdjust="spacing">{escape(s)}</text>')
    allev = [e for ev in per for e in ev]
    cursor = (f'<rect x="{x0:.1f}" y="{ytype-14}" width="{cw:.1f}" height="18" fill="{TEXT}" opacity=".85">'
              f'{anim("x", allev, cw, x0)}'
              f'<animate attributeName="opacity" values=".85;0" keyTimes="0;.5" dur="1.2s" '
              f'calcMode="discrete" repeatCount="indefinite"/></rect>')

    body = "\n".join([
        f'<text x="{w/2}" y="90" font-size="36" text-anchor="middle" class="w bold">{escape(NAME)}</text>',
        f'<text x="{w/2}" y="116" font-size="13" text-anchor="middle" class="d">{escape(SUBTITLE)}</text>',
        f'<path d="M150 138.5H570" stroke="{LINE}"/>',
        f'<text x="150" y="{ytype}" font-size="{fs}" class="g">$</text>',
        *texts, cursor,
    ])
    return window(w, h, "ujwal@github: ~", body, "".join(clips))


# ================================= ABOUT ====================================
def about():
    w, fs, lh = 720, 14, 21
    y, parts = 58, []
    for cmd, out in ABOUT:
        parts.append(prompt(24, y, cmd)); y += lh
        for line in out:
            if line.startswith("->"):
                parts.append(f'<text x="24" y="{y}" font-size="{fs}"><tspan class="b">-&gt;</tspan>'
                             f'<tspan>{escape(line[2:])}</tspan></text>')
            else:
                cls = ' class="w bold"' if cmd == "whoami" else ""
                parts.append(f'<text x="24" y="{y}" font-size="{fs}"{cls}>{escape(line)}</text>')
            y += lh
        y += lh // 2
    cw = fs * ADV
    parts.append(prompt(24, y, "", extra=f' textLength="{16*cw:.1f}" lengthAdjust="spacing"'))
    parts.append(blink(24 + 16 * cw, y - 13, cw, 17))
    return window(w, y + 22, "ujwal@github: ~", "\n".join(parts))


# ================================= LEARNING =================================
def learning():
    w, fs, lh = 720, 14, 20
    parts = [prompt(24, 58, "tree ~/learning")]

    def col(x, groups):
        y = 90
        for head, leaves in groups:
            parts.append(f'<text x="{x}" y="{y}" font-size="{fs}" class="w bold">{escape(head)}</text>')
            y += lh
            for i, leaf in enumerate(leaves):
                con = "`-- " if i == len(leaves) - 1 else "|-- "
                parts.append(f'<text x="{x}" y="{y}" font-size="{fs}"><tspan class="d">{con}</tspan>'
                             f'<tspan>{escape(leaf)}</tspan></text>')
                y += lh
            y += lh // 2
        return y
    yl, yr = col(24, LEARN_LEFT), col(372, LEARN_RIGHT)
    return window(w, max(yl, yr) + 6, "ujwal@github: ~/learning", "\n".join(parts))


# =============================== ARCHITECTURE ===============================
def architecture():
    w, h, cy, bw, bh = 720, 262, 150, 104, 60
    xs = [24, 160, 296, 432]
    mains = [("Customer", "Browse · Order", "client"), ("Frontend", "React · Vite", "web"),
             ("API", "Node + Express", "server"), ("Supabase", "Database", "data")]
    roles = [("Picker", 88), ("Delivery Partner", 150), ("Admin", 212)]
    rx, rw, rh, trunk = 568, 128, 44, 552
    marker = (f'<marker id="ah" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="6" markerHeight="6" '
              f'orient="auto"><path d="M0 0L8 4L0 8z" fill="{MUTED}"/></marker>')

    lines = []
    for k in range(3):
        lines.append(f'<path d="M{xs[k]+bw} {cy}H{xs[k+1]}" stroke="{MUTED}" marker-end="url(#ah)"/>')
    lines.append(f'<path d="M{xs[3]+bw} {cy}H{trunk}M{trunk} 88V212" stroke="{MUTED}" fill="none"/>')
    for _, yc in roles:
        lines.append(f'<path d="M{trunk} {yc}H{rx}" stroke="{MUTED}" marker-end="url(#ah)"/>')

    # request packets: drawn BEFORE the boxes, so they emerge from box edges
    paths = [f'<path id="p0" d="M{xs[0]+bw/2} {cy}H{xs[3]+bw/2}" fill="none"/>']
    for i, (_, yc) in enumerate(roles, 1):
        paths.append(f'<path id="p{i}" d="M{xs[3]+bw/2} {cy}H{trunk}V{yc}H{rx+rw/2}" fill="none"/>')
    dur = "9s"
    pk = [f'<circle r="3" fill="{BLUE}"><animateMotion dur="{dur}" repeatCount="indefinite" '
          f'calcMode="linear" keyPoints="0;1;1" keyTimes="0;.45;1"><mpath xlink:href="#p0"/></animateMotion></circle>']
    for i in (1, 2, 3):
        pk.append(f'<circle r="3" fill="{BLUE}"><animateMotion dur="{dur}" repeatCount="indefinite" '
                  f'calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;.45;.72;1"><mpath xlink:href="#p{i}"/></animateMotion></circle>')

    boxes = []
    for x, (t, s, cap) in zip(xs, mains):
        boxes.append(f'<rect x="{x}.5" y="{cy-bh//2}.5" width="{bw-1}" height="{bh-1}" fill="{BG}" stroke="{LINE}"/>')
        boxes.append(f'<text x="{x+bw/2}" y="{cy-3}" font-size="13" text-anchor="middle" class="w bold">{t}</text>')
        boxes.append(f'<text x="{x+bw/2}" y="{cy+14}" font-size="10.5" text-anchor="middle" class="d">{escape(s)}</text>')
        boxes.append(f'<text x="{x}" y="{cy-bh/2-9}" font-size="10.5" class="d">{cap}</text>')
    boxes.append(f'<text x="{rx}" y="52" font-size="10.5" class="d">roles</text>')
    for t, yc in roles:
        boxes.append(f'<rect x="{rx}.5" y="{yc-rh//2}.5" width="{rw-1}" height="{rh-1}" fill="{BG}" stroke="{LINE}"/>')
        boxes.append(f'<text x="{rx+rw/2}" y="{yc+4}" font-size="12" text-anchor="middle" class="w">{t}</text>')

    body = "\n".join(lines + paths + pk + boxes)
    return window(w, h, "hyperlocal-grocery-platform / request flow", body, marker)


if __name__ == "__main__":
    for name, fn in [("hero", hero), ("about", about), ("learning", learning), ("architecture", architecture)]:
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print("wrote", OUT / f"{name}.svg")
