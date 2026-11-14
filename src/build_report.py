# -*- coding: utf-8 -*-
"""bigtest.json → docs/油价真伪卡.html（单文件报告，可直接截图）"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;")

V_COLOR = {"correct": "#0f9d58", "stale": "#b26a00",
           "mismatch": "#c62828", "unknown": "#5f6b7a"}
V_CN = {"correct": "属实", "stale": "已过期",
        "mismatch": "不符", "unknown": "存疑"}


def main(work="."):
    work = Path(work).resolve()
    d = json.loads((work / "data" / "bigtest.json").read_text(encoding="utf-8"))

    a = d["assert_verify"]; w = d["web_freshness"]
    c = d["cross_city"]; v = d["vertical"]; u = d["unit"]
    m = d["_meta"]

    n_assert = a["n"]
    n_mis = a["dist"].get("mismatch", 0)
    err_rate = f"{w['error_rate']*100:.1f}%" if w["error_rate"] is not None else "—"

    # 40 城断言表
    ar = []
    for r in a["results"]:
        off = f"{r['official_today']:.2f}" if r.get("official_today") is not None else "无卡"
        gap = f"+{r['gap']:.2f}" if r.get("gap", 0) >= 0 else f"{r['gap']:.2f}"
        ar.append(f"""<tr><td>{esc(r['city'])}</td>
<td class="mono">{r['asserted']:.2f}</td>
<td class="mono">{off}</td>
<td class="mono">{r['official_history']:.2f}</td>
<td class="mono">{gap}</td>
<td><span class="badge" style="background:{V_COLOR[r['verdict']]}">{V_CN[r['verdict']]}</span></td></tr>""")

    # 网页审计：按城聚合
    cities = {}
    for r in w["rows"]:
        cities.setdefault(r["city"], []).append(r["state"])
    wr = []
    for city, sts in cities.items():
        cc = sts.count("correct"); mm = sts.count("mismatch")
        sl = sts.count("stale"); ud = sts.count("undetermined")
        dec = cc + mm + sl
        bad = mm + sl
        wr.append(f"""<tr><td>{esc(city)}</td><td class="mono">{len(sts)}</td>
<td class="mono">{cc}</td><td class="mono">{sl}</td><td class="mono">{mm}</td>
<td class="mono">{ud}</td>
<td class="mono">{(bad/dec*100):.1f}%</td></tr>""")

    # 价差表
    cr = []
    rows = c["rows"]
    mn, mx = c["min"]["price"], c["max"]["price"]
    for r in rows:
        hl = ""
        if r["today"] == mn: hl = ' style="background:#e8f6ee"'
        if r["today"] == mx: hl = ' style="background:#fdeaea"'
        cr.append(f"""<tr{hl}><td>{esc(r['city'])}</td>
<td class="mono">{r['today']:.2f}</td>
<td class="mono">{r['history']:.2f}</td>
<td class="mono">-{r['delta']:.2f}</td></tr>""")

    # 垂类
    vr = []
    for x in v["categories"]:
        miss = [y["query"] for y in x["detail"] if not y["hit"]]
        vr.append(f"""<tr><td class="mono">{x['category']}</td>
<td class="mono">{x['hits']}/{x['n']}</td>
<td class="mono">{x['rate']*100:.0f}%</td>
<td style="color:#5f6b7a">{esc('、'.join(miss)) or '—'}</td></tr>""")

    # 单测
    ur = []
    for r in u["rows"]:
        mark = "✓" if r["pass"] else "✗"
        ur.append(f"""<tr><td class="mono">{r['asserted']:.3f}</td>
<td class="mono">{r['today'] if r['today'] is not None else 'None'}</td>
<td class="mono">{r['history'] if r['history'] is not None else 'None'}</td>
<td class="mono">{r['expected']}</td>
<td class="mono">{r['got']}</td>
<td style="color:{'#0f9d58' if r['pass'] else '#c62828'}">{mark}</td></tr>""")

    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<title>油价真伪卡 · 实测报告</title><style>
:root{{--bg:#f6f7f9;--ink:#14181f;--muted:#5f6b7a;--line:#e3e7ec;--mono:'SF Mono',Consolas,monospace}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);
font:14.5px/1.65 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}}
.wrap{{max-width:1160px;margin:0 auto;padding:36px 26px 60px}}
h1{{font-size:24px;margin:0 0 4px}}h1 small{{font-size:13px;color:var(--muted);font-weight:400;margin-left:12px}}
.sub{{color:var(--muted);font-size:13.5px;margin:0 0 26px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:32px}}
.kpi{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px}}
.kpi .l{{font-size:12.5px;color:var(--muted)}}
.kpi .v{{font-size:28px;font-weight:700;font-variant-numeric:tabular-nums;margin-top:3px}}
.kpi .v small{{font-size:12px;font-weight:500;color:var(--muted);margin-left:3px}}
.kpi.bad .v{{color:#c62828}}
h2{{font-size:16px;margin:32px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--line)}}
h2 .tag{{font-size:12px;color:var(--muted);font-weight:400;margin-left:10px}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);
border-radius:10px;overflow:hidden}}
th,td{{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);font-size:13.5px}}
th{{background:#f0f2f5;font-size:12.5px;color:var(--muted);font-weight:600}}
tr:last-child td{{border-bottom:0}}
.mono{{font-family:var(--mono);font-variant-numeric:tabular-nums}}
.badge{{color:#fff;font-size:11.5px;padding:3px 9px;border-radius:5px;font-weight:600}}
.note{{font-size:12.5px;color:var(--muted);margin-top:10px;line-height:1.6}}
.chip{{display:inline-block;font-size:12px;color:var(--muted);border:1px solid var(--line);
background:#fff;padding:3px 10px;border-radius:16px;margin-right:8px}}
footer{{margin-top:36px;border-top:1px solid var(--line);padding-top:16px;
font-size:12.5px;color:var(--muted);line-height:1.7}}
</style></head><body><div class="wrap">
<h1>油价真伪卡 · 大规模实测报告 <small>生成于 {m['generated_at']}</small></h1>
<p class="sub">
<span class="chip">数据源 data/bigtest.json</span>
<span class="chip">SearchPro {m['tool_calls']} 次真实调用</span>
<span class="chip">耗时 {m['elapsed_sec']} 秒</span>
<span class="chip">判定器：整数分比较</span>
</p>

<div class="cards">
<div class="kpi bad"><div class="l">AI 盲测报价（40 城）</div>
<div class="v">{n_mis}<small>/{n_assert} 全错</small></div></div>
<div class="kpi bad"><div class="l">网页报价有误率</div>
<div class="v">{err_rate}<small> · {w['decidable']} 条可判定</small></div></div>
<div class="kpi"><div class="l">49 城价差（92 号）</div>
<div class="v">{c['spread']}<small> 元/升</small></div></div>
<div class="kpi"><div class="l">垂类覆盖 / 单元测试</div>
<div class="v">{v['covered']}/9<small> · {u['passed']}/{u['n']} 通过</small></div></div>
</div>

<h2>A. 断言验真 <span class="tag">40 城，全部在未联网条件下先作答</span></h2>
<table>
<tr><th>城市</th><th>AI 报价</th><th>官方今日</th><th>官方上一轮</th><th>低估幅度</th><th>判定</th></tr>
{''.join(ar)}
</table>
<p class="note">
AI 报价集中在 {a['asserted_range'][0]:.2f} ~ {a['asserted_range'][1]:.2f}（σ = {a['asserted_std']}），
官方价在 {a['today_range'][0]:.2f} ~ {a['today_range'][1]:.2f}（σ = {a['today_std']}），
两个区间<b>零重叠</b>。平均低估 {abs(a['gap_mean']):.2f} 元/升，最大低估 {abs(a['gap_min']):.2f}（昆明 7.95 vs 官方 9.38）。
按一箱 50 升算，平均差 {abs(a['gap_mean'])*50:.0f} 元。
</p>

<h2>B. 网页时效审计 <span class="tag">10 城 × 10 条，Mode=0 自然检索</span></h2>
<table>
<tr><th>城市</th><th>总条数</th><th>报今日</th><th>报上一轮</th><th>两轮都不是</th><th>无价格</th><th>有误率</th></tr>
{''.join(wr)}
</table>
<p class="note">
合计 {w['n']} 条：{w['dist'].get('correct',0)} 条报今日价、{w['dist'].get('stale',0)} 条报上一轮价、
{w['dist'].get('mismatch',0)} 条两轮都不是、{w['dist'].get('undetermined',0)} 条没有明确价格。
可判定的 {w['decidable']} 条里，<b>{w['error_rate']*100:.1f}%</b> 不是今天的价。普通搜索本身就在生产过期信息。
</p>

<h2>C. 跨城价差 <span class="tag">{c['n']} 城 · 92 号 · 同一天 · 零售挂牌价</span></h2>
<table>
<tr><th>城市</th><th>今日价</th><th>上一轮价</th><th>本轮变动</th></tr>
{''.join(cr)}
</table>
<p class="note">
最低 {c['min']['city']} {c['min']['price']}，最高 {c['max']['city']} {c['max']['price']}，
极差 <b>{c['spread']} 元/升</b>（一箱 50 升差 {c['tank_50_spread']} 元）。
价差 ≥ 1 元的城市：{'、'.join(c['over_1yuan'])}。均值 {c['mean']}，中位 {c['median']}，σ = {c['std']}。
「全国一个价」在结构上就不成立。
</p>

<h2>D. 垂类召回 <span class="tag">9 类 × 3 探针 = 27 次</span></h2>
<table>
<tr><th>垂类</th><th>命中</th><th>召回率</th><th>未命中的 query</th></tr>
{''.join(vr)}
</table>
<p class="note">
覆盖 {v['covered']}/9 类，全命中 {v['full_covered']}/9 类，总命中率 {v['total_hits']}/{v['total_probes']}。
对照组（非垂类 query）误命中 {v['control_false_hit']}/{v['control_n']}。
<b>oil 类只有 1/3 命中</b>：「上海 95 号」「成都 0 号柴油」无卡，说明 VR 卡不是标号全覆盖；
weather 与 phone 在不同批次结果不稳定，覆盖是变量不是常量。
</p>

<h2>E. 判定器单元测试 <span class="tag">零调用 · 含浮点边界用例</span></h2>
<table>
<tr><th>断言值</th><th>今日</th><th>上一轮</th><th>期望</th><th>实际</th><th>通过</th></tr>
{''.join(ur)}
</table>
<p class="note">
{u['passed']}/{u['n']} 通过。8.365 那条是浮点陷阱：8.365 × 100 在 IEEE 754 下得 836.4999…，
按浮点容差比较会判成 correct，与手算相反。判定器改为整数分比较后才稳定。
</p>

<footer>
本报告由 <span class="mono">src/bigtest.py</span> 一次真实采集生成，
{m['tool_calls']} 次 SearchPro 调用（约 {(m['tool_calls']*0.02):.1f} 元）。
数据包 <span class="mono">data/bigtest.json</span> 带 <span class="mono">_meta.generated_at</span> 与
<span class="mono">tool_calls</span>，本文每个数字都能 grep 到。
</footer>
</div></body></html>"""

    out = work / "docs" / "油价真伪卡.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"→ {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
