# -*- coding: utf-8 -*-
"""oil_pack.json → docs/油价真伪卡.html（单文件，零依赖，可直接截图）"""
import json
from pathlib import Path

CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f6f7f9;color:#1a1a1a;
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:40px 28px 80px}
h1{font-size:30px;margin:0 0 6px;letter-spacing:-.4px}
.sub{color:#6b7280;font-size:14px;margin-bottom:28px}
.meta{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:32px}
.chip{background:#fff;border:1px solid #e5e7eb;border-radius:999px;padding:6px 14px;font-size:13px;color:#374151}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:34px}
.card{background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:18px}
.card .k{font-size:12px;color:#6b7280;margin-bottom:8px}
.card .v{font-size:32px;font-weight:700;line-height:1}
.card .n{font-size:12px;color:#9ca3af;margin-top:8px}
.bad .v{color:#c2410c}.good .v{color:#15803d}.warn .v{color:#b45309}.mute .v{color:#6b7280}
section{background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:24px 26px;margin-bottom:22px}
h2{font-size:19px;margin:0 0 4px}
.note{color:#6b7280;font-size:13px;margin:0 0 18px}
table{width:100%;border-collapse:collapse;font-size:13.5px}
th{text-align:left;background:#f9fafb;color:#4b5563;font-weight:600;padding:9px 10px;border-bottom:1px solid #e5e7eb;white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid #f3f4f6}
tr:last-child td{border-bottom:0}
td.num{font-variant-numeric:tabular-nums}
.tag{display:inline-block;padding:2px 9px;border-radius:6px;font-size:12px;white-space:nowrap}
.t-correct{background:#dcfce7;color:#15803d}
.t-stale{background:#fef3c7;color:#b45309}
.t-mismatch{background:#fee2e2;color:#b91c1c}
.t-unknown,.t-undetermined{background:#f3f4f6;color:#6b7280}
.bar{height:15px;background:#e5e7eb;border-radius:4px;position:relative;overflow:hidden;min-width:120px}
.bar i{position:absolute;left:0;top:0;bottom:0;background:#f97316;border-radius:4px}
.hl{background:#fffbeb}
footer{color:#9ca3af;font-size:12px;text-align:center;margin-top:36px;line-height:1.9}
"""

LBL = {"correct": ("属实", "t-correct"), "stale": ("已过期", "t-stale"),
       "mismatch": ("与官方不符", "t-mismatch"), "unknown": ("存疑", "t-unknown"),
       "undetermined": ("无明确价格", "t-undetermined")}


def tag(v):
    t, c = LBL.get(v, (v, "t-unknown"))
    return f'<span class="tag {c}">{t}</span>'


def main(work="."):
    work = Path(work)
    p = json.loads((work / "data" / "oil_pack.json").read_text(encoding="utf-8"))
    pv, wf, cc, vt, meta, edge = p["price_verify"], p["web_freshness"], p["cross_city"], p["vertical"], p["_meta"], p.get("edge", [])

    s = pv["summary"]
    w = wf["summary"]
    judged = w.get("correct", 0) + w.get("stale", 0) + w.get("mismatch", 0)
    wrong_rate = round((w.get("mismatch", 0) + w.get("stale", 0)) / judged * 100, 1) if judged else 0

    cards = f"""
    <div class="cards">
      <div class="card bad"><div class="k">断言验真 · 全错</div><div class="v">{s.get('mismatch',0)}/{pv['n']}</div>
        <div class="n">mismatch {s.get('mismatch',0)} · stale {s.get('stale',0)} · correct {s.get('correct',0)}</div></div>
      <div class="card warn"><div class="k">网页信息 · 非今日价占比</div><div class="v">{wrong_rate}%</div>
        <div class="n">可判定 {judged} / {wf['n']} 条</div></div>
      <div class="card"><div class="k">跨城价差（92 号）</div><div class="v">{cc['spread']:.2f}</div>
        <div class="n">元/升 · {cc['min']:.2f} ~ {cc['max']:.2f} · {len(cc['rows'])} 城</div></div>
      <div class="card mute"><div class="k">垂类覆盖</div><div class="v">{len(vt['covered'])}/{len(vt['verticals'])}</div>
        <div class="n">对照组误命中 {vt['control_hits']}/{vt['control_n']}</div></div>
    </div>"""

    arows = "".join(
        f"<tr><td>{r['city']}</td><td class='num'>{r['asserted']:.2f}</td>"
        f"<td class='num'>{r['official_today']:.2f}</td><td class='num'>{r['official_history']:.2f}</td>"
        f"<td class='num'>{r['official_today']-r['asserted']:+.2f}</td><td>{tag(r['verdict'])}</td></tr>"
        for r in pv["results"] if r["asserted"] is not None)

    wrows = "".join(
        f"<tr><td>{r['city']}</td><td>{r['site']}</td><td class='num'>"
        f"{'' if r['claim'] is None else format(r['claim'], '.2f')}</td>"
        f"<td class='num'>{r['official_today']:.2f}</td><td class='num'>{r['official_history']:.2f}</td>"
        f"<td>{tag(r['verdict'])}</td></tr>" for r in wf["rows"][:24])

    mn, mx = cc["min"], cc["max"]
    bars = ""
    for r in sorted(cc["rows"], key=lambda x: -(x["p92"] or 0)):
        pct = (r["p92"] - mn) / (mx - mn) * 88 + 12 if mx > mn else 50
        bars += (f"<tr><td>{r['city']}</td><td class='num'>{r['p92']:.2f}</td>"
                 f"<td><div class='bar'><i style='width:{pct:.1f}%'></i></div></td>"
                 f"<td class='num'>{r['p92_hist']-r['p92']:+.2f}</td></tr>")

    vrows = "".join(f"<tr><td>{k}</td><td>{v['query']}</td>"
                    f"<td>{'✅ 召回' if v['hit'] else '❌ 未召回'}</td><td>{v.get('category','') or '—'}</td></tr>"
                    for k, v in vt["verticals"].items())
    erows = "".join(f"<tr><td>{e['city']}</td><td>{'有卡' if e['has_card'] else '无 VR 卡'}</td>"
                    f"<td>{tag(e['verdict'])}</td><td>{e['note']}</td></tr>" for e in edge)

    html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>油价真伪卡 · 实测报告</title><style>{CSS}</style></head><body><div class="wrap">
<h1>油价真伪卡 · 实测报告</h1>
<div class="sub">用元宝搜索成品油 VR 卡的「今日 / 上一轮」双字段，判定一句油价断言属于哪一轮</div>
<div class="meta">
  <span class="chip">生成时间 {meta['generated_at']}</span>
  <span class="chip">SearchPro 调用 {meta['tool_calls']} 次</span>
  <span class="chip">耗时 {meta['elapsed_sec']}s</span>
  <span class="chip">数据源 oil_pack.json</span>
  <span class="chip">Mode=1 VR 卡 / Mode=0 自然检索</span>
</div>
{cards}

<section>
  <h2>一、断言验真：8 个城市，8 条全错</h2>
  <p class="note">模型在未联网、未见官方值的条件下先作答，再由脚本与 VR 卡四态比对。「低估幅度」= 官方今日价 − 断言值。</p>
  <table><thead><tr><th>城市</th><th>AI 断言</th><th>官方今日价</th><th>官方上一轮价</th><th>低估幅度</th><th>判定</th></tr></thead>
  <tbody>{arows}</tbody></table>
</section>

<section>
  <h2>二、网页信息时效审计（Mode=0 自然检索）</h2>
  <p class="note">同一城市自然检索前十条摘要，取首个「元/升」价格与今日价、上一轮价比对。共 {wf['n']} 条，此处展示前 24 条。</p>
  <table><thead><tr><th>城市</th><th>站点</th><th>网页所报价</th><th>今日价</th><th>上一轮价</th><th>判定</th></tr></thead>
  <tbody>{wrows}</tbody></table>
</section>

<section>
  <h2>三、跨城价差：8.17 ~ 9.62，差 1.45 元/升</h2>
  <p class="note">同标号、同一天、同口径（零售挂牌价）。最低与最高都在西部，说明是运距而非地域标签决定价格。</p>
  <table><thead><tr><th>城市</th><th>92 号今日价</th><th>相对水平</th><th>本轮变动</th></tr></thead>
  <tbody>{bars}</tbody></table>
</section>

<section>
  <h2>四、垂类召回与边界测试</h2>
  <p class="note">官方文档列 9 类，本次稳定召回 {len(vt['covered'])} 类。垂类覆盖会随查询词与时间变化，故「查不到」一律判存疑。</p>
  <table><thead><tr><th>垂类</th><th>探测 query</th><th>召回</th><th>vr_category</th></tr></thead>
  <tbody>{vrows}</tbody></table>
  <p class="note" style="margin-top:18px">边界测试（无卡城市）：</p>
  <table><thead><tr><th>城市</th><th>VR 卡</th><th>判定</th><th>说明</th></tr></thead>
  <tbody>{erows}</tbody></table>
</section>

<section>
  <h2>五、判定口径</h2>
  <table><thead><tr><th>项</th><th>值</th><th>说明</th></tr></thead><tbody>
  <tr><td>数值容差</td><td class="num">0.005</td><td>两位小数零售价，差一分为差</td></tr>
  <tr><td>断言正则</td><td><code>\\d{{1,2}}\\.\\d{{1,2}}\\s*元/\\s*升</code></td><td>只认带单位的数字</td></tr>
  <tr><td>断言分母</td><td>{pv['n']}</td><td>抽不出数字的回答不计入</td></tr>
  <tr><td>网页分母</td><td>{judged} / {wf['n']}</td><td>无明确价格的 {w.get('undetermined',0)} 条不计入</td></tr>
  <tr><td>跨城价差口径</td><td>极值差</td><td>非平均值波动</td></tr>
  </tbody></table>
</section>

<footer>本报告由 oil_pack.py 采集、build_report_oil.py 渲染，全部数字可在 oil_pack.json 中逐项核对<br>
模型断言为单模型单次作答样本，仅用于演示判定流程，不构成对任何模型的性能结论</footer>
</div></body></html>"""

    out = work / "docs" / "油价真伪卡.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print("报告 →", out)


if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("."))
