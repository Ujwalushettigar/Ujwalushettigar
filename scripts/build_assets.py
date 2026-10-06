#!/usr/bin/env python3
"""Generate hero, boot, about, architecture, env, code and learning SVGs into assets/.

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


class Scene:
    """One looping SVG animation. Everything is SMIL (no JS, no CSS animation):
    elements are revealed at absolute times, text is typed with a stepped clip
    rectangle, and a single cursor rect hops along the typing positions."""

    def __init__(self, uid, fs=14, hold=6.0):
        self.uid, self.fs, self.hold, self.n = uid, fs, hold, 0
        self.items, self.cur, self.t_end = [], [], 0.0

    @property
    def T(self):
        return self.t_end + self.hold

    def mark(self, t):
        self.t_end = max(self.t_end, t)

    def show(self, inner, on, off=None):
        self.mark(on if off is None else off)

        def f(T):
            if STATIC:
                return "", ("" if off is not None else inner)
            if on <= 0 and off is None:
                return "", inner
            ts, vs = [0], [1 if on <= 0 else 0]
            if on > 0:
                ts.append(on); vs.append(1)
            if off is not None:
                ts.append(off); vs.append(0)
            return "", (f'<g opacity="{vs[0]}">{inner}<animate attributeName="opacity" dur="{T:.2f}s" '
                        f'repeatCount="indefinite" calcMode="discrete" keyTimes="{kt(ts, T)}" '
                        f'values="{";".join(map(str, vs))}"/></g>')
        self.items.append(f)

    def typed(self, x, y, segs, t0, speed, fs=None):
        fs = fs or self.fs
        cw = fs * ADV
        text = "".join(s for _, s in segs)
        n = len(text)
        self.n += 1
        cid = f"{self.uid}{self.n}"
        self.mark(t0 + n * speed)
        self.cur.append((t0, x, y))
        for k in range(1, n + 1):
            self.cur.append((t0 + k * speed, x + k * cw, y))

        def f(T):
            tsp = "".join(f'<tspan class="{c}">{escape(s)}</tspan>' if c else f"<tspan>{escape(s)}</tspan>"
                          for c, s in segs)
            base = (f'<text x="{x:.1f}" y="{y}" font-size="{fs}" textLength="{n * cw:.1f}" '
                    f'lengthAdjust="spacing"')
            if STATIC:
                return "", f"{base}>{tsp}</text>"
            ts = [0] + [t0 + k * speed for k in range(1, n + 1)]
            vs = [0] + [round(k * cw, 1) for k in range(1, n + 1)]
            clip = (f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{y - fs - 2}" width="0" height="{fs + 9}">'
                    f'<animate attributeName="width" dur="{T:.2f}s" repeatCount="indefinite" '
                    f'calcMode="discrete" keyTimes="{kt(ts, T)}" values="{";".join(map(str, vs))}"/>'
                    f'</rect></clipPath>')
            return clip, f'{base} clip-path="url(#{cid})">{tsp}</text>'
        self.items.append(f)
        return t0 + n * speed

    def prompt_line(self, x, y, cmd, t0, speed=0.07):
        cw = self.fs * ADV
        self.show(prompt(x, y, "", self.fs, f' textLength="{16 * cw:.1f}" lengthAdjust="spacing"'), t0)
        self.cur.append((t0, x + 16 * cw, y))
        return self.typed(x + 16 * cw, y, [("w", cmd)], t0 + 0.3, speed)

    def idle_prompt(self, x, y, t0):
        cw = self.fs * ADV
        self.show(prompt(x, y, "", self.fs, f' textLength="{16 * cw:.1f}" lengthAdjust="spacing"'), t0)
        self.cur.append((t0, x + 16 * cw, y))
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
        ts = kt([e[0] for e in out], T)
        xs = ";".join(f"{e[1]:.1f}" for e in out)
        ys = ";".join(f"{e[2] - 0.875 * fs:.1f}" for e in out)
        common = f'dur="{T:.2f}s" repeatCount="indefinite" calcMode="discrete" keyTimes="{ts}"'
        return (f'<rect x="{out[0][1]:.1f}" y="{out[0][2] - 0.875 * fs:.1f}" width="{cw:.1f}" '
                f'height="{1.125 * fs:.1f}" fill="{TEXT}" opacity=".85">'
                f'<animate attributeName="x" {common} values="{xs}"/>'
                f'<animate attributeName="y" {common} values="{ys}"/>'
                f'<animate attributeName="opacity" values=".85;0" keyTimes="0;.5" dur="1.1s" '
                f'calcMode="discrete" repeatCount="indefinite"/></rect>')

    def render(self, w, h, title, extra_defs=""):
        T = self.T
        parts = [it(T) for it in self.items]
        defs = "".join(d for d, _ in parts) + extra_defs
        body = "\n".join(b for _, b in parts) + "\n" + self.cursor_svg(T)
        return window(w, h, title, body, defs)


def line_el(x, y, segs, fs=14):
    tsp = "".join(f'<tspan class="{c}">{escape(s)}</tspan>' if c else f"<tspan>{escape(s)}</tspan>"
                  for c, s in segs)
    return f'<text x="{x}" y="{y}" font-size="{fs}">{tsp}</text>'



# =============================== CONTENT ====================================
NAME = "Ujwal Shettigar"
SUBTITLE = "Computer Science Engineering student"
ROLES = [
    "CSE Student",
    "Full-Stack Developer",
    "C++ / DSA Learner",
    "Linux Enthusiast",
    "AI & Cybersecurity Explorer",
    "Game Development / Graphics Explorer",
]
BOOT = ["Initializing profile...", "Loading projects...", "Loading tech stack...",
        "Fetching GitHub activity..."]
INTERESTS = ["cpp/", "linux/", "fullstack/", "ai/", "cybersecurity/", "graphics/"]
FOCUS = ["C++ + DSA", "Full-stack development", "Linux", "AI / Cybersecurity"]
ENV = [("C++", "dsa · systems"), ("React", "frontend · ui"), ("Node.js", "api · express"),
       ("Linux", "shell · tooling"), ("Supabase", "database · backend"), ("Git", "version control")]
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
    w, h, fs = 720, 246, 16
    cw = fs * ADV
    x0, yrole = 150 + 2 * cw, 196
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

    def anim(attr, events, scale, base=0.0):
        evs = [(0.0, 0)] + events if events[0][0] > 0 else list(events)
        evs.append((total, 0))
        ded, last = [], None
        for tm, v in evs:
            if v != last or tm == total:
                ded.append((tm, v)); last = v
        kts = ";".join(f"{tm / total:.5f}" for tm, _ in ded)
        vs = ";".join(f"{base + v * scale:.1f}" for _, v in ded)
        return (f'<animate attributeName="{attr}" dur="{total:.2f}s" repeatCount="indefinite" '
                f'calcMode="discrete" keyTimes="{kts}" values="{vs}"/>')

    clips, texts = [], []
    for i, s in enumerate(ROLES):
        if STATIC and i:
            continue
        clip = "" if STATIC else (
            f'<clipPath id="c{i}"><rect x="{x0:.1f}" y="{yrole - 18}" width="0" height="26">'
            f'{anim("width", per[i], cw)}</rect></clipPath>')
        clips.append(clip)
        texts.append(
            f'<text x="{x0:.1f}" y="{yrole}" font-size="{fs}" '
            f'{"" if STATIC else f"clip-path=url(#c{i}) "}'
            f'textLength="{len(s) * cw:.1f}" lengthAdjust="spacing">{escape(s)}</text>'.replace(
                "clip-path=url(#c%d)" % i, 'clip-path="url(#c%d)"' % i))
    allev = [e for ev in per for e in ev]
    cursor = "" if STATIC else (
        f'<rect x="{x0:.1f}" y="{yrole - 14}" width="{cw:.1f}" height="18" fill="{TEXT}" opacity=".85">'
        f'{anim("x", allev, cw, x0)}'
        f'<animate attributeName="opacity" values=".85;0" keyTimes="0;.5" dur="1.1s" '
        f'calcMode="discrete" repeatCount="indefinite"/></rect>')

    body = "\n".join([
        f'<text x="{w / 2}" y="90" font-size="36" text-anchor="middle" class="w bold">{escape(NAME)}</text>',
        f'<text x="{w / 2}" y="116" font-size="13" text-anchor="middle" class="d">{escape(SUBTITLE)}</text>',
        f'<path d="M150 138.5H570" stroke="{LINE}"/>',
        prompt(150, 168, "./introduce.sh", 16),
        f'<text x="150" y="{yrole}" font-size="{fs}" class="g">&gt;</text>',
        *texts, cursor,
    ])
    return window(w, h, "ujwal@github: ~", body, "".join(clips))


# ================================== BOOT ====================================
def boot():
    fs, lh = 14, 24
    s = Scene("bt", fs=fs, hold=6.0)
    y = 58
    t = s.prompt_line(24, y, "./boot.sh", 0.3) + 0.5
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
    return s.render(720, y + 22, "ujwal@github: ~/boot.log")


# ================================== ABOUT ===================================
def about():
    fs, lh = 14, 22
    s = Scene("ab", fs=fs, hold=7.0)
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
    ls = []
    for i, d in enumerate(INTERESTS):
        ls += [("b bold", d)] + ([("", "  ")] if i < len(INTERESTS) - 1 else [])
    t, y = block("ls ./interests", [ls], t, y)
    t, y = block("./current_focus", [[("", f)] for f in FOCUS], t, y)
    s.idle_prompt(24, y, t)
    return s.render(720, y + 22, "ujwal@github: ~")


# ============================== ENVIRONMENT =================================
def env():
    fs, lh = 14, 28
    s = Scene("en", fs=fs, hold=7.0)
    y = 58
    t = s.prompt_line(24, y, "stack --active", 0.3) + 0.5
    y += 10
    tx0, tw, seg = 436, 260, 30
    for i, (name, desc) in enumerate(ENV):
        y += lh
        d0 = f"{i * 0.45:.2f}"
        inner = (
            f'<text x="24" y="{y}" font-size="14" class="w bold">{escape(name)}</text>'
            f'<circle cx="124" cy="{y - 5}" r="4" fill="{GREEN}">'
            f'<animate attributeName="opacity" values="1;.3;1" dur="2.4s" begin="{d0}s" repeatCount="indefinite"/></circle>'
            f'<text x="138" y="{y}" font-size="12" class="g">ACTIVE</text>'
            f'<text x="214" y="{y}" font-size="12" class="d">{escape(desc)}</text>'
            f'<path d="M{tx0} {y - 5}H{tx0 + tw}" stroke="{LINE}"/>'
            f'<rect x="{tx0}" y="{y - 6.5}" width="{seg}" height="3" fill="{BLUE}" opacity=".7">'
            f'<animate attributeName="x" values="{tx0};{tx0 + tw - seg};{tx0}" dur="{5 + i * 0.7:.1f}s" '
            f'begin="{d0}s" repeatCount="indefinite"/></rect>'
        )
        s.show(inner, t)
        t += 0.35
    y += lh + 6
    s.idle_prompt(24, y, t + 0.3)
    return s.render(720, y + 22, "ujwal@github: ~")


# ================================== CODE ====================================
def code():
    fs, lh, cx = 14, 22, 60
    s = Scene("cd", fs=fs, hold=7.0)
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
    body_sep = f'<path d="M0 {ysep}.5H720" stroke="{LINE}"/>'
    svg = s.render(720, y + 22, "main.cpp")
    return svg.replace("</svg>", body_sep + "\n</svg>")


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
    w, h = 720, 468
    cx, bw, bh = 360, 150, 44
    sup_x, auth_x = 250, 470
    role_x, rw, rh = [110, 250, 390], 124, 40
    ymain = {"cust": 68, "web": 140, "api": 220}
    ysb, ytrunk, yrole = 310, 366, 418
    ybranch = 266
    marker = (f'<marker id="ah" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="6" markerHeight="6" '
              f'orient="auto"><path d="M0 0L8 4L0 8z" fill="{MUTED}"/></marker>')
    mk = ' marker-end="url(#ah)"'
    ln = lambda d, arrow=False: f'<path d="{d}" stroke="{MUTED}" fill="none"{mk if arrow else ""}/>'

    lines = [
        ln(f"M{cx} 86V117", True),
        ln(f"M{cx} 162V197", True),
        ln(f"M{cx} 242V{ybranch}"),
        ln(f"M{cx} {ybranch}H{sup_x}V287", True),
        ln(f"M{cx} {ybranch}H{auth_x}V287", True),
        ln(f"M{sup_x} 332V{ytrunk}"),
        ln(f"M{role_x[0]} {ytrunk}H{role_x[2]}"),
        *[ln(f"M{rx} {ytrunk}V397", True) for rx in role_x],
    ]

    # packets travel behind the boxes, so they emerge from box edges
    D, speed = 10.0, 120.0
    def packet(path, length, begin, color):
        a, b = begin / D, (begin + length / speed) / D
        return (f'<g><circle r="5" fill="{color}" opacity=".18"/><circle r="2.8" fill="{color}"/>'
                f'<animateMotion dur="{D:.0f}s" repeatCount="indefinite" calcMode="linear" path="{path}" '
                f'keyPoints="0;0;1;1" keyTimes="0;{a:.4f};{b:.4f};1"/></g>')

    trunk = lambda rx: f"M{cx} 68V{ybranch}H{sup_x}V{ytrunk}H{rx}V{yrole}"
    pk = []
    if not STATIC:
        for rx, begin in zip(role_x, [1.2, 0.0, 2.4]):
            L = (ybranch - 68) + abs(cx - sup_x) + (ytrunk - ybranch) + abs(sup_x - rx) + (yrole - ytrunk)
            pk.append(packet(trunk(rx), L, begin, BLUE))
        pk.append(packet(f"M{cx} 68V{ybranch}H{auth_x}V{ysb}", (ybranch - 68) + abs(auth_x - cx) + (ysb - ybranch), 0.5, BLUE))
        pk.append(packet(f"M{sup_x} {ysb}V{ybranch}H{cx}V68", (ysb - ybranch) + abs(cx - sup_x) + (ybranch - 68), 6.2, GREEN))

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
    boxes += box(cx, ymain["cust"], bw, 36, "Customer", None, 13)
    boxes += box(cx, ymain["web"], bw, bh, "React / Vite", "frontend")
    boxes += box(cx, ymain["api"], bw, bh, "Node / Express", "api server")
    boxes += box(sup_x, ysb, 150, bh, "Supabase", "database")
    boxes += box(auth_x, ysb, 150, bh, "Auth", "roles · sessions")
    for rx, name in zip(role_x, ["Picker", "Delivery Partner", "Admin"]):
        boxes += box(rx, yrole, rw, rh, name, None, 11.5)

    dim = lambda x, y, t: f'<text x="{x}" y="{y}" font-size="10.5" class="d">{escape(t)}</text>'
    labels = [
        dim(24, ymain["cust"] + 4, "client"), dim(24, ymain["web"] + 4, "web"),
        dim(24, ymain["api"] + 4, "server"), dim(24, ysb + 4, "data"),
        dim(48, 392, "role dashboards"),
        dim(372, 106, "browse / order"), dim(372, 184, "API request"),
        dim(262, 282, "query"), dim(482, 282, "verify"),
    ]
    legend = (f'<circle cx="540" cy="414" r="3" fill="{BLUE}"/>{dim(552, 418, "request")}'
              f'<circle cx="540" cy="434" r="3" fill="{GREEN}"/>{dim(552, 438, "response")}')

    body = "\n".join(lines + pk + boxes + labels + [legend])
    return window(w, h, "hyperlocal-grocery-platform / request flow", body, marker)



if __name__ == "__main__":
    for name, fn in [("hero", hero), ("boot", boot), ("about", about), ("architecture", architecture),
                     ("env", env), ("code", code), ("learning", learning)]:
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print("wrote", OUT / f"{name}.svg")
