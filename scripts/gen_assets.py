#!/usr/bin/env python3
"""Render every visual on the profile as self-hosted SVG cards.

  hero.svg / hero-dark.svg          Asymmetric split studio hero
  domains.svg / domains-dark.svg    2×2 architectural bento grid
  projects.svg / projects-dark.svg  2×3 featured open-source workbench
  stack.svg / stack-dark.svg        Refined engineering stack
  activity.svg / activity-dark.svg  52-week cadence & language share

Each card has a light and a dark variant matched 1:1 to qilaidav.com's
Apple White & Pro Dark design system. Live cards read GitHub data and are
refreshed weekly by .github/workflows/charts.yml so the README never
embeds a number that goes stale.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

USER = "qilaidev"
WEBSITE = "qilaidav.com"
TELEGRAM = "@BD8888 · @AIKB8"
EMAIL = "hello@qilaidav.com"

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
ICONS = ROOT / "scripts" / "icons"

W = 880
PAD = 28

# Font stacks — CSS inside <style> uses single-quoted names to avoid XML entity issues
SANS = (
    "-apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Text', "
    "'PingFang SC', 'Hiragino Sans GB', 'Noto Sans CJK SC', sans-serif"
)
MONO = (
    "'JetBrains Mono', 'SFMono-Regular', ui-monospace, Menlo, Consolas, monospace"
)

# ── Design system tokens matched 1:1 to qilaidav.com ───────────────────

THEMES = {
    "light": {
        "canvas": "#F5F7FA",
        "paper": "#FFFFFF",
        "box": "#F5F7FA",
        "box_alt": "#F5F7FA",
        "border": "#E2E6EE",
        "rule": "#ECEFF4",
        "ink": "#111827",
        "ink2": "#4B5565",
        "muted": "#6B7487",
        "accent": "#0055B3",
        "positive": "#16A34A",
        "amber": "#B45309",
        "bars": ["#E5E9F0", "#B8D4F8", "#6AA6F8", "#1E70D6", "#0055B3"],
    },
    "dark": {
        "canvas": "#0B0D14",
        "paper": "#0B0D14",
        "box": "#11141C",
        "box_alt": "#161A24",
        "border": "#222736",
        "rule": "#1A1E28",
        "ink": "#EEF0F5",
        "ink2": "#A3A9B8",
        "muted": "#7A8296",
        "accent": "#4796FF",
        "positive": "#4CC38A",
        "amber": "#F59E0B",
        "bars": ["#1A1E28", "#17345E", "#235396", "#3578D4", "#4796FF"],
    },
}

LANG_COLORS = {
    "Python": "#3572A5", "TypeScript": "#3178c6", "JavaScript": "#f1e05a",
    "Rust": "#dea584", "Swift": "#F05138", "Shell": "#89e051", "Go": "#00ADD8",
    "Batchfile": "#C1F12E", "HTML": "#e34c26", "CSS": "#663399", "C": "#555555",
    "C++": "#f34b7d", "Java": "#b07219", "Objective-C++": "#6866fb",
    "PowerShell": "#012456", "Dockerfile": "#384d54", "Makefile": "#427819",
    "PLpgSQL": "#336790", "Vue": "#41b883", "Kotlin": "#A97BFF", "Ruby": "#701516",
}

# ── Featured projects (pulled live from API) ────────────────────────────

PROJECTS = [
    ("cleanplate",
     "AI 视频水印检测、ComfyUI/FFmpeg 时序修复与视觉质检流水线",
     ["FastAPI", "ComfyUI", "FFmpeg"]),
    ("social-copilot",
     "Telegram / WhatsApp / Slack Web 本地优先 BYOK 强拟人回复扩展",
     ["TypeScript", "MV3"]),
    ("PromptPanel",
     "macOS 14+ 原生全局热键多模型提示词与上下文工作台",
     ["Swift", "SQLite FTS5"]),
    ("wechat-localmind",
     "微信本地群聊 SQLCipher 只读原子快照提取与 MCP Server",
     ["Python", "MCP"]),
    ("social-cleaner",
     "Bilibili / X 社媒历史资产合规预检与审计清理 CLI",
     ["Python", "Playwright"]),
    ("anyreality-resi-stack",
     "无面板多路径 sing-box 住宅代理与十阶段选择性 WARP 运维栈",
     ["Shell", "Python", "systemd"]),
]

# ── Stack lanes (domain-centric) ────────────────────────────────────────

STACK = [
    ("Growth & SEO/GEO", [
        ("Headless DOM Probe", None, "#0055B3"), ("Schema.org / JSON-LD", None, "#16A34A"),
        ("hreflang Loop", None, "#16A34A"), ("IndexNow / llms.txt", None, "#0055B3"),
        ("SERP 160u Guard", None, "#0055B3"), ("Negative Testing", None, "#B45309"),
    ]),
    ("Persona & Agent AI", [
        ("Telegram MTProto", "telegram", "#26A5E4"), ("OpenAI API", "openai", "#111827"),
        ("MCP", "modelcontextprotocol", "#111827"), ("Playwright / CDP", None, "#2EAD33"),
        ("Anti-Detect FSM", None, "#0055B3"), ("Structured Output", None, "#0055B3"),
    ]),
    ("Video & Multimodal", [
        ("FastAPI", "fastapi", "#009688"), ("ComfyUI", None, "#0055B3"),
        ("FFmpeg", None, "#007808"), ("Playwright", None, "#2EAD33"),
    ]),
    ("Languages", [
        ("TypeScript", "typescript", "#3178C6"), ("Python", "python", "#3776AB"),
        ("JavaScript", "javascript", "#C9B300"), ("HTML", None, "#E34C26"),
        ("Swift", "swift", "#F05138"), ("Bash", "gnubash", "#4EAA25"),
    ]),
    ("App & Web", [
        ("React", "react", "#149ECA"), ("Electron", "electron", "#47848F"),
        ("Vite", "vite", "#646CFF"), ("Tailwind CSS", "tailwindcss", "#06B6D4"),
        ("shadcn/ui", "shadcnui", "#111827"), ("SwiftUI", "swift", "#F05138"),
    ]),
    ("Backend & Data", [
        ("FastAPI", "fastapi", "#009688"), ("Node.js", "nodedotjs", "#5FA04E"),
        ("PostgreSQL", "postgresql", "#4169E1"), ("Redis", "redis", "#FF4438"),
        ("SQLite", "sqlite", "#003B57"), ("Prisma", "prisma", "#2D3748"),
    ]),
    ("Anti-Detect & Infra", [
        ("Cloudflare Edge", "cloudflare", "#F38020"), ("Nginx", "nginx", "#009639"),
        ("Linux / systemd", "linux", "#E5A000"), ("Docker", "docker", "#2496ED"),
        ("GitHub Actions", "githubactions", "#2088FF"), ("Git", "git", "#F05032"),
    ]),
]

# ── Domain cards for 2×2 bento ──────────────────────────────────────────

DOMAINS = [
    {
        "title_zh": "增长型 AI 与跨平台智慧投流",
        "title_en": "Growth AI & Smart Ad Ops",
        "route": "/ads/",
        "desc": "X / FB / TG / Google 政策预检、外层素材与落地页 1:1 穿透、5m 分时控盘止损",
        "schematic": "bars_funnel",
    },
    {
        "title_zh": "强拟人交互 AI 与电报中枢",
        "title_en": "Human-Grade Persona AI",
        "route": "/oash/",
        "desc": "24h 作息节律曲线、阅读/打字字节延迟、群私聊双轨记忆与 OASH 多源编排",
        "schematic": "circadian",
    },
    {
        "title_zh": "AI 视频生成与多模态管线",
        "title_en": "AI Video & Multimodal",
        "route": "/workspace/",
        "desc": "AI 视频生产、动态水印检测、ComfyUI/FFmpeg 时序修复与视觉 QA",
        "schematic": "timeline",
    },
    {
        "title_zh": "技术 SEO / GEO 与确定性底座",
        "title_en": "Technical SEO, GEO & Infra",
        "route": "/seo/",
        "desc": "无头 DOM 可见字符探测、JSON-LD / llms.txt 闭环、ROM 级防关联与三库底座",
        "schematic": "protocol_dom",
    },
]

# ── Probe rows for hero telemetry card ──────────────────────────────────

PROBE_ROWS = [
    ("Growth & Smart Ad Ops", "LIVE"),
    ("Human-Grade Persona Engine", "PASS"),
    ("AI Video & Multimodal", "LIVE"),
    ("Technical SEO & GEO Audit", "PASS"),
]


# ================================================================ data layer

def get_token() -> str | None:
    """Check GITHUB_TOKEN / GH_TOKEN first (CI), then fallback to gh CLI."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        token = os.popen("gh auth token 2>/dev/null").read().strip()
    except Exception:  # noqa: BLE001
        pass
    return token or None


def api(path: str, body: dict | None = None):
    url = path if path.startswith("http") else f"https://api.github.com{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", f"{USER}-profile-assets")
    if data:
        req.add_header("Content-Type", "application/json")
    token = get_token()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else None


def fetch_contributions() -> tuple[int, list[int]] | None:
    if not get_token():
        return None
    query = """query { user(login: "%s") { contributionsCollection { contributionCalendar {
      totalContributions weeks { contributionDays { contributionCount } } } } } }""" % USER
    try:
        cal = api("https://api.github.com/graphql", {"query": query})["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except Exception as exc:  # noqa: BLE001
        print(f"  ! contributions via GraphQL failed: {exc}", file=sys.stderr)
        return None
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    return cal["totalContributions"], weekly[-52:]


def collect() -> dict:
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner") or []
    # Filter: exclude forks, archived, AND private repos
    owned = [r for r in repos if not r.get("fork") and not r.get("archived") and not r.get("private")]
    by_name = {r["name"]: r for r in owned}
    stars = sum(r.get("stargazers_count", 0) for r in owned)

    totals: dict[str, int] = {}

    def fetch_lang(repo):
        try:
            return api(f"/repos/{USER}/{repo['name']}/languages")
        except Exception:  # noqa: BLE001
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for langs in pool.map(fetch_lang, owned):
            for name, size in (langs or {}).items():
                totals[name] = totals.get(name, 0) + size

    got = fetch_contributions()
    contribs, weeks = got if got else (0, [0] * 52)

    projects = []
    for name, blurb, tags in PROJECTS:
        r = by_name.get(name)
        if not r:
            print(f"  ! project {name} not found among owned repos", file=sys.stderr)
            continue
        projects.append({
            "name": name, "blurb": blurb, "tags": tags,
            "lang": r.get("language") or "Python",
            "stars": r.get("stargazers_count", 0),
        })

    print(f"  {len(owned)} repos · {stars} stars · {len(totals)} languages · {contribs} contributions/52w · {len(projects)} project cards")
    return {
        "repos": len(owned), "stars": stars, "langs": totals,
        "weeks": weeks, "contribs": contribs, "projects": projects,
    }


# ============================================================ svg plumbing

def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tw(text: str, size: float, mono: bool = False) -> float:
    """Rough advance width: CJK = 1em, ASCII ≈ 0.6em (mono) / 0.52em (sans)."""
    ratio = 0.6 if mono else 0.52
    return sum(size if ord(ch) > 0x2E7F else size * ratio for ch in text)


def wrap(text: str, size: float, width: float, max_lines: int) -> list[str]:
    tokens = re.findall(r"[^\x00-\u2e7f]|[\x00-\u2e7f]+?(?=\s|[^\x00-\u2e7f]|$)\s*", text)
    lines: list[str] = []
    cur = ""
    for tok in tokens:
        if cur and tw(cur + tok.rstrip(), size) > width:
            lines.append(cur.rstrip())
            cur = tok.lstrip()
        else:
            cur += tok
    if cur.strip():
        lines.append(cur.rstrip())
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip()[:-1] + "…"
    return lines


def svg_open(width: int, height: int, c: dict) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        "<style>",
        f"text{{font-family:{SANS};font-variant-numeric:tabular-nums}}",
        f".mono{{font-family:{MONO}}}",
        f".section-head{{font-size:13px;font-weight:600;fill:{c['ink']}}}",
        f".section-sub{{font-family:{MONO};font-size:11px;font-weight:400;fill:{c['muted']}}}",
        f".body{{font-size:12px;fill:{c['muted']};line-height:1.5}}",
        f".ink{{font-size:12px;fill:{c['ink']}}}",
        f".label{{font-family:{MONO};font-size:10px;font-weight:500;fill:{c['muted']}}}",
        f".num{{font-size:22px;font-weight:600;letter-spacing:-0.4px}}",
        f".chip{{font-family:{MONO};font-size:11px;font-weight:500;fill:{c['ink']}}}",
        f".tag{{font-family:{MONO};font-size:9.5px;font-weight:500}}",
        "</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{c["paper"]}" stroke="{c["border"]}"/>',
    ]


_icon_cache: dict[str, str] = {}


def icon_path(slug: str) -> str | None:
    if slug in _icon_cache:
        return _icon_cache[slug]
    f = ICONS / f"{slug}.svg"
    if not f.exists():
        return None
    m = re.search(r'<path[^>]*\sd="([^"]+)"', f.read_text(encoding="utf-8"))
    _icon_cache[slug] = m.group(1) if m else None
    return _icon_cache[slug]


def brand_colour(colour: str, theme: str, c: dict) -> str:
    """Make dark-on-dark icons visible."""
    if theme == "dark":
        r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
        if 0.299 * r + 0.587 * g + 0.114 * b < 70:
            return c["ink"]
    return colour


CHIP_H = 28
CHIP_FS = 11


def chip_w(label: str, with_icon: bool) -> float:
    return (32 if with_icon else 22) + tw(label, CHIP_FS, mono=True) + 10


def chip(x: float, y: float, label: str, slug: str | None, colour: str, c: dict) -> str:
    d = icon_path(slug) if slug else None
    w = chip_w(label, d is not None)
    out = [
        f'<g><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{CHIP_H}" rx="6" '
        f'fill="{c["box"]}" stroke="{c["border"]}"/>'
    ]
    if d:
        out.append(
            f'<g transform="translate({x + 8:.1f},{y + 6:.1f}) scale(0.6667)">'
            f'<path d="{d}" fill="{colour}"/></g>'
        )
        tx = x + 32
    else:
        out.append(f'<circle cx="{x + 11:.1f}" cy="{y + CHIP_H / 2:.1f}" r="3" fill="{colour}"/>')
        tx = x + 22
    out.append(f'<text x="{tx:.1f}" y="{y + CHIP_H / 2 + 4:.1f}" class="chip">{esc(label)}</text></g>')
    return "".join(out)


def tag(x: float, y: float, label: str, colour: str, c: dict) -> tuple[str, float]:
    w = tw(label, 9.5, mono=True) + 14
    fill_op = "0.06" if c["paper"] == "#FFFFFF" else "0.12"
    stroke_op = "0.28" if c["paper"] == "#FFFFFF" else "0.36"
    s = (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="18" rx="4" '
        f'fill="{colour}" fill-opacity="{fill_op}" stroke="{colour}" stroke-opacity="{stroke_op}"/>'
        f'<text x="{x + 7:.1f}" y="{y + 12.5:.1f}" class="tag" fill="{colour}">{esc(label)}</text>'
    )
    return s, w


# ================================================================== hero

HERO_H = 268


def render_hero(theme: str, d: dict) -> str:
    c = THEMES[theme]
    out = svg_open(W, HERO_H, c)

    # ── Left column: brand + manifesto (x=32..496) ──
    lx = PAD + 4  # 32
    out.append(f'<text x="{lx}" y="52" font-size="32px" font-weight="600" fill="{c["ink"]}">qilai</text>')
    # "qilai" at 32px sans-serif (narrow i/l) renders ~72px wide (ends ~x=104)
    dot_x = lx + 84  # 116 (~12px after "qilai")
    out.append(f'<circle cx="{dot_x}" cy="43" r="2.5" fill="{c["accent"]}"/>')
    out.append(f'<text x="{dot_x + 12}" y="52" class="mono" font-size="13px" font-weight="500" fill="{c["accent"]}">{WEBSITE}</text>')

    # Role headline
    role = "增长型 AI · 强拟人交互 · AI 视频生成 · 技术 SEO/GEO"
    out.append(f'<text x="{lx}" y="80" font-size="12.5px" font-weight="500" fill="{c["ink2"]}">{esc(role)}</text>')

    # 2-line manifesto
    m1 = "把 AI 增长投流、多模态视频管线、强拟人交互状态机"
    m2 = "与高信噪比 SEO/GEO 诊断，锻造成长期自运转的确定性系统"
    out.append(f'<text x="{lx}" y="104" font-size="11.5px" fill="{c["muted"]}">{esc(m1)}</text>')
    out.append(f'<text x="{lx}" y="120" font-size="11.5px" fill="{c["muted"]}">{esc(m2)}</text>')

    # 4 domain pills
    pills = ["Growth AI", "AI Video Pipeline", "Human-Grade Persona", "Technical SEO &amp; GEO"]
    px, py = float(lx), 140.0
    for p in pills:
        raw_p = p.replace("&amp;", "&")
        pw = tw(raw_p, 9.5, mono=True) + 14
        fill_op = "0.06" if theme == "light" else "0.12"
        stroke_op = "0.22" if theme == "light" else "0.32"
        out.append(
            f'<rect x="{px:.1f}" y="{py:.1f}" width="{pw:.1f}" height="20" rx="4" '
            f'fill="{c["accent"]}" fill-opacity="{fill_op}" stroke="{c["accent"]}" stroke-opacity="{stroke_op}"/>'
            f'<text x="{px + 7:.1f}" y="{py + 13.5:.1f}" class="tag" fill="{c["accent"]}">{p}</text>'
        )
        px += pw + 6

    # Contact strip
    contacts = [
        (WEBSITE, c["accent"]), (TELEGRAM, c["ink2"]), (EMAIL, c["accent"]),
    ]
    cy_base = 184
    for i, (txt, col) in enumerate(contacts):
        out.append(f'<text x="{lx}" y="{cy_base + i * 18}" class="mono" font-size="11px" font-weight="400" fill="{col}">{esc(txt)}</text>')

    # ── Separator ──
    out.append(f'<line x1="508" y1="28" x2="508" y2="{HERO_H - 24}" stroke="{c["rule"]}"/>')

    # ── Right column: Telemetry probe card (x=520..848) ──
    rx = 528
    rw = W - PAD - rx  # 324
    card_y = 28
    card_h = HERO_H - 52
    out.append(
        f'<rect x="{rx}" y="{card_y}" width="{rw}" height="{card_h}" rx="8" '
        f'fill="{c["box"]}" stroke="{c["border"]}"/>'
    )

    # Probe header
    out.append(f'<text x="{rx + 12}" y="{card_y + 20}" class="mono" font-size="10.5px" font-weight="500" fill="{c["ink2"]}">qilai-studio · live telemetry</text>')
    # VERIFIED badge
    vx = rx + rw - 12
    out.append(
        f'<rect x="{vx - 56:.0f}" y="{card_y + 8}" width="52" height="18" rx="4" '
        f'fill="{c["positive"]}" fill-opacity="0.1" stroke="{c["positive"]}" stroke-opacity="0.3"/>'
        f'<text x="{vx - 30:.0f}" y="{card_y + 20}" class="mono" font-size="9px" font-weight="500" '
        f'fill="{c["positive"]}" text-anchor="middle">VERIFIED</text>'
    )
    out.append(f'<line x1="{rx + 12}" y1="{card_y + 30}" x2="{rx + rw - 12}" y2="{card_y + 30}" stroke="{c["rule"]}"/>')

    # 4 probe rows
    probe_y = card_y + 40
    for label, status in PROBE_ROWS:
        stat_col = c["positive"] if status == "PASS" else c["accent"]
        out.append(f'<text x="{rx + 16}" y="{probe_y + 12}" font-size="11px" font-weight="500" fill="{c["ink"]}">{esc(label)}</text>')
        # status badge
        sw = tw(status, 9, mono=True) + 12
        sx = rx + rw - 16 - sw
        out.append(
            f'<rect x="{sx:.1f}" y="{probe_y + 1}" width="{sw:.1f}" height="16" rx="4" '
            f'fill="{stat_col}" fill-opacity="0.1" stroke="{stat_col}" stroke-opacity="0.28"/>'
            f'<text x="{sx + sw / 2:.1f}" y="{probe_y + 12}" class="mono" font-size="9px" font-weight="500" '
            f'fill="{stat_col}" text-anchor="middle">{status}</text>'
        )
        probe_y += 28

    # Bottom metric strip
    out.append(f'<line x1="{rx + 12}" y1="{probe_y + 4}" x2="{rx + rw - 12}" y2="{probe_y + 4}" stroke="{c["rule"]}"/>')
    metrics = [
        (f'{d["repos"]}', "Public repos"),
        (f'{d["contribs"]:,}', "52w commits"),
        (f'{len(d["langs"])}', "Languages"),
        ("204", "Field notes"),
    ]
    mx = rx + 16
    my = probe_y + 14
    for val, lbl in metrics:
        out.append(f'<text x="{mx}" y="{my + 12}" class="mono" font-size="14px" font-weight="600" fill="{c["ink"]}">{esc(val)}</text>')
        out.append(f'<text x="{mx}" y="{my + 26}" class="mono" font-size="9px" font-weight="400" fill="{c["muted"]}">{esc(lbl)}</text>')
        mx += 76

    out.append("</svg>")
    return "\n".join(out)


# ================================================================ domains

DOMAINS_H = 356


def _mini_schematic(kind: str, x: float, y: float, w: float, c: dict) -> list[str]:
    """Draw a minimal vector schematic inside a domain card."""
    out: list[str] = []
    mid = x + w / 2
    acc = c["accent"]
    pos = c["positive"]
    muted = c["muted"]

    if kind == "bars_funnel":
        # Mini bar chart + funnel arrow
        bx = x + 4
        bars = [24, 36, 28, 42, 32]
        for i, h in enumerate(bars):
            bh = h * 0.5
            out.append(f'<rect x="{bx + i * 14:.0f}" y="{y + 28 - bh:.1f}" width="10" height="{bh:.1f}" rx="2" fill="{acc}" fill-opacity="{0.2 + i * 0.15:.2f}"/>')
        # funnel arrow
        fx = bx + 80
        out.append(f'<path d="M{fx},{y + 6} L{fx + 16},{y + 14} L{fx},{y + 22}" fill="none" stroke="{acc}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>')

    elif kind == "circadian":
        # Bezier circadian curve
        out.append(
            f'<path d="M{x + 4},{y + 22} C{x + 20},{y + 4} {x + 40},{y + 4} {x + 56},{y + 16} '
            f'S{x + 80},{y + 28} {x + 96},{y + 12}" fill="none" stroke="{acc}" stroke-width="1.5" stroke-linecap="round"/>'
        )
        # Two memory nodes
        out.append(f'<circle cx="{x + 36}" cy="{y + 8}" r="3" fill="{pos}" fill-opacity="0.5"/>')
        out.append(f'<circle cx="{x + 76}" cy="{y + 24}" r="3" fill="{acc}" fill-opacity="0.5"/>')

    elif kind == "timeline":
        # 3-frame video timeline
        for i in range(3):
            fx = x + 4 + i * 34
            fy = y + 4
            out.append(f'<rect x="{fx}" y="{fy}" width="28" height="20" rx="3" fill="{c["box_alt"]}" stroke="{c["border"]}"/>')
            if i == 1:
                # QA gate marker
                out.append(f'<rect x="{fx + 8}" y="{fy + 6}" width="12" height="8" rx="2" fill="{pos}" fill-opacity="0.3"/>')
        # Arrow connectors
        for i in range(2):
            ax = x + 4 + (i + 1) * 34 - 4
            out.append(f'<line x1="{ax - 2}" y1="{y + 14}" x2="{ax + 2}" y2="{y + 14}" stroke="{muted}" stroke-width="1"/>')

    elif kind == "protocol_dom":
        # Protocol -> DOM -> GEO chain
        nodes = ["P", "D", "G"]
        for i, n in enumerate(nodes):
            nx = x + 8 + i * 36
            ny = y + 6
            out.append(f'<rect x="{nx}" y="{ny}" width="24" height="18" rx="4" fill="{c["box_alt"]}" stroke="{c["border"]}"/>')
            out.append(f'<text x="{nx + 12}" y="{ny + 13}" class="mono" font-size="9px" font-weight="500" fill="{acc}" text-anchor="middle">{n}</text>')
            if i < 2:
                out.append(f'<line x1="{nx + 26}" y1="{ny + 9}" x2="{nx + 34}" y2="{ny + 9}" stroke="{muted}" stroke-width="1" stroke-dasharray="2,2"/>')

    return out


def render_domains(theme: str) -> str:
    c = THEMES[theme]
    out = svg_open(W, DOMAINS_H, c)

    # Header
    out.append(f'<text x="{PAD}" y="28" class="section-head">Core Domains · 四大核心方向</text>')
    out.append(f'<text x="{W - PAD}" y="28" class="section-sub" text-anchor="end">{WEBSITE}</text>')
    out.append(f'<line x1="{PAD}" y1="40" x2="{W - PAD}" y2="40" stroke="{c["rule"]}"/>')

    # 2×2 grid
    card_w = (W - PAD * 2 - 16) // 2  # 404
    card_h = 140
    gap = 16
    grid_y = 52

    for i, dom in enumerate(DOMAINS):
        col = i % 2
        row = i // 2
        cx = PAD + col * (card_w + gap)
        cy = grid_y + row * (card_h + gap)

        out.append(
            f'<rect x="{cx}" y="{cy}" width="{card_w}" height="{card_h}" rx="8" '
            f'fill="{c["box"]}" stroke="{c["border"]}"/>'
        )

        # Mini schematic (top-right of card)
        schem_x = cx + card_w - 112
        schem_y = cy + 8
        out.extend(_mini_schematic(dom["schematic"], schem_x, schem_y, 100, c))

        # Title
        tx = cx + 16
        ty_zh = cy + 28
        out.append(f'<text x="{tx}" y="{ty_zh}" font-size="12.5px" font-weight="600" fill="{c["ink"]}">{esc(dom["title_zh"])}</text>')
        out.append(f'<text x="{tx}" y="{ty_zh + 18}" class="mono" font-size="10px" font-weight="400" fill="{c["muted"]}">{esc(dom["title_en"])}</text>')

        # 2-line summary
        desc_lines = wrap(dom["desc"], 11, card_w - 32, 2)
        for j, line in enumerate(desc_lines):
            out.append(f'<text x="{tx}" y="{ty_zh + 42 + j * 16}" font-size="11px" fill="{c["muted"]}">{esc(line)}</text>')

        # Route badge
        route_y = cy + card_h - 28
        rs, rw_tag = tag(tx, route_y, dom["route"], c["accent"], c)
        out.append(rs)

    out.append("</svg>")
    return "\n".join(out)


# ================================================================ projects

PROJ_H = 420
PROJ_CARD_W = (W - PAD * 2 - 16) // 2  # 404
PROJ_CARD_H = 112


def render_projects(theme: str, d: dict) -> str:
    c = THEMES[theme]
    projects = d["projects"]
    rows_needed = (len(projects) + 1) // 2
    height = 52 + rows_needed * (PROJ_CARD_H + 12) + 8
    out = svg_open(W, height, c)

    # Header
    out.append(f'<text x="{PAD}" y="28" class="section-head">Open-Source Workbench · 代表性开源矩阵</text>')
    out.append(f'<text x="{W - PAD}" y="28" class="section-sub" text-anchor="end">github.com/qilaidev</text>')
    out.append(f'<line x1="{PAD}" y1="40" x2="{W - PAD}" y2="40" stroke="{c["rule"]}"/>')

    grid_y = 52
    for i, p in enumerate(projects):
        col = i % 2
        row = i // 2
        cx = PAD + col * (PROJ_CARD_W + 16)
        cy = grid_y + row * (PROJ_CARD_H + 12)

        lang_col = LANG_COLORS.get(p["lang"], c["muted"])

        out.append(
            f'<rect x="{cx}" y="{cy}" width="{PROJ_CARD_W}" height="{PROJ_CARD_H}" rx="8" '
            f'fill="{c["box"]}" stroke="{c["border"]}"/>'
        )
        # Top color accent bar
        out.append(
            f'<rect x="{cx}" y="{cy}" width="{PROJ_CARD_W}" height="3" rx="1.5" fill="{lang_col}"/>'
        )

        # Repo name
        tx = cx + 16
        out.append(f'<text x="{tx}" y="{cy + 26}" class="mono" font-size="13px" font-weight="600" fill="{c["accent"]}">{esc(p["name"])}</text>')

        # Stars & language
        lang_label = p["lang"]
        right_x = cx + PROJ_CARD_W - 16
        if p["stars"]:
            star_str = f'\u2605 {p["stars"]:,}'
            out.append(f'<text x="{right_x}" y="{cy + 26}" class="mono" font-size="10px" font-weight="600" text-anchor="end" fill="{c["amber"]}">{esc(star_str)}</text>')
            right_x -= tw(star_str, 10, mono=True) + 12
        out.append(f'<circle cx="{right_x - 4}" cy="{cy + 22}" r="3" fill="{lang_col}"/>')
        out.append(f'<text x="{right_x - 12}" y="{cy + 26}" class="mono" font-size="10px" font-weight="400" text-anchor="end" fill="{c["muted"]}">{esc(lang_label)}</text>')

        # Description
        desc_lines = wrap(p["blurb"], 11, PROJ_CARD_W - 32, 2)
        for j, line in enumerate(desc_lines):
            out.append(f'<text x="{tx}" y="{cy + 50 + j * 16}" font-size="11px" fill="{c["muted"]}">{esc(line)}</text>')

        # Tag pills
        tag_x = float(tx)
        tag_y = cy + PROJ_CARD_H - 26
        for t in p["tags"]:
            ts, tw_ = tag(tag_x, tag_y, t, c["accent"], c)
            out.append(ts)
            tag_x += tw_ + 6

    out.append("</svg>")
    return "\n".join(out)


# ================================================================== stack

LANE_X = 148
CHIP_GAP = 8
ROW_H = 36


def _lane_rows(items):
    rows, row, x = [], [], float(LANE_X)
    for label, slug, colour in items:
        w = chip_w(label, slug is not None and icon_path(slug) is not None)
        if row and x + w > W - PAD:
            rows.append(row)
            row, x = [], float(LANE_X)
        row.append((label, slug, colour, w))
        x += w + CHIP_GAP
    if row:
        rows.append(row)
    return rows


def render_stack(theme: str) -> str:
    c = THEMES[theme]
    lanes = [(label, _lane_rows(items)) for label, items in STACK]
    height = 52 + sum(len(rows) * ROW_H + 12 for _, rows in lanes) + 8
    out = svg_open(W, height, c)

    out.append(f'<text x="{PAD}" y="28" class="section-head">Engineering stack · 工程技术栈</text>')
    out.append(f'<text x="{W - PAD}" y="28" class="section-sub" text-anchor="end">{WEBSITE}</text>')
    out.append(f'<line x1="{PAD}" y1="40" x2="{W - PAD}" y2="40" stroke="{c["rule"]}"/>')

    y = 52
    for i, (label, rows) in enumerate(lanes):
        block = len(rows) * ROW_H
        out.append(f'<text x="{PAD}" y="{y + block / 2 + 4:.1f}" class="mono" font-size="10px" font-weight="500" fill="{c["muted"]}">{esc(label)}</text>')
        for r, row in enumerate(rows):
            x = float(LANE_X)
            for name, slug, colour, w in row:
                out.append(chip(x, y + r * ROW_H + 2, name, slug, brand_colour(colour, theme, c), c))
                x += w + CHIP_GAP
        y += block + 12
        if i < len(lanes) - 1:
            out.append(f'<line x1="{PAD}" y1="{y - 6:.1f}" x2="{W - PAD}" y2="{y - 6:.1f}" stroke="{c["rule"]}"/>')

    out.append("</svg>")
    return "\n".join(out)


# ================================================================ activity

ACT_H = 216


def tier_of(weeks: list[int]):
    active = sorted(v for v in weeks if v > 0)
    if not active:
        return lambda v: 0
    cuts = [active[int(len(active) * q)] for q in (0.25, 0.5, 0.8)]
    return lambda v: 0 if v == 0 else 1 + sum(v > k for k in cuts)


def render_activity(theme: str, d: dict) -> str:
    c = THEMES[theme]
    out = svg_open(W, ACT_H, c)

    out.append(f'<text x="{PAD}" y="28" class="section-head">{esc("Activity & language distribution · 贡献与语言分布")}</text>')
    out.append(f'<text x="{W - PAD}" y="28" class="section-sub" text-anchor="end">Public repos · self-hosted SVG · auto-refresh weekly</text>')
    out.append(f'<line x1="{PAD}" y1="40" x2="{W - PAD}" y2="40" stroke="{c["rule"]}"/>')

    # ── Left: 52-week contribution bars ──
    lx, lw = PAD, 500
    out.append(f'<text x="{lx}" y="62" class="mono" font-size="10px" font-weight="500" fill="{c["muted"]}">Contributions · last 52 weeks</text>')
    weeks = d["weeks"] or [0] * 52
    n = len(weeks)
    base, maxh = 156, 66
    peak = max(weeks) or 1
    gapb = 3
    bwid = (lw - gapb * (n - 1)) / n
    tier = tier_of(weeks)
    out.append(f'<line x1="{lx}" y1="{base + 0.5}" x2="{lx + lw}" y2="{base + 0.5}" stroke="{c["rule"]}"/>')
    for i, v in enumerate(weeks):
        h = max(2.0, v / peak * maxh) if v else 2.0
        bx = lx + i * (bwid + gapb)
        out.append(f'<rect x="{bx:.2f}" y="{base - h:.2f}" width="{bwid:.2f}" height="{h:.2f}" rx="1.5" fill="{c["bars"][tier(v)]}"/>')
    out.append(f'<text x="{lx}" y="{base + 16}" class="mono" font-size="9px" fill="{c["muted"]}">52 weeks ago</text>')
    out.append(f'<text x="{lx + lw}" y="{base + 16}" class="mono" font-size="9px" fill="{c["muted"]}" text-anchor="end">Now</text>')

    total = f'{d["contribs"]:,}'
    out.append(f'<text x="{lx}" y="{base + 40}" class="num" fill="{c["ink"]}">{total}</text>')
    out.append(f'<text x="{lx + tw(total, 22) + 10:.1f}" y="{base + 40}" class="mono" font-size="10px" font-weight="400" fill="{c["muted"]}">contributions</text>')

    # ── Right: top-6 languages ──
    rx, rw = 576, W - PAD - 576
    langs = sorted(d["langs"].items(), key=lambda kv: kv[1], reverse=True)
    total_b = sum(v for _, v in langs) or 1
    shown = langs[:6]
    out.append(f'<text x="{rx}" y="62" class="mono" font-size="10px" font-weight="500" fill="{c["muted"]}">Languages · by bytes</text>')
    out.append(f'<text x="{rx + rw}" y="62" class="mono" font-size="10px" font-weight="400" fill="{c["muted"]}" text-anchor="end">Top {len(shown)} of {len(langs)}</text>')
    bar_x, bar_w = rx + 96, rw - 96 - 48
    y = 86
    for name, v in shown:
        pct = v / total_b * 100
        colour = LANG_COLORS.get(name, c["muted"])
        out.append(f'<circle cx="{rx + 4}" cy="{y - 4}" r="3" fill="{colour}"/>')
        out.append(f'<text x="{rx + 13}" y="{y}" class="mono" font-size="11px" font-weight="400" fill="{c["ink"]}">{esc(name[:12])}</text>')
        out.append(f'<rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="8" rx="4" fill="{c["box"]}" stroke="{c["border"]}"/>')
        out.append(f'<rect x="{bar_x}" y="{y - 10}" width="{max(3.0, pct / 100 * bar_w):.1f}" height="8" rx="4" fill="{colour}"/>')
        out.append(f'<text x="{rx + rw}" y="{y}" class="mono" font-size="10px" font-weight="400" fill="{c["muted"]}" text-anchor="end">{pct:.1f}%</text>')
        y += 18
    out.append("</svg>")
    return "\n".join(out)


# =================================================================== main

EXPECTED_FILES = {"hero", "hero-dark", "domains", "domains-dark", "projects", "projects-dark",
                  "stack", "stack-dark", "activity", "activity-dark"}


def main() -> int:
    t0 = time.time()
    ASSETS.mkdir(parents=True, exist_ok=True)

    # Clean ALL old SVGs (including stale systems*.svg, project-*.svg)
    for old in ASSETS.glob("*.svg"):
        old.unlink()

    data = collect()

    written = []
    for theme in THEMES:
        suffix = "" if theme == "light" else "-dark"
        outputs = [
            ("hero", render_hero(theme, data)),
            ("domains", render_domains(theme)),
            ("projects", render_projects(theme, data)),
            ("stack", render_stack(theme)),
            ("activity", render_activity(theme, data)),
        ]
        for stem, svg in outputs:
            path = ASSETS / f"{stem}{suffix}.svg"
            path.write_text(svg + "\n", encoding="utf-8")
            written.append(path)

    for p in written:
        print(f"  wrote {p.relative_to(ROOT)} ({p.stat().st_size:,} B)")

    actual = {p.stem for p in written}
    if actual != EXPECTED_FILES:
        print(f"  ! MISMATCH: expected {EXPECTED_FILES}, got {actual}", file=sys.stderr)
        return 1

    print(f"Done in {time.time() - t0:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
