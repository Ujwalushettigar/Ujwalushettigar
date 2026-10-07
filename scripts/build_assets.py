#!/usr/bin/env python3
"""Generate hero, boot, about, architecture, env, code and learning SVGs into assets/.

Every animation is SMIL (no JavaScript). The markup is always the FINAL, complete frame; animations
only replay the build-up on top of it, so a renderer without SMIL support still shows everything.

Edit the CONTENT section, then run:  python3 scripts/build_assets.py
Standard library only. Roboto Mono (subset, ASCII + a few symbols) is embedded
as base64 so the SVGs render in Roboto Mono without any external request.
"""
import base64
import os
import pathlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
# SVG_STATIC=1 renders a motionless final frame to /tmp/static (layout check only)
STATIC = os.environ.get("SVG_STATIC") == "1"
OUT = pathlib.Path("/tmp/static") if STATIC else ROOT / "assets"
OUT.mkdir(parents=True, exist_ok=True)

# ---- palette (GitHub dark, restrained) -------------------------------------
BG, BAR, LINE = "#0d1117", "#161b22", "#30363d"
TEXT, DIM, WHITE = "#c9d1d9", "#8b949e", "#e6edf3"
BLUE, GREEN, MUTED = "#58a6ff", "#3fb950", "#484f58"
STACK = "'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
ADV = 0.6  # Roboto Mono advance width in em
W = 560    # one design width for every graphic: stays legible when GitHub scales it down on a phone


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



# =============================== TIMELINE ENGINE ============================
def kt(times, T):
    return ";".join(f"{min(max(t / T, 0), 1):.5f}" for t in times)


def vals(v):
    return ";".join(str(x) for x in v)


class Scene:
    """One looping terminal animation. The markup is the finished frame; SMIL replays the build-up:
    elements fade in at absolute times, typed text is uncovered by a moving background-coloured
    rectangle, and one cursor rect hops along the typing positions. After the build-up the scene
    holds the finished frame for `hold` seconds, then replays."""

    def __init__(self, uid, fs=14, hold=14.0):
        self.uid, self.fs, self.hold = uid, fs, hold
        self.items, self.cur, self.t_end = [], [], 0.0

    @property
    def T(self):
        return self.t_end + self.hold

    def mark(self, t):
        self.t_end = max(self.t_end, t)

    def show(self, inner, on, off=None):
        """Visible from `on` (until `off` if given). Default markup state = end of the timeline."""
        self.mark(on if off is None else off)

        def f(T):
            if STATIC:
                return "", ("" if off is not None else inner)
            if off is None and on <= 0:
                return "", inner
            ts, vs = ([0, on], [0, 1]) if off is None else ([0, on, off], [0, 1, 0])
            base = 1 if off is None else 0
            return "", (f'<g opacity="{base}">{inner}<animate attributeName="opacity" dur="{T:.2f}s" '
                        f'repeatCount="indefinite" calcMode="discrete" keyTimes="{kt(ts, T)}" '
                        f'values="{vals(vs)}"/></g>')
        self.items.append(f)

    def typed(self, x, y, segs, t0, speed, fs=None):
        fs = fs or self.fs
        cw = fs * ADV
        text = "".join(s for _, s in segs)
        n = len(text)
        self.mark(t0 + n * speed)
        self.cur.append((t0, x, y))
        for k in range(1, n + 1):
            self.cur.append((t0 + k * speed, x + k * cw, y))

        def f(T):
            tsp = "".join(f'<tspan class="{c}">{escape(s)}</tspan>' if c else f"<tspan>{escape(s)}</tspan>"
                          for c, s in segs)
            txt = (f'<text x="{x:.1f}" y="{y}" font-size="{fs}" textLength="{n * cw:.1f}" '
                   f'lengthAdjust="spacing">{tsp}</text>')
            if STATIC:
                return "", txt
            ts = [0] + [t0 + k * speed for k in range(1, n + 1)]
            xs = [round(x, 1)] + [round(x + k * cw, 1) for k in range(1, n + 1)]
            ws = [round(n * cw + 6 - k * cw, 1) for k in range(0, n + 1)]
            common = (f'dur="{T:.2f}s" repeatCount="indefinite" calcMode="discrete" '
                      f'keyTimes="{kt(ts, T)}"')
            cover = (f'<rect x="{x + n * cw:.1f}" y="{y - 0.88 * fs:.1f}" width="6" '
                     f'height="{1.2 * fs:.1f}" fill="{BG}">'
                     f'<animate attributeName="x" {common} values="{vals(xs)}"/>'
                     f'<animate attributeName="width" {common} values="{vals(ws)}"/></rect>')
            return "", txt + cover
        self.items.append(f)
        return t0 + n * speed

    def _prompt_svg(self, x, y):
        cw = self.fs * ADV
        return prompt(x, y, "", self.fs, f' textLength="{16 * cw:.1f}" lengthAdjust="spacing"')

    def prompt_line(self, x, y, cmd, t0, speed=0.07):
        cw = self.fs * ADV
        self.show(self._prompt_svg(x, y), t0)
        self.cur.append((t0, x + 16 * cw, y))
        return self.typed(x + 16 * cw, y, [("w", cmd)], t0 + 0.3, speed)

    def idle_prompt(self, x, y, t0):
        self.show(self._prompt_svg(x, y), t0)
        self.cur.append((t0, x + 16 * self.fs * ADV, y))
        self.mark(t0)

    def cursor_svg(self, T):
        if STATIC or not self.cur:
            return ""
        out = []
        for e in sorted(self.cur, key=lambda e: e[0]):
            if out and abs(out[-1][0] - e[0]) < 1e-9:
                out[-1] = e
            else:
                out.append(e)
        if out[0][0] > 0:
            out.insert(0, (0, out[0][1], out[0][2]))
        fs, cw = self.fs, self.fs * ADV
        xs = [f"{e[1]:.1f}" for e in out]
        ys = [f"{e[2] - 0.875 * fs:.1f}" for e in out]
        common = f'dur="{T:.2f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{kt([e[0] for e in out], T)}"'
        return (f'<rect x="{xs[-1]}" y="{ys[-1]}" width="{cw:.1f}" height="{1.125 * fs:.1f}" '
                f'fill="{TEXT}" opacity=".85">'
                f'<animate attributeName="x" {common} values="{vals(xs)}"/>'
                f'<animate attributeName="y" {common} values="{vals(ys)}"/>'
                f'<animate attributeName="opacity" values=".85;0" keyTimes="0;.5" dur="1.1s" '
                f'calcMode="discrete" repeatCount="indefinite"/></rect>')

    def render(self, h, title, extra_defs=""):
        T = self.T
        parts = [it(T) for it in self.items]
        defs = "".join(d for d, _ in parts) + extra_defs
        body = "\n".join(b for _, b in parts) + "\n" + self.cursor_svg(T)
        return window(W, h, title, body, defs)


def line_el(x, y, segs, fs=14):
    tsp = "".join(f'<tspan class="{c}">{escape(s)}</tspan>' if c else f"<tspan>{escape(s)}</tspan>"
                  for c, s in segs)
    return f'<text x="{x}" y="{y}" font-size="{fs}">{tsp}</text>'


# =============================== CONTENT ====================================
NAME = "Ujwal Shettigar"
SUBTITLE = "CSE Student · Full-Stack Developer · Systems & Technology Explorer"
ROLES = [
    "CSE Student",
    "Full-Stack Developer",
    "C++ / DSA Learner",
    "Linux Enthusiast",
    "AI & Cybersecurity Explorer",
    "Game Development / Graphics Explorer",
]
BOOT = ["Loading identity...", "Loading projects...", "Loading stack...", "Fetching GitHub activity..."]
ABOUT_TXT = ["CSE Engineering Student", "Full-stack developer", "C++ / DSA learner", "Linux enthusiast",
             "AI / Cybersecurity explorer", "Game development / graphics explorer"]
FOCUS = ["C++ + DSA", "Full-stack applications", "Linux / systems", "AI / cybersecurity",
         "graphics programming"]
ENV = ["C++", "React", "Node.js", "Linux", "Git", "Supabase"]
LEARN_LEFT = [
    ("C++", ["Data Structures", "Algorithms"]),
    ("JavaScript", ["React", "Node.js"]),
    ("Linux", ["Shell", "Systems"]),
]
LEARN_RIGHT = [
    ("AI / ML", ["Applied AI"]),
    ("Cybersecurity", ["Network / app security"]),
    ("Graphics", ["OpenGL", "Vulkan"]),
]


# ================================= HERO =====================================
def hero():
    h, fs, L = 164, 16, 80
    cw = fs * ADV
    x0, yprompt, yrole = L + 2 * cw, 112, 140
    type_s, erase_s, hold, gap = 0.07, 0.025, 1.7, 0.35

    t, per = 0.0, []
    for s in ROLES:
        n, ev = len(s), [(t, 0)]
        ev += [(t + k * type_s, k) for k in range(1, n + 1)]
        t += n * type_s + hold
        ev += [(t + k * erase_s, n - k) for k in range(1, n + 1)]
        t += n * erase_s + gap
        per.append(ev)
    total = t

    def steps(attr, events, scale, base):
        evs = list(events)
        if evs[0][0] > 0:
            evs.insert(0, (0.0, 0))
        ded = []
        for tm, v in evs:
            if ded and abs(ded[-1][0] - tm) < 1e-9:
                ded[-1] = (tm, v)
            else:
                ded.append((tm, v))
        return (f'<animate attributeName="{attr}" dur="{total:.2f}s" repeatCount="indefinite" '
                f'calcMode="discrete" keyTimes="{kt([a for a, _ in ded], total)}" '
                f'values="{vals([round(base + v * scale, 1) for _, v in ded])}"/>')

    groups = []
    for i, s in enumerate(ROLES):
        n = len(s)
        txt = (f'<text x="{x0:.1f}" y="{yrole}" font-size="{fs}" textLength="{n * cw:.1f}" '
               f'lengthAdjust="spacing">{escape(s)}</text>')
        if STATIC:
            if i == 0:
                groups.append(txt)
            continue
        start, end = per[i][0][0], per[i][-1][0]
        gts, gvs = ([0, end], [1, 0]) if start == 0 else ([0, start, end], [0, 1, 0])
        cover = (f'<rect x="{x0 + n * cw:.1f}" y="{yrole - 0.88 * fs:.1f}" width="6" '
                 f'height="{1.2 * fs:.1f}" fill="{BG}">{steps("x", per[i], cw, x0)}'
                 f'{steps("width", per[i], -cw, n * cw + 6)}</rect>')
        groups.append(
            f'<g opacity="{1 if i == 0 else 0}">{txt}{cover}'
            f'<animate attributeName="opacity" dur="{total:.2f}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="{kt(gts, total)}" values="{vals(gvs)}"/></g>')

    cursor = "" if STATIC else (
        f'<rect x="{x0 + len(ROLES[0]) * cw:.1f}" y="{yrole - 14}" width="{cw:.1f}" height="18" '
        f'fill="{TEXT}" opacity=".85">{steps("x", [e for ev in per for e in ev], cw, x0)}'
        f'<animate attributeName="opacity" values=".85;0" keyTimes="0;.5" dur="1.1s" '
        f'calcMode="discrete" repeatCount="indefinite"/></rect>')

    body = "\n".join([
        f'<text x="{W / 2}" y="60" font-size="12" text-anchor="middle" class="d">{escape(SUBTITLE)}</text>',
        f'<path d="M{L} 80.5H{W - L}" stroke="{LINE}"/>',
        prompt(L, yprompt, "./introduce.sh", fs),
        f'<text x="{L}" y="{yrole}" font-size="{fs}" class="g">&gt;</text>',
        *groups, cursor,
    ])
    return window(W, h, "ujwal@github: ~", body)


# ================================== BOOT ====================================
def boot():
    fs, lh = 14, 24
    s = Scene("bt", fs=fs, hold=18.0)
    y = 58
    t = s.prompt_line(24, y, "./profile", 0.3) + 0.5
    for msg in BOOT:
        y += lh
        pend = line_el(24, y, [("d", "[ .. ] "), ("", msg)], fs)
        done = line_el(24, y, [("d", "[ "), ("g bold", "OK"), ("d", " ] "), ("", msg)], fs)
        s.show(pend, t, t + 0.55)
        s.show(done, t + 0.55)
        t += 0.8
    y += lh
    s.show(line_el(24, y, [("d", "[ "), ("g bold", "OK"), ("d", " ] "), ("w bold", "System ready.")], fs), t)
    t += 0.7
    y += lh + 6
    s.idle_prompt(24, y, t)
    return s.render(y + 20, "ujwal@github: ~")


# ================================== ABOUT ===================================
def about():
    fs, lh = 14, 22
    s = Scene("ab", fs=fs, hold=16.0)
    y, t = 58, 0.5

    def block(cmd, rows, t, y):
        t = s.prompt_line(24, y, cmd, t) + 0.45
        y += lh
        for segs in rows:
            s.show(line_el(24, y, segs, fs), t)
            t += 0.2
            y += lh
        return t + 0.3, y + lh // 2

    t, y = block("whoami", [[("w bold", NAME)]], t, y)
    t, y = block("cat about.txt", [[("", l)] for l in ABOUT_TXT], t, y)
    t, y = block("current_focus", [[("b", "-> "), ("", f)] for f in FOCUS], t, y)
    s.idle_prompt(24, y, t)
    return s.render(y + 20, "ujwal@github: ~")


# ============================== ENVIRONMENT =================================
def env():
    fs, lh = 14, 28
    s = Scene("en", fs=fs, hold=14.0)
    y0 = 58
    t = s.prompt_line(24, y0, "stack --active", 0.3) + 0.5
    cols = [24, 292]
    for i, name in enumerate(ENV):
        x, y = cols[i // 3], y0 + 12 + lh * (i % 3 + 1)
        inner = (
            f'<text x="{x}" y="{y}" font-size="14" class="w bold">{escape(name)}</text>'
            f'<circle cx="{x + 118}" cy="{y - 5}" r="4" fill="{GREEN}">'
            f'<animate attributeName="opacity" values="1;.3;1" dur="2.4s" begin="{i * 0.4:.1f}s" '
            f'repeatCount="indefinite"/></circle>'
            f'<text x="{x + 132}" y="{y}" font-size="12" class="g">ACTIVE</text>'
        )
        s.show(inner, t)
        t += 0.3
    yend = y0 + 12 + lh * 3 + 34
    s.idle_prompt(24, yend, t + 0.2)
    return s.render(yend + 20, "ujwal@github: ~")


# ================================== CODE ====================================
def code():
    fs, lh, cx = 14, 22, 60
    s = Scene("cd", fs=fs, hold=16.0)
    lines = [
        [("b", "#include"), ("", " "), ("g", "<iostream>")],
        None,
        [("b", "int"), ("", " "), ("w bold", "main"), ("", "() {")],
        [("", "    std::cout "), ("d", "<<"), ("", " "), ("g", '"Building something...\\n"'), ("", ";")],
        [("", "    "), ("b", "return"), ("", " "), ("g", "0"), ("", ";")],
        [("", "}")],
    ]
    y, t = 58, 0.4
    for i, segs in enumerate(lines, 1):
        s.show(f'<text x="24" y="{y}" font-size="{fs}" class="d">{i}</text>', t)
        if segs is None:
            t += 0.3
        else:
            t = s.typed(cx, y, segs, t, 0.05) + 0.3
        y += lh
    ysep = y - 6
    t += 0.5
    y += 14
    t = s.prompt_line(24, y, "g++ main.cpp -o main && ./main", t, 0.05) + 0.6
    y += lh
    s.show(f'<text x="24" y="{y}" font-size="{fs}">Building something...</text>', t)
    t += 0.6
    y += lh + 6
    s.idle_prompt(24, y, t)
    svg = s.render(y + 20, "main.cpp")
    return svg.replace("</svg>", f'<path d="M0 {ysep}.5H{W}" stroke="{LINE}"/>\n</svg>')


# ================================= LEARNING =================================
def learning():
    fs, lh = 14, 20
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
    yl, yr = col(24, LEARN_LEFT), col(292, LEARN_RIGHT)
    return window(W, max(yl, yr) + 2, "ujwal@github: ~/learning", "\n".join(parts))


# =============================== ARCHITECTURE ===============================
def architecture():
    h = 468
    cx, bw, bh = W // 2, 150, 44
    role_x, rw, rh = [110, 280, 450], 124, 40
    ycust, yweb, yapi, ysb, ytrunk, yrole = 68, 140, 220, 310, 366, 418
    marker = (f'<marker id="ah" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="6" markerHeight="6" '
              f'orient="auto"><path d="M0 0L8 4L0 8z" fill="{MUTED}"/></marker>')
    mk = ' marker-end="url(#ah)"'
    ln = lambda d, arrow=False: f'<path d="{d}" stroke="{MUTED}" fill="none"{mk if arrow else ""}/>'

    lines = [
        ln(f"M{cx} 86V117", True),
        ln(f"M{cx} 162V197", True),
        ln(f"M{cx} 242V287", True),
        ln(f"M{cx} 332V{ytrunk}"),
        ln(f"M{role_x[0]} {ytrunk}H{role_x[2]}"),
        *[ln(f"M{rx} {ytrunk}V397", True) for rx in role_x],
    ]

    # packets run behind the boxes, so they emerge from box edges; hidden until SMIL starts
    D, speed = 10.0, 120.0

    def packet(path, length, begin, color):
        a, b = begin / D, (begin + length / speed) / D
        return (f'<g opacity="0"><set attributeName="opacity" to="1" begin="0s"/>'
                f'<circle r="5" fill="{color}" opacity=".18"/><circle r="2.8" fill="{color}"/>'
                f'<animateMotion dur="{D:.0f}s" repeatCount="indefinite" calcMode="linear" path="{path}" '
                f'keyPoints="0;0;1;1" keyTimes="0;{a:.4f};{b:.4f};1"/></g>')

    pk = []
    if not STATIC:
        for rx, begin in zip(role_x, [1.2, 0.0, 2.4]):      # different timing per flow
            L = (ytrunk - ycust) + abs(cx - rx) + (yrole - ytrunk)
            pk.append(packet(f"M{cx} {ycust}V{ytrunk}H{rx}V{yrole}", L, begin, BLUE))
        pk.append(packet(f"M{cx} {ysb}V{ycust}", ysb - ycust, 6.2, GREEN))   # response to the customer

    def box(cxx, cy, bw_, bh_, title, sub=None, fs_t=13):
        x, y = cxx - bw_ / 2, cy - bh_ / 2
        out = [f'<rect x="{x:.0f}.5" y="{y:.0f}.5" width="{bw_ - 1}" height="{bh_ - 1}" fill="{BG}" stroke="{LINE}"/>']
        if sub:
            out.append(f'<text x="{cxx}" y="{cy - 2}" font-size="{fs_t}" text-anchor="middle" class="w bold">{escape(title)}</text>')
            out.append(f'<text x="{cxx}" y="{cy + 14}" font-size="10.5" text-anchor="middle" class="d">{escape(sub)}</text>')
        else:
            out.append(f'<text x="{cxx}" y="{cy + 4}" font-size="{fs_t}" text-anchor="middle" class="w">{escape(title)}</text>')
        return out

    boxes = []
    boxes += box(cx, ycust, bw, 36, "Customer")
    boxes += box(cx, yweb, bw, bh, "React / Vite", "frontend")
    boxes += box(cx, yapi, bw, bh, "Node / Express", "api server")
    boxes += box(cx, ysb, bw, bh, "Supabase", "database")
    for rx, name in zip(role_x, ["Picker", "Delivery Partner", "Admin"]):
        boxes += box(rx, yrole, rw, rh, name, None, 11.5)

    dim = lambda x, y, t: f'<text x="{x}" y="{y}" font-size="10.5" class="d">{escape(t)}</text>'
    labels = [
        dim(24, ycust + 4, "client"), dim(24, yweb + 4, "web"), dim(24, yapi + 4, "server"),
        dim(24, ysb + 4, "data"), dim(24, ytrunk + 4, "roles"),
        dim(cx + 12, 106, "browse / order"), dim(cx + 12, 184, "API request"), dim(cx + 12, 270, "query"),
        dim(cx + 12, 354, "role dashboards"),
    ]
    legend = (f'<circle cx="438" cy="66" r="3" fill="{BLUE}"/>{dim(450, 70, "request")}'
              f'<circle cx="438" cy="86" r="3" fill="{GREEN}"/>{dim(450, 90, "response")}')

    body = "\n".join(lines + pk + boxes + labels + [legend])
    return window(W, h, "hyperlocal-grocery-platform / request flow", body, marker)


if __name__ == "__main__":
    for name, fn in [("hero", hero), ("boot", boot), ("about", about), ("architecture", architecture),
                     ("env", env), ("code", code), ("learning", learning)]:
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print("wrote", OUT / f"{name}.svg")
