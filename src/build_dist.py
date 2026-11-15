# -*- coding: utf-8 -*-
"""读 bigtest.json，生成「AI 报价分布 vs 官方价分布」白底 SVG → figs/fig_dist.png

风格与 build_figs.py 其余数据图一致：白底、同一套色板、标题/副标题/页脚。
用法：
    python src/build_dist.py            # 只生成 SVG
    python src/build_dist.py --png      # 再用 cdp.py 截图（需 Chrome 9222）
"""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "bigtest.json").read_text(encoding="utf-8"))
A = DATA["assert_verify"]
rows = A["results"]

ai = sorted(r["asserted"] for r in rows if r["asserted"] is not None)
off = sorted(r["official_today"] for r in rows if r.get("official_today") is not None)

INK = "#1f2328"
MUTED = "#6b7280"
LINE = "#d8dbe0"
RED = "#a32d2d"
RED_L = "#f2c6c6"
GREEN = "#0f6e56"
AMBER = "#b45309"
FONT = "'Microsoft YaHei','PingFang SC','Noto Sans CJK SC',sans-serif"

X0, X1 = 7.4, 9.7
W, H = 1200, 560
L, R, T, B = 70, 50, 130, 80


def x(v):
    return L + (v - X0) / (X1 - X0) * (W - L - R)


def text(x_, y_, s_, size=15, fill=INK, weight="400", anchor="start"):
    return (f'<text x="{x_:.1f}" y="{y_:.1f}" font-size="{size}" fill="{fill}" '
            f'font-weight="{weight}" text-anchor="{anchor}">{s_}</text>')


body = []
body.append(text(40, 48, "AI 报的价和官方的价，不在一个区间", 23, INK, "500"))
body.append(text(40, 76, "40 座城市，同一批 query、同一天。橙点是 AI 不联网凭记忆报的价，绿点是元宝搜索成品油 VR 卡的今日价。两个分布零重叠。", 14, MUTED))

# 列头
body.append(text(L, T - 26, "官方今日价（40 城）", 15, GREEN, "500"))
body.append(text(L, T - 6, f"范围 {min(off):.2f} ~ {max(off):.2f} · σ {A['today_std']:.3f}", 13, MUTED))

body.append(text(L, 386, "AI 盲测报价（40 城）", 15, AMBER, "500"))
body.append(text(L, 406, f"范围 {min(ai):.2f} ~ {max(ai):.2f} · σ {A['asserted_std']:.3f}", 13, MUTED))

# 零重叠间隔带
gap_lo, gap_hi = max(ai), min(off)
body.append(f'<rect x="{x(gap_lo):.1f}" y="{T-40}" width="{x(gap_hi)-x(gap_lo):.1f}" '
            f'height="{H-B-T+40}" fill="{RED}" fill-opacity="0.06"/>')
for v in (gap_lo, gap_hi):
    body.append(f'<line x1="{x(v):.1f}" y1="{T-40}" x2="{x(v):.1f}" y2="{H-B}" '
                f'stroke="{RED}" stroke-opacity="0.45" stroke-dasharray="5 5"/>')
body.append(text((x(gap_lo) + x(gap_hi)) / 2, T - 14, f"间隔 {gap_hi - gap_lo:.2f} 元/升", 14, RED, "500", "middle"))

# 散点（正弦抖动成带状）
for i, v in enumerate(off):
    j = math.sin(i * 2.399963) * 26
    body.append(f'<circle cx="{x(v):.1f}" cy="{215 + j:.1f}" r="6" fill="{GREEN}" fill-opacity="0.75"/>')
for i, v in enumerate(ai):
    j = math.sin(i * 2.399963 + 1.1) * 26
    body.append(f'<circle cx="{x(v):.1f}" cy="{460 + j:.1f}" r="6" fill="{AMBER}" fill-opacity="0.75"/>')

# 坐标轴与刻度
body.append(f'<line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="{LINE}"/>')
t = 7.5
while t <= 9.6:
    body.append(f'<line x1="{x(t):.1f}" y1="{H-B}" x2="{x(t):.1f}" y2="{H-B+8}" stroke="{LINE}"/>')
    body.append(text(x(t), H - B + 28, f"{t:.1f}", 13, MUTED, "400", "middle"))
    t += 0.5
body.append(text(W - R, H - B - 12, "92 号汽油 · 元/升", 13, MUTED, "400", "end"))
body.append(text(40, H - 20, "数据：data/bigtest.json → assert_verify（40 条，先答后查）；σ 为总体标准差", 12, MUTED))

svg_str = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" font-family="{FONT}">'
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>' + "".join(body) + "</svg>")

OUT = ROOT / "figs"
OUT.mkdir(exist_ok=True)
(OUT / "fig_dist.svg").write_text(svg_str, encoding="utf-8")
print(f"[svg] figs/fig_dist.svg  ai {min(ai):.2f}~{max(ai):.2f}  off {min(off):.2f}~{max(off):.2f}  gap {gap_hi-gap_lo:.2f}")

if "--png" in sys.argv:
    html = ('<!doctype html><meta charset="utf-8"><style>html,body{margin:0;padding:0;'
            'background:#fff}svg{display:block}</style>' + svg_str)
    tmp = OUT / "_fig_dist.html"
    tmp.write_text(html, encoding="utf-8")
    url = "file:///" + str(tmp).replace("\\", "/")
    cdp = str(ROOT.parent / "cdp.py")
    env = dict(os.environ, CDP_MATCH="figs")
    subprocess.run([sys.executable, cdp, "goto", url], check=False, stdout=subprocess.DEVNULL, env=env)
    subprocess.run([sys.executable, cdp, "shot", str(OUT / "fig_dist.png"),
                    "--viewport", f"{W},{H}"], check=False, env=env)
    tmp.unlink(missing_ok=True)
    print("[png] figs/fig_dist.png")
