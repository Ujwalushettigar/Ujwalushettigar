#!/usr/bin/env python3
"""Build assets/contributions.svg from your real GitHub contribution calendar.

Data source, in order:
  1. GraphQL API (needs GH_TOKEN) - official, stable.
  2. Public contributions page   - no token, parses GitHub's HTML (can break).
Standard library only.
"""
import base64
import datetime as dt
import json
import os
import pathlib
import re
import urllib.request
from xml.sax.saxutils import escape

LOGIN = os.environ.get("PROFILE_LOGIN", "Ujwalushettigar")
TOKEN = os.environ.get("GH_TOKEN", "")
ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "assets" / "contributions.svg"

BG, BAR, LINE, TEXT, DIM, WHITE = "#0d1117", "#161b22", "#30363d", "#c9d1d9", "#8b949e", "#e6edf3"
LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
STACK = "'Roboto Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
UA = {"User-Agent": "profile-readme-builder"}

QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
ENUM = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def from_graphql():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={**UA, "Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    cal = json.load(urllib.request.urlopen(req, timeout=30))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [(d["date"], d["contributionCount"], ENUM[d["contributionLevel"]])
            for w in cal["weeks"] for d in w["contributionDays"]]
    return days


def from_html():
    req = urllib.request.Request(f"https://github.com/users/{LOGIN}/contributions", headers=UA)
    html = urllib.request.urlopen(req, timeout=30).read().decode()
    tips = {m.group(1): m.group(2) for m in
            re.finditer(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)<', html)}
    days = []
    for m in re.finditer(r'<td[^>]*data-date="([^"]+)"[^>]*\bid="([^"]+)"[^>]*data-level="(\d)"', html):
        n = re.match(r"(\d+) contribution", tips.get(m.group(2), "").strip())
        days.append((m.group(1), int(n.group(1)) if n else 0, int(m.group(3))))
    if not days:
        raise RuntimeError("no contribution cells found in HTML")
    return days


def load():
    if TOKEN:
        try:
            return from_graphql()
        except Exception as e:  # fall back to public page
            print("graphql failed, using HTML fallback:", e)
    return from_html()


def b64(name):
    return base64.b64encode((FONTS / name).read_bytes()).decode()


def build(days):
    days = sorted(set(days))
    first = dt.date.fromisoformat(days[0][0])
    offset = (first.weekday() + 1) % 7            # Sunday-based row of the first day
    n_weeks = (offset + len(days) + 6) // 7
    w, pad_l, pad_r, top = 720, 40, 16, 64
    pitch = (w - pad_l - pad_r) / n_weeks
    cell = round(pitch - 2.4, 2)
    total = sum(c for _, c, _ in days)

    cells, months, last_m, last_w = [], [], None, -9
    for i, (d, count, lvl) in enumerate(days):
        col, row = (i + offset) // 7, (i + offset) % 7
        x, y = pad_l + col * pitch, top + row * pitch
        cls = ' class="c t"' if i == len(days) - 1 else ' class="c"'
        cells.append(f'<rect{cls} x="{x:.2f}" y="{y:.2f}" width="{cell}" height="{cell}" rx="2" '
                     f'fill="{LEVELS[lvl]}" style="animation-delay:{col*14}ms"/>')
        dd = dt.date.fromisoformat(d)
        if dd.day <= 7 and row == 0 and dd.month != last_m and col - last_w >= 3 and x < w - 44:
            months.append(f'<text x="{x:.1f}" y="{top-8}" font-size="10.5" class="d">{dd.strftime("%b")}</text>')
            last_m, last_w = dd.month, col
    side = "".join(f'<text x="12" y="{top + r*pitch + cell - 1:.1f}" font-size="10.5" class="d">{n}</text>'
                   for r, n in ((1, "Mon"), (3, "Wed"), (5, "Fri")))

    h = int(top + 7 * pitch + 36)
    fy = h - 14
    lx = w - pad_r - 5 * 13 - 30 - 34
    legend = (f'<text x="{lx}" y="{fy}" font-size="10.5" class="d" text-anchor="end">Less</text>' +
              "".join(f'<rect x="{lx+8+i*13}" y="{fy-9}" width="10" height="10" rx="2" fill="{c}"/>'
                      for i, c in enumerate(LEVELS)) +
              f'<text x="{lx+8+5*13+4}" y="{fy}" font-size="10.5" class="d">More</text>')
    summary = (f'<text x="{pad_l}" y="{fy}" font-size="12"><tspan class="w bold">{total}</tspan>'
               f'<tspan class="d"> contributions in the last year</tspan></text>')
    label = f"{total} GitHub contributions in the last year"

    style = (
        f"@font-face{{font-family:'Roboto Mono';font-weight:400;src:url(data:font/woff2;base64,{b64('RobotoMono-400.woff2')}) format('woff2')}}"
        f"@font-face{{font-family:'Roboto Mono';font-weight:700;src:url(data:font/woff2;base64,{b64('RobotoMono-700.woff2')}) format('woff2')}}"
        f"text{{font-family:{STACK};fill:{TEXT};white-space:pre}}.d{{fill:{DIM}}}.w{{fill:{WHITE}}}.bold{{font-weight:700}}"
        "@keyframes in{from{opacity:0}}@keyframes pulse{50%{opacity:.35}}"
        ".c{animation:in .5s ease-out backwards}"
        ".t{animation:in .5s ease-out backwards,pulse 3.2s ease-in-out 2.4s infinite}"
        "@media (prefers-reduced-motion:reduce){.c,.t{animation:none}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{label}">\n<title>{label}</title>\n'
        f"<defs><style>{style}</style></defs>\n"
        f'<rect width="{w}" height="{h}" rx="4" fill="{BG}"/>\n'
        f'<path d="M0 4a4 4 0 0 1 4-4H{w-4}a4 4 0 0 1 4 4V28H0z" fill="{BAR}"/>\n'
        f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="4" fill="none" stroke="{LINE}"/>\n'
        f'<path d="M0 28.5H{w}" stroke="{LINE}"/>\n'
        f'<text x="14" y="18" font-size="12" class="d">ujwal@github: ~/contributions</text>\n'
        + "\n".join(months) + side + "\n" + "\n".join(cells) + "\n" + summary + legend + "\n</svg>\n")


if __name__ == "__main__":
    svg = build(load())
    OUT.write_text(svg, encoding="utf-8")
    print("wrote", OUT, f"({len(svg)//1024} KB)")
