# -*- coding: utf-8 -*-
"""读 bigtest.json，生成「AI 报价分布 vs 官方价分布」对比 SVG → docs/dist.html"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
data = json.loads((ROOT / "data" / "bigtest.json").read_text(encoding="utf-8"))
rows = data["assert_verify"]["results"]

ai = sorted([r["asserted"] for r in rows if r["asserted"] is not None])
off = sorted([r["official_today"] for r in rows if r.get("official_today") is not None])

X0, X1 = 7.4, 9.7          # 价格轴范围
W, H = 1720, 560
L, R, T, B = 90, 40, 70, 80

def x(v):
    return L + (v - X0) / (X1 - X0) * (W - L - R)

def jitter(i, n):
    """给散点纵向抖动，形成带状分布"""
    return math.sin(i * 2.399963) * 34

dots_ai, dots_off = [], []
for i, v in enumerate(ai):
    dots_ai.append(f'<circle cx="{x(v):.1f}" cy="{340+jitter(i,40):.1f}" r="7" fill="#d29922" fill-opacity="0.78"/>')
for i, v in enumerate(off):
    dots_off.append(f'<circle cx="{x(v):.1f}" cy="{190+jitter(i+7,40):.1f}" r="7" fill="#3fb950" fill-opacity="0.78"/>')

# 分界区间
gap_lo, gap_hi = max(ai), min(off)
gap_band = (f'<rect x="{x(gap_lo):.1f}" y="{T}" width="{x(gap_hi)-x(gap_lo):.1f}" '
            f'height="{H-T-B}" fill="#f85149" fill-opacity="0.08"/>')
gap_line_top = (f'<line x1="{x(gap_lo):.1f}" y1="{T}" x2="{x(gap_lo):.1f}" y2="{H-B}" '
                f'stroke="#f85149" stroke-opacity="0.45" stroke-dasharray="5 5"/>')
gap_line_bot = (f'<line x1="{x(gap_hi):.1f}" y1="{T}" x2="{x(gap_hi):.1f}" y2="{H-B}" '
                f'stroke="#f85149" stroke-opacity="0.45" stroke-dasharray="5 5"/>')

# 价格刻度
ticks = []
t = 7.5
while t <= 9.6:
    ticks.append(f'''<line x1="{x(t):.1f}" y1="{H-B}" x2="{x(t):.1f}" y2="{H-B+8}" stroke="#6e7681"/>
<text x="{x(t):.1f}" y="{H-B+28}" fill="#8b949e" font-size="14" text-anchor="middle">{t:.1f}</text>''')
    t += 0.25

# 均值线
am, om = sum(ai)/len(ai), sum(off)/len(off)

svg = f'''<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{W}" height="{H}" fill="#0d1117"/>
  {gap_band}{gap_line_top}{gap_line_bot}
  <text x="{(x(gap_lo)+x(gap_hi))/2:.0f}" y="{T+40}" fill="#f85149" font-size="15"
        text-anchor="middle">间隔 0.16 元/升</text>

  <text x="{L}" y="{T+42}" fill="#3fb950" font-size="18" font-weight="600">官方今日价（40 城）</text>
  <text x="{L}" y="{T+66}" fill="#8b949e" font-size="13">范围 {min(off):.2f} ~ {max(off):.2f} · σ 0.182</text>
  {''.join(dots_off)}

  <text x="{L}" y="{390}" fill="#d29922" font-size="18" font-weight="600">AI 盲测报价（40 城）</text>
  <text x="{L}" y="{414}" fill="#8b949e" font-size="13">范围 {min(ai):.2f} ~ {max(ai):.2f} · σ 0.103</text>
  {''.join(dots_ai)}

  {''.join(ticks)}
  <text x="{W-40}" y="{H-B+28}" fill="#8b949e" font-size="14" text-anchor="end">92 号汽油 · 元/升</text>

  <line x1="{L}" y1="{H-B}" x2="{W-R}" y2="{H-B}" stroke="#30363d"/>
</svg>'''

html = f'''<!DOCTYPE html><html><head><meta charset="utf-8"><title>分布对比</title>
<style>body{{margin:0;background:#0d1117;font:14px/1.5 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{padding:30px 40px}}h1{{color:#e8edf3;font-size:24px;margin:0 0 6px}}
p{{color:#8b949e;margin:0 0 20px}}svg{{max-width:100%}}</style></head>
<body><div class="wrap">
<h1>AI 报的价和官方的价，不在一个区间</h1>
<p>40 座城市，同一批 query、同一天。黄色是 AI（未联网）给的价，绿色是元宝搜索成品油 VR 卡的今日价。两个分布零重叠。</p>
{svg}
</div></body></html>'''

(ROOT / "docs" / "dist.html").write_text(html, encoding="utf-8")
print(f"ai {min(ai):.2f}~{max(ai):.2f} mean {am:.2f}")
print(f"off {min(off):.2f}~{max(off):.2f} mean {om:.2f}")
print(f"gap {gap_hi - gap_lo:.2f}")
