# -*- coding: utf-8 -*-
"""从 data/bigtest.json 渲染文章配图（纯标准库，手写 SVG）。

四张图：
  figs/fig_four_state.svg    四态判定决策路径
  figs/fig_gap40.svg         40 城盲测的单城价差（全部为负，方向一致）
  figs/fig_spread49.svg      49 城同日 92 号挂牌价极差
  figs/fig_web_dedup.svg     100 条网页 → 去重 89 条，有误率反而升高

用法：
    python src/build_figs.py            # 只生成 SVG
    python src/build_figs.py --png      # 再用 cdp.py 截图成 PNG（需 Chrome 9222）
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "bigtest.json").read_text(encoding="utf-8"))
OUT = ROOT / "figs"
OUT.mkdir(exist_ok=True)

INK = "#1f2328"
MUTED = "#6b7280"
LINE = "#d8dbe0"
BLUE = "#185FA5"
BLUE_L = "#b6d4f4"
RED = "#a32d2d"
RED_L = "#f2c6c6"
GREEN = "#0f6e56"
GREEN_L = "#a8d8c8"
AMBER = "#854f0b"
AMBER_L = "#f6d9a8"
FONT = "'Microsoft YaHei','PingFang SC','Noto Sans CJK SC',sans-serif"


def svg(w, h, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" font-family="{FONT}">'
        f'<rect width="{w}" height="{h}" fill="#ffffff"/>' + body + "</svg>"
    )


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=15, fill=INK, weight="400", anchor="start", opacity=1.0):
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}" text-anchor="{anchor}" opacity="{opacity}">{esc(s)}</text>'
    )


def fig_four_state():
    """判定路径：先比今日，再比上一轮，都不等才是 mismatch；无卡直接 unknown。"""
    body = []
    body.append(text(40, 46, "一句话进来，先问三个问题", 22, INK, "500"))
    body.append(text(40, 74, "判定器只看两个官方字段：今日价、上一轮价。没有卡就不判，不猜。", 14, MUTED))

    # 输入
    body.append(f'<rect x="40" y="110" width="200" height="88" rx="8" fill="#f3f5f8" stroke="{LINE}"/>')
    body.append(text(140, 145, "AI 的回答", 15, INK, "500", "middle"))
    body.append(text(140, 170, "「约 7.85 元/升」", 14, MUTED, "400", "middle"))

    # 三道判断
    steps = [
        ("Q1  等于今日价？", "是 → correct（属实）", GREEN, GREEN_L, 110),
        ("Q2  等于上一轮价？", "是 → stale（过期，不是编造）", AMBER, AMBER_L, 260),
        ("都不等", "→ mismatch（两轮都不是）", RED, RED_L, 410),
    ]
    for title, verdict, col, colL, y in steps:
        body.append(f'<rect x="300" y="{y}" width="300" height="88" rx="8" fill="#ffffff" stroke="{col}" stroke-width="1.4"/>')
        body.append(text(320, y + 36, title, 15, INK, "500"))
        body.append(text(320, y + 64, verdict, 13, col, "500"))
        # 连线
        body.append(f'<path d="M240 154 H270 V{y + 44} H300" fill="none" stroke="{LINE}" stroke-width="1.4"/>')
        body.append(f'<path d="M295 {y + 44} l6 -4 v8 z" fill="{LINE}"/>')
        # 结果
        body.append(f'<rect x="660" y="{y + 14}" width="200" height="60" rx="6" fill="{colL}" opacity="0.55"/>')
        body.append(text(760, y + 40, verdict.split("→ ")[1].split("（")[0] if "→" in verdict else "", 14, col, "500", "middle"))
        body.append(text(760, y + 60, verdict.split("（")[1].rstrip("）") if "（" in verdict else "", 12, MUTED, "400", "middle"))
        body.append(f'<path d="M600 {y + 44} H660" fill="none" stroke="{LINE}" stroke-width="1.4"/>')

    # unknown 分支
    body.append(f'<rect x="300" y="560" width="300" height="76" rx="8" fill="#ffffff" stroke="{MUTED}" stroke-width="1.2" stroke-dasharray="5 4"/>')
    body.append(text(320, 592, "Q0  这个城市有 VR 卡吗？", 15, INK, "500"))
    body.append(text(320, 618, "没有 → unknown（存疑，不进分母）", 13, MUTED, "500"))
    body.append(f'<path d="M140 198 V598 H300" fill="none" stroke="{LINE}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    body.append(f'<rect x="660" y="574" width="200" height="48" rx="6" fill="#eef0f3"/>')
    body.append(text(760, 604, "不降级、不借邻省价", 13, MUTED, "400", "middle"))

    body.append(text(40, 690, "四态的价值在 stale 单独成立：它把「曾经是真的」和「从来没有过」分开，"
                              "误判成本从「冤枉」降到「提醒」。", 13, MUTED))
    return svg(900, 720, "".join(body))


def fig_gap40():
    """40 城盲测：每城 AI 报价 − 官方今日价，全部为负。"""
    rows = DATA["assert_verify"]["results"]
    rows = sorted(rows, key=lambda r: r["gap"])
    body = []
    W, H = 1200, 620
    left, right, top, bottom = 70, 60, 96, 90
    pw, ph = W - left - right, H - top - bottom

    body.append(text(40, 44, "40 个城市，40 条都偏低：没有一条是正的", 22, INK, "500"))
    body.append(text(40, 72, "每根柱 = 一个城市（AI 报价 − 官方今日价，元/升）。"
                             "排序后全部落在零线下方，说明是系统性偏移，不是随机出错。", 13, MUTED))

    lo, hi = -1.55, 0.05
    def y(v):
        return top + (hi - v) / (hi - lo) * ph

    # 网格
    for v in [0, -0.5, -1.0, -1.5]:
        yy = y(v)
        body.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{W - right}" y2="{yy:.1f}" stroke="{LINE}" stroke-width="0.8"/>')
        body.append(text(left - 10, yy + 4, f"{v:.1f}", 12, MUTED, "400", "end"))
    body.append(f'<line x1="{left}" y1="{y(0):.1f}" x2="{W - right}" y2="{y(0):.1f}" stroke="{INK}" stroke-width="1.2"/>')

    bw = pw / len(rows)
    for i, r in enumerate(rows):
        x = left + i * bw + bw * 0.18
        w = bw * 0.64
        y0, y1 = y(0), y(r["gap"])
        body.append(f'<rect x="{x:.1f}" y="{y0:.1f}" width="{w:.1f}" height="{y1 - y0:.1f}" fill="{BLUE}" opacity="0.82"/>')

    # 标注首尾（海口=最负，苏州=最不负）
    first, last = rows[0], rows[-1]
    for r, col, above in [(first, RED, False), (last, MUTED, True)]:
        i = rows.index(r)
        xc = left + i * bw + bw * 0.5
        yy = y(r["gap"])
        ly = yy + 20 if not above else y(0) - 12
        xc2 = xc + 34 if not above else xc
        body.append(text(xc2, ly, f'{r["city"]} {r["gap"]:.2f}', 12, col, "500", "middle"))

    avg = DATA["assert_verify"]["gap_mean"]
    body.append(f'<line x1="{left}" y1="{y(avg):.1f}" x2="{W - right}" y2="{y(avg):.1f}" stroke="{RED}" stroke-width="1.2" stroke-dasharray="6 4"/>')
    body.append(text(W - right - 6, y(avg) - 8, f"均值 {avg:.2f}", 12, RED, "500", "end"))
    body.append(text(W / 2, H - 34, "40 个盲测城市，按价差从小到大排（最左海口 −1.43，最右苏州 −0.29）", 13, MUTED, "400", "middle"))
    return svg(W, H, "".join(body))


def fig_spread49():
    """49 城同日挂牌价，横向点线图。"""
    rows = sorted(DATA["cross_city"]["rows"], key=lambda r: r["today"])
    body = []
    W, H = 1200, 600
    left, right, top, bottom = 90, 260, 140, 80
    pw = W - left - right
    lo, hi = 8.15, 9.55
    def x(v):
        return left + (v - lo) / (hi - lo) * pw

    body.append(text(40, 44, "同一天，同一个标号，全国最贵和最便宜差 1.23 元", 22, INK, "500"))
    body.append(text(40, 72, "49 个城市同日 92 号挂牌价。一箱 50 升，最贵和最便宜的城差 61.5 元。", 13, MUTED))

    axis_y = H - bottom
    for v in [8.2, 8.5, 8.8, 9.1, 9.4]:
        body.append(f'<line x1="{x(v):.1f}" y1="{top - 10}" x2="{x(v):.1f}" y2="{axis_y}" stroke="{LINE}" stroke-width="0.8"/>')
        body.append(text(x(v), axis_y + 24, f"{v:.1f}", 12, MUTED, "400", "middle"))

    n = len(rows)
    for i, r in enumerate(rows):
        yy = top + (i + 0.5) * (axis_y - top) / n
        body.append(f'<circle cx="{x(r["today"]):.1f}" cy="{yy:.1f}" r="4.2" fill="{BLUE}" opacity="0.9"/>')
        if i % 6 == 0 or r["city"] in ("西安", "海口"):
            body.append(text(x(r["today"]) - 10, yy + 4, r["city"], 11, MUTED, "400", "end"))

    for city, v, col in [("西安", 8.25, GREEN), ("海口", 9.48, RED)]:
        body.append(f'<line x1="{x(v):.1f}" y1="{top - 34}" x2="{x(v):.1f}" y2="{axis_y}" stroke="{col}" stroke-width="1.2" stroke-dasharray="4 4"/>')
        body.append(text(x(v), top - 44, f"{city} {v:.2f}", 13, col, "500", "middle"))
    body.append(text(x(8.865), axis_y + 52, "92 号汽油挂牌价（元/升）", 12, MUTED, "400", "middle"))
    return svg(W, H, "".join(body))


def fig_web_dedup():
    """100 条 → 去重 89 条；有误率 76.7% → 79.2%。"""
    w = DATA["web_freshness"]
    dist = w["dist"]
    body = []
    W, H = 1200, 520
    body.append(text(40, 44, "去重之后，错误率反而升了", 22, INK, "500"))
    body.append(text(40, 72, "100 条网页摘要里有 11 组是同标题的跨站转载。去掉转载样本，分母缩小，错误率从 76.7% 升到 79.2%。", 13, MUTED))

    # 左：未去重
    def panel(x0, title, total, dec, wrong, rate, note):
        body.append(text(x0, 140, title, 15, INK, "500"))
        body.append(text(x0, 166, f"{dec} / {total} 条有明确价格", 12, MUTED))
        # 条
        bw, bh = 440, 54
        body.append(f'<rect x="{x0}" y="186" width="{bw}" height="{bh}" rx="4" fill="#eef0f3"/>')
        body.append(f'<rect x="{x0}" y="186" width="{bw * wrong / dec:.1f}" height="{bh}" rx="4" fill="{RED}" opacity="0.85"/>')
        body.append(text(x0 + 12, 220, f"有误 {wrong}", 14, "#ffffff", "500"))
        body.append(text(x0 + bw + 14, 220, f"{rate:.1f}%", 20, RED, "500"))
        body.append(text(x0, 274, note, 12, MUTED))

    panel(40, "① 未去重：100 条原始样本", 100, 60, 46, 76.7,
          "分母 60 = 100 − 40 条摘要里没有明确价格")
    panel(620, "② 按标题去重：89 条独立内容", 89, 53, 42, 79.2,
          "分母 53 = 89 − 36 条无价格；11 组转载合并为首条")

    body.append(f'<path d="M520 213 H596" fill="none" stroke="{INK}" stroke-width="1.4"/>')
    body.append(f'<path d="M590 208 l8 5 -8 5 z" fill="{INK}"/>')
    body.append(text(558, 200, "去重", 12, MUTED, "400", "middle"))

    body.append(text(40, 356, "为什么这条值得写：", 14, INK, "500"))
    body.append(text(40, 384, "如果错误率是靠「多抓几条」堆出来的，去重后应该下降。它上升了，说明这 100 条里的错误不是"
                              "样本噪声，而是同一个错误被搬运了 11 次。", 13, MUTED))
    body.append(text(40, 412, "换句话说，普通搜索里那些看起来「多源互证」的结果，很可能是同一篇文章的镜像。", 13, MUTED))
    body.append(text(40, 460, "数据：data/bigtest.json → web_freshness（100 条 = 10 城 × 10 条）", 12, MUTED, "400"))
    return svg(W, H, "".join(body))


def fig_gains():
    """元宝搜索解决了什么：三处「没卡 / 有卡」的对照，外加一处没解决。"""
    W, H = 1200, 880
    body = []
    body.append(text(40, 48, "元宝搜索解决了三个问题，第四个没解决", 23, INK, "500"))
    body.append(text(40, 76, "同一批城市、同一个 query，只换检索模式。左边是普通检索（Mode=0），右边是权威 VR 卡（Mode=1）。", 14, MUTED))

    # 列头
    body.append(text(268, 108, "普通检索：45 个数字，说不清是哪天的", 13, MUTED, "500"))
    body.append(text(732, 108, "元宝 VR 卡：字段带生效日，两个数能互证", 13, BLUE, "500"))

    rows = [
        ("①", "分不清\n过期和编造",
         ["40%", "首答是今日价", "其余 60% 是别的日子，", "从结果里看不出来"],
         ["15/15", "今日价 + 上一轮价都给", "8.89 等于上一轮", "→ 判 stale，不算编造"]),
        ("②", "抽取\n噪声",
         ["0.28", "郑州首答抽出的\"价格\"", "100 条里 36 条摘要", "压根没写价格"],
         ["3 字段", "数值 / 生效日 / 来源站点", "不用正则，不用二次核对", "89 次调用 41 秒跑完"]),
        ("③", "来源\n不可追",
         ["11 组", "同标题被站点互搬", "有误率 76.7% → 79.2%", "多查来源反而更糟"],
         ["同价", "来源与生效日跟着价格走", "被十家站点搬", "还是那一个价"]),
    ]

    top = 126
    rh = 178
    for i, (num, label, left, right) in enumerate(rows):
        y = top + i * (rh + 14)
        # 左侧标签
        body.append(f'<rect x="40" y="{y}" width="200" height="{rh}" rx="8" fill="#f3f5f8" stroke="{LINE}"/>')
        body.append(text(66, y + 46, num, 28, MUTED, "500"))
        parts = label.split("\n")
        for j, pt in enumerate(parts):
            body.append(text(96, y + 40 + j * 26, pt, 17, INK, "500"))
        body.append(text(66, y + 132, "问题", 12, MUTED))

        # 普通检索面板
        body.append(f'<rect x="258" y="{y}" width="445" height="{rh}" rx="8" fill="#fff" stroke="{RED_L}"/>')
        body.append(f'<rect x="258" y="{y}" width="4" height="{rh}" rx="2" fill="{RED}"/>')
        body.append(text(284, y + 50, left[0], 34, RED, "500"))
        body.append(text(284, y + 84, left[1], 14, INK))
        body.append(text(284, y + 116, left[2], 13, MUTED))
        body.append(text(284, y + 140, left[3], 13, MUTED))

        # VR 卡面板
        body.append(f'<rect x="722" y="{y}" width="438" height="{rh}" rx="8" fill="#fff" stroke="{BLUE_L}"/>')
        body.append(f'<rect x="722" y="{y}" width="4" height="{rh}" rx="2" fill="{BLUE}"/>')
        body.append(text(748, y + 50, right[0], 34, BLUE, "500"))
        body.append(text(748, y + 84, right[1], 14, INK))
        body.append(text(748, y + 116, right[2], 13, MUTED))
        body.append(text(748, y + 140, right[3], 13, MUTED))

    # 没解决的一条
    y = top + 3 * (rh + 14)
    body.append(f'<rect x="40" y="{y}" width="1120" height="128" rx="8" fill="#fdf6ec" stroke="{AMBER_L}"/>')
    body.append(text(66, y + 40, "④", 26, AMBER, "500"))
    body.append(text(96, y + 38, "没解决：覆盖不全", 17, INK, "500"))
    body.append(text(66, y + 74, "上海 95 号、成都 0 号柴油返回 0 条卡；27 个垂类探针只命中 14 个，oil 这一类命中 1/3。", 14, INK))
    body.append(text(66, y + 102, "所以我从头到尾只敢说 92 号汽油。工具给的是对照值，判决还得自己写，这是它不管的部分。", 14, MUTED))

    body.append(text(40, H - 24, "数据：data/bigtest.json（assert_verify / web_freshness）、data/compare.json；普通检索 45 次首答，VR 卡 15 城 15 次双字段", 12, MUTED))
    return svg(W, H, "".join(body))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", action="store_true")
    args = ap.parse_args()

    figs = {
        "fig_four_state": fig_four_state(),
        "fig_gap40": fig_gap40(),
        "fig_spread49": fig_spread49(),
        "fig_web_dedup": fig_web_dedup(),
        "fig_gains": fig_gains(),
    }
    for name, s in figs.items():
        p = OUT / f"{name}.svg"
        p.write_text(s, encoding="utf-8")
        print(f"[svg] {p.relative_to(ROOT)}  {len(s)} bytes")

    if not args.png:
        return

    items = list(figs.items())
    cdp = str(ROOT.parent / "cdp.py")
    for name, s in items:
        w, h = [int(x) for x in s.split('viewBox="0 0 ')[1].split('"')[0].split()]
        html = (f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;padding:0;'
                f'background:#fff}}svg{{display:block}}</style>' + s)
        tmp = OUT / f"_{name}.html"
        tmp.write_text(html, encoding="utf-8")
        url = "file:///" + str(tmp).replace("\\", "/")
        env = dict(os.environ, CDP_MATCH="figs")
        subprocess.run([sys.executable, cdp, "goto", url], check=False,
                       stdout=subprocess.DEVNULL, env=env)
        png = OUT / f"{name}.png"
        subprocess.run([sys.executable, cdp, "shot", str(png),
                        "--viewport", f"{w},{h}"], check=False, env=env)
        print(f"[png] {png.relative_to(ROOT)}  {w}x{h}")


if __name__ == "__main__":
    main()
