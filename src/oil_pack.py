# -*- coding: utf-8 -*-
"""油价信息验真 · 一键采集

产出 oil_pack.json —— 文章的唯一数据源。四块证据：
  1) price_verify  8 个城市的 92 号油价断言，与 VR 卡「今日/历史」双字段比对
  2) web_freshness 5 个城市的自然检索结果（Mode=0）里，报的是今日价还是上一轮价
  3) cross_city    同标号跨城价差（证明「全国一个价」是错的）
  4) vertical      垂类召回覆盖实测（文档列的 9 类到底召回几类）

判定四态（刻意不是两态）：
  correct   等于今日价
  stale     等于历史价 —— 不是编造，是「用了一轮前的价」，本轮调价前它是真的
  mismatch  两轮都不是
  unknown   该城市无 VR 卡，判不了

用法：python src/oil_pack.py            # 在仓库根目录执行，读根目录 .env
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsa_client import WsaClient               # noqa: E402

GRADE_QUERIES = {
    "92": "92 号汽油",
    "95": "95 号汽油",
}

ASSERT_CITIES = ["南京", "杭州", "武汉", "西安", "郑州", "重庆", "天津", "沈阳"]
AUDIT_CITIES = ["北京", "上海", "广州", "成都", "哈尔滨"]
SPREAD_CITIES = ["北京", "上海", "广州", "成都", "哈尔滨", "乌鲁木齐", "西安", "沈阳",
                 "拉萨", "阿里", "三沙", "日喀则"]
# 边界测试：验证「查不到」时工具是否敢判存疑
EDGE_CITIES = ["漠河"]

VERTICALS = {
    "stock": "腾讯控股 股价", "train": "G677 次列车 时刻表", "gold": "黄金价格 每克",
    "oil": "北京 92 号汽油 价格", "weather": "北京 天气 最高温", "phone": "iPhone 17 价格",
    "car": "比亚迪 汉 价格", "exchangerate": "美元 人民币 汇率", "medical": "阿莫西林 用法用量",
}
CONTROLS = ["今天吃什么好", "推荐一部电影", "如何学习编程"]

DATE_RE = re.compile(r"#\s*日期：(.+)")
CITY_RE = re.compile(r"#\s*城市：(.+)")
BLOCK_RE = re.compile(r"国内燃油标号：(\S+?号)")
TODAY_RE = re.compile(r"今日油价（元每升）：([\d.]+)")
HIST_RE = re.compile(r"历史油价（元每升）：([\d.]+)")
PRICE_RE = re.compile(r"(\d{1,2}\.\d{1,2})\s*元/\s*升")


def parse_oil(passage: str) -> dict:
    """把油类 VR 卡解析成 {date, city, grades:{'92':{'today','history','type'}}}"""
    date = DATE_RE.search(passage)
    city = CITY_RE.search(passage)
    grades = {}
    parts = BLOCK_RE.split(passage)
    # parts = [前缀, '92号', 正文, '95号', 正文, ...]
    for i in range(1, len(parts) - 1, 2):
        name = parts[i].replace("号", "")
        body = parts[i + 1][:300]
        t = TODAY_RE.search(body)
        h = HIST_RE.search(body)
        if t:
            grades[name] = {
                "today": float(t.group(1)),
                "history": float(h.group(1)) if h else None,
            }
    return {
        "date": date.group(1).strip() if date else "",
        "city": city.group(1).strip() if city else "",
        "grades": grades,
    }


def fetch_oil(client, city: str, grade: str = "92") -> dict | None:
    q = f"{city} {GRADE_QUERIES[grade]} 价格"
    pages = client.pages(q, mode=1, cnt=10)
    for p in pages:
        if p.get("vr") and p.get("vr_category") == "oil":
            d = parse_oil(p.get("passage") or "")
            if d["grades"]:
                d["_query"] = q
                d["_site"] = p.get("site", "")
                d["_url"] = p.get("url", "")
                return d
    return None


def judge(asserted: float, off: dict) -> str:
    if not off:
        return "unknown"
    today, hist = off.get("today"), off.get("history")
    if today is not None and abs(asserted - today) < 0.005:
        return "correct"
    if hist is not None and abs(asserted - hist) < 0.005:
        return "stale"
    return "mismatch"


def load_answers(work: Path) -> list[dict]:
    out = []
    for f in sorted((work / "answers").glob("*.json")):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".", help="项目根目录（含 .env / answers）")
    ap.add_argument("--out", default="data/oil_pack.json")
    args = ap.parse_args()
    work = Path(args.work).resolve()
    work.mkdir(parents=True, exist_ok=True)

    client = WsaClient(env_file=str(work / ".env"))
    print(f"[ok] 密钥就绪（{client.secret_id[:4]}****）")
    t0 = time.time()
    pack = {"_meta": {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}}

    # ---------- 1) 断言验真 ----------
    print("\n===== 1/4 油价断言验真 =====")
    results, offs = [], {}
    for a in load_answers(work):
        model = a.get("model", "unknown")
        for item in a.get("answers", []):
            q, ans, qid = item.get("question", ""), item.get("answer", ""), item.get("qid", "")
            city = next((c for c in ASSERT_CITIES if c in q), "")
            m = PRICE_RE.search(ans)
            asserted = float(m.group(1)) if m else None
            off = fetch_oil(client, city) if city else None
            if off:
                offs[city] = off
            g = (off or {}).get("grades", {}).get("92", {})
            verdict = judge(asserted, g) if asserted is not None else "unknown"
            results.append({
                "model": model, "qid": qid, "city": city, "asserted": asserted,
                "official_today": g.get("today"), "official_history": g.get("history"),
                "date": (off or {}).get("date", ""), "verdict": verdict,
            })
            print(f"  {city:4} 断言 {asserted} | 今日 {g.get('today')} 历史 {g.get('history')} → {verdict}")
    summ = {}
    for r in results:
        summ[r["verdict"]] = summ.get(r["verdict"], 0) + 1
    pack["price_verify"] = {"results": results, "summary": summ,
                            "n": len(results), "official": {c: o for c, o in offs.items()}}
    print(f"  合计 {len(results)} 条 → {summ}")

    # ---------- 2) 网页信息时效审计 ----------
    print("\n===== 2/4 网页信息时效审计（Mode=0）=====")
    rows = []
    for city in AUDIT_CITIES:
        off = offs.get(city) or fetch_oil(client, city)
        if not off:
            continue
        offs[city] = off
        g = off["grades"].get("92", {})
        pages = client.pages(f"{city} 92 号汽油 价格 今天", mode=0, cnt=10)
        for p in pages:
            text = (p.get("content") or "")[:1200]
            prices = [float(x) for x in PRICE_RE.findall(text)]
            if not prices:
                v, claim = "undetermined", None
            else:
                claim = prices[0]
                v = judge(claim, g)
            rows.append({"city": city, "site": p.get("site", ""), "title": p.get("title", "")[:60],
                         "claim": claim, "verdict": v,
                         "official_today": g.get("today"), "official_history": g.get("history")})
        c = {}
        for r in rows:
            if r["city"] == city:
                c[r["verdict"]] = c.get(r["verdict"], 0) + 1
        print(f"  {city:4} 今日 {g.get('today')} 历史 {g.get('history')} | 网页 {len(pages)} 条 → {c}")
    wsum = {}
    for r in rows:
        wsum[r["verdict"]] = wsum.get(r["verdict"], 0) + 1
    pack["web_freshness"] = {"rows": rows, "summary": wsum, "n": len(rows)}
    print(f"  合计 {len(rows)} 条 → {wsum}")

    # ---------- 3) 跨城价差 ----------
    print("\n===== 3/4 跨城价差 =====")
    spread = []
    for city in SPREAD_CITIES:
        off = offs.get(city) or fetch_oil(client, city)
        if not off:
            print(f"  {city} 无 VR 卡")
            continue
        offs[city] = off
        g = off["grades"]
        spread.append({"city": city, "date": off["date"],
                       "p92": g.get("92", {}).get("today"),
                       "p95": g.get("95", {}).get("today"),
                       "p92_hist": g.get("92", {}).get("history")})
        print(f"  {city:5} 92={g.get('92',{}).get('today')} 95={g.get('95',{}).get('today')} 上一轮92={g.get('92',{}).get('history')}")
    p92 = [s["p92"] for s in spread if s.get("p92")]
    pack["cross_city"] = {
        "rows": spread,
        "min": min(p92) if p92 else None, "max": max(p92) if p92 else None,
        "spread": round(max(p92) - min(p92), 3) if p92 else None,
    }
    if p92:
        print(f"  92 号价差 {pack['cross_city']['spread']} 元/升（{pack['cross_city']['min']} ~ {pack['cross_city']['max']}）")

    # ---------- 4) 垂类覆盖 ----------
    print("\n===== 4/4 垂类覆盖实测 =====")
    vert = {}
    for k, q in VERTICALS.items():
        try:
            pages = client.pages(q, mode=1, cnt=10)
            vrs = [p for p in pages if p.get("vr")]
            vert[k] = {"query": q, "hit": bool(vrs),
                       "category": vrs[0].get("vr_category", "") if vrs else "",
                       "n_vr": len(vrs)}
        except Exception as e:
            vert[k] = {"query": q, "hit": False, "category": "", "n_vr": 0, "err": str(e)[:80]}
        print(f"  {k:13} {'✓' if vert[k]['hit'] else '✗'} {vert[k]['category']}")
    chits = 0
    for q in CONTROLS:
        try:
            pages = client.pages(q, mode=1, cnt=10)
            chits += 1 if [p for p in pages if p.get("vr")] else 0
        except Exception:
            pass
    pack["vertical"] = {"verticals": vert, "control_hits": chits, "control_n": len(CONTROLS),
                        "covered": [k for k, v in vert.items() if v["hit"]]}
    print(f"  覆盖 {len(pack['vertical']['covered'])}/{len(VERTICALS)} 类；对照组误命中 {chits}/{len(CONTROLS)}")

    # ---------- 5) 边界测试：查不到时说不知道 ----------
    print("\n===== 5/5 边界测试（无卡城市）=====")
    edge = []
    for city in EDGE_CITIES:
        off = fetch_oil(client, city)
        edge.append({"city": city, "has_card": bool(off),
                     "verdict": "unknown" if not off else "correct",
                     "note": "无 VR 卡，判定为存疑（不判编造）" if not off else "有卡"})
        print(f"  {city:4} {'有卡' if off else '无卡 → 判存疑'}")
    pack["edge"] = edge

    pack["_meta"]["tool_calls"] = client.calls
    pack["_meta"]["elapsed_sec"] = round(time.time() - t0, 1)
    out = work / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n调用 {client.calls} 次，耗时 {pack['_meta']['elapsed_sec']}s\n数据包 → {out}")


if __name__ == "__main__":
    main()
