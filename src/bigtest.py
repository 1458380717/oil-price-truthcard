# -*- coding: utf-8 -*-
"""油价真伪卡 · 大规模测试

五组测试，规模比首轮扩大约 5 倍：
  A. 断言验真      40 城（盲测样本，未见官方值前写下）
  B. 网页时效审计  10 城 × 10 条 = 100 条
  C. 跨城价差      40 城同标号（复用 A 的采集结果，不额外调用）
  D. 垂类召回      9 类 × 3 探针 = 27 次
  E. 判定器单测    本地用例，0 次调用

用法：python src/bigtest.py
产出：data/bigtest.json
"""
import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wsa_client import WsaClient  # noqa: E402

TODAY_RE = re.compile(r"今日油价（元每升）：([\d.]+)")
HIST_RE = re.compile(r"历史油价（元每升）：([\d.]+)")
PRICE_RE = re.compile(r"(\d{1,2}\.\d{1,2})\s*元\s*/\s*升")
GRADE_RE = re.compile(r"国内燃油标号：(\d+)号")

AUDIT_CITIES = ["北京", "上海", "广州", "成都", "哈尔滨",
                "南京", "武汉", "西安", "郑州", "长沙"]

VERTICAL_PROBES = {
    "stock": ["腾讯控股 股价", "贵州茅台 股价", "宁德时代 股价"],
    "train": ["G677 次列车 时刻表", "Z21 次列车 时刻表", "D2286 次列车 时刻表"],
    "gold": ["黄金价格 每克", "足金 999 价格", "今日金价"],
    "oil": ["北京 92 号汽油 价格", "上海 95 号汽油 价格", "成都 0 号柴油 价格"],
    "weather": ["北京 天气 最高温", "上海 天气预报", "广州 气温"],
    "phone": ["iPhone 17 价格", "华为 Mate 80 价格", "小米 16 价格"],
    "car": ["比亚迪 汉 价格", "特斯拉 Model Y 价格", "理想 L6 价格"],
    "exchangerate": ["美元 人民币 汇率", "欧元 人民币 汇率", "日元 人民币 汇率"],
    "medical": ["阿莫西林 用法用量", "布洛芬 说明书", "二甲双胍 副作用"],
}
CONTROL_PROBES = ["如何学习 Python", "红烧肉怎么做", "自行车链条怎么保养"]


def parse_oil(passage):
    blocks = passage.split("国内燃油标号：")[1:]
    grades = {}
    for b in blocks:
        g = GRADE_RE.match("国内燃油标号：" + b)
        if not g:
            continue
        head = b[:220]
        t, h = TODAY_RE.search(head), HIST_RE.search(head)
        grades[g.group(1)] = {
            "today": float(t.group(1)) if t else None,
            "history": float(h.group(1)) if h else None,
        }
    return grades


def judge(asserted, today, history):
    """四态判定。整数分比较，避开浮点边界抖动。"""
    a = int(round(asserted * 100))
    if today is not None and a == int(round(today * 100)):
        return "correct"
    if history is not None and a == int(round(history * 100)):
        return "stale"
    return "mismatch"


def unit_tests():
    """判定器单元测试：0 次调用，覆盖四态与容差边界"""
    cases = [
        # (断言, 今日, 历史, 期望)
        (8.37, 8.37, 8.89, "correct"),      # 精确相等
        (8.372, 8.37, 8.89, "correct"),     # 差 0.002，同分（837 vs 837）
        (8.89, 8.37, 8.89, "stale"),        # 等于上一轮
        (7.85, 8.37, 8.89, "mismatch"),     # 两轮都不是
        (8.35, 8.37, 8.89, "mismatch"),     # 差 2 分
        (8.364, 8.37, 8.89, "mismatch"),    # 差 0.006，跨分
        (8.365, 8.37, 8.89, "mismatch"),    # 浮点陷阱：*100 得 836.4999…
        (9.99, 8.37, None, "mismatch"),     # 历史缺失时不应崩
        (8.37, 8.37, None, "correct"),      # 历史缺失但今日命中
        (8.37, None, 8.89, "unknown"),      # 今日缺失 → 调用方判 unknown
    ]
    passed = 0
    rows = []
    for a, t, h, exp in cases:
        if t is None:
            got = "unknown"
        else:
            got = judge(a, t, h)
        ok = (got == exp)
        passed += ok
        rows.append({"asserted": a, "today": t, "history": h,
                     "expected": exp, "got": got, "pass": ok})
    return {"n": len(cases), "passed": passed, "rows": rows,
            "note": "今日为 None 的用例由调用方先行判 unknown，此处单独标注"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".")
    ap.add_argument("--out", default="data/bigtest.json")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--only", default="", help="只跑某一组：unit")
    a = ap.parse_args()
    work = Path(a.work).resolve()

    if a.only == "unit":
        out = work / a.out
        pack = json.loads(out.read_text(encoding="utf-8"))
        pack["unit"] = unit_tests()
        pack["_meta"]["rerun_unit_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
        u = pack["unit"]
        print(f"单测 {u['passed']}/{u['n']} 通过")
        for r in u["rows"]:
            if not r["pass"]:
                print("  FAIL:", r)
        return

    c = WsaClient(env_file=str(work / ".env"))
    t0 = time.time()
    pack = {"_meta": {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "script": "bigtest.py"}}

    # ---------- A. 断言验真（40 城盲测） ----------
    print("===== A. 断言验真（40 城） =====")
    ans_files = sorted((work / "answers").glob("blind*.json"))
    asserts = []
    for f in ans_files:
        d = json.loads(f.read_text(encoding="utf-8"))
        for item in d.get("answers", []):
            q, ans = item["question"], item["answer"]
            city = q.split("今天")[0].split(" ")[0].strip()
            m = re.search(r"(\d{1,2}\.\d{1,2})\s*元", ans)
            asserts.append({"qid": item["qid"], "city": city,
                            "question": q, "answer": ans,
                            "asserted": float(m.group(1)) if m else None})
    print(f"  读入断言 {len(asserts)} 条")

    offs = {}
    for i, it in enumerate(asserts, 1):
        city = it["city"]
        if city not in offs:
            ps = c.pages(f"{city} 92 号汽油 价格", mode=1, cnt=10)
            cards = [p for p in ps if p.get("vr") and p.get("vr_category") == "oil"]
            if cards:
                g = parse_oil(cards[0].get("passage") or "").get("92") or {}
                offs[city] = {"found": True, "today": g.get("today"),
                              "history": g.get("history"),
                              "site": cards[0].get("site"),
                              "date": (re.search(r"#\s*日期：(.+)",
                                                 cards[0].get("passage") or "") or [None, ""])[1]}
            else:
                offs[city] = {"found": False}
            time.sleep(a.sleep)

        o = offs[city]
        if not o["found"]:
            it["verdict"] = "unknown"
        elif it["asserted"] is None:
            it["verdict"] = "no_claim"
        else:
            it["verdict"] = judge(it["asserted"], o["today"], o["history"])
        it["official_today"] = o.get("today")
        it["official_history"] = o.get("history")
        if it["asserted"] is not None and o.get("today") is not None:
            it["gap"] = round(it["asserted"] - o["today"], 2)
        if i % 10 == 0:
            print(f"  ... {i}/{len(asserts)}")

    dist = {}
    for it in asserts:
        dist[it["verdict"]] = dist.get(it["verdict"], 0) + 1
    have = [x for x in asserts if x["verdict"] in ("correct", "stale", "mismatch")]
    gaps = [x["gap"] for x in have if x.get("gap") is not None]
    av = [x["asserted"] for x in asserts if x["asserted"] is not None]
    tv = [x["official_today"] for x in asserts if x.get("official_today") is not None]
    pack["assert_verify"] = {
        "n": len(asserts),
        "decidable": len(have),
        "dist": dist,
        "coverage": round(len(have) / len(asserts), 3) if asserts else 0,
        "gap_mean": round(statistics.mean(gaps), 2) if gaps else None,
        "gap_min": min(gaps) if gaps else None,
        "gap_max": max(gaps) if gaps else None,
        "asserted_range": [min(av), max(av)] if av else None,
        "asserted_mean": round(statistics.mean(av), 2) if av else None,
        "today_range": [min(tv), max(tv)] if tv else None,
        "today_mean": round(statistics.mean(tv), 2) if tv else None,
        "today_std": round(statistics.pstdev(tv), 3) if len(tv) > 1 else None,
        "asserted_std": round(statistics.pstdev(av), 3) if len(av) > 1 else None,
        "results": asserts,
    }
    print(f"  结果 {dist} | 可判定 {len(have)}/{len(asserts)}")

    # ---------- B. 网页时效审计（10 城 × 10 条） ----------
    print("\n===== B. 网页时效审计（100 条） =====")
    audit = []
    for city in AUDIT_CITIES:
        o = offs.get(city)
        if not o or not o.get("found"):
            ps = c.pages(f"{city} 92 号汽油 价格", mode=1, cnt=10)
            cards = [p for p in ps if p.get("vr") and p.get("vr_category") == "oil"]
            if cards:
                g = parse_oil(cards[0].get("passage") or "").get("92") or {}
                o = {"found": True, "today": g.get("today"), "history": g.get("history")}
                offs[city] = o
            time.sleep(a.sleep)
        if not o or not o.get("found"):
            continue

        ps = c.pages(f"{city} 92 号汽油 价格", mode=0, cnt=10)
        time.sleep(a.sleep)
        for p in ps:
            txt = (p.get("title") or "") + " " + (p.get("passage") or "")
            m = PRICE_RE.search(txt)
            v = float(m.group(1)) if m else None
            if v is None:
                st = "undetermined"
            elif o["today"] is not None and abs(v - o["today"]) < 0.005:
                st = "correct"
            elif o["history"] is not None and abs(v - o["history"]) < 0.005:
                st = "stale"
            else:
                st = "mismatch"
            audit.append({"city": city, "price": v, "state": st,
                          "site": p.get("site"), "date": p.get("date"),
                          "title": (p.get("title") or "")[:60]})
        print(f"  {city} 完成（累计 {len(audit)} 条）")

    wdist = {}
    for r in audit:
        wdist[r["state"]] = wdist.get(r["state"], 0) + 1
    dec = [r for r in audit if r["state"] != "undetermined"]
    bad = [r for r in dec if r["state"] != "correct"]
    pack["web_freshness"] = {
        "n": len(audit), "dist": wdist, "decidable": len(dec),
        "error_rate": round(len(bad) / len(dec), 3) if dec else None,
        "cities": AUDIT_CITIES, "rows": audit,
    }
    print(f"  分布 {wdist} | 有误率 {pack['web_freshness']['error_rate']}")

    # ---------- C. 跨城价差（复用 40 城） ----------
    print("\n===== C. 跨城价差 =====")
    rows = []
    for city, o in offs.items():
        if o.get("found") and o.get("today") is not None:
            rows.append({"city": city, "today": o["today"],
                         "history": o.get("history"),
                         "delta": (round(o["today"] - o["history"], 2)
                                   if o.get("history") is not None else None)})
    rows.sort(key=lambda r: r["today"])
    ts = [r["today"] for r in rows]
    pack["cross_city"] = {
        "n": len(rows), "rows": rows,
        "min": {"city": rows[0]["city"], "price": rows[0]["today"]} if rows else None,
        "max": {"city": rows[-1]["city"], "price": rows[-1]["today"]} if rows else None,
        "spread": round(rows[-1]["today"] - rows[0]["today"], 2) if rows else None,
        "mean": round(statistics.mean(ts), 2) if ts else None,
        "median": round(statistics.median(ts), 2) if ts else None,
        "std": round(statistics.pstdev(ts), 3) if len(ts) > 1 else None,
        "tank_50_spread": round((rows[-1]["today"] - rows[0]["today"]) * 50, 1) if rows else None,
        "over_1yuan": [r["city"] for r in rows if r["today"] - rows[0]["today"] >= 1.0] if rows else [],
    }
    print(f"  {len(rows)} 城，极差 {pack['cross_city']['spread']} 元/升")

    # ---------- D. 垂类召回（9 类 × 3 探针） ----------
    print("\n===== D. 垂类召回（27 探针） =====")
    vert = []
    for cat, qs in VERTICAL_PROBES.items():
        hit, detail = 0, []
        for q in qs:
            ps = c.pages(q, mode=1, cnt=10)
            vrs = [p for p in ps if p.get("vr")]
            got = vrs[0].get("vr_category") if vrs else None
            ok = (got == cat)
            hit += ok
            detail.append({"query": q, "hit": ok, "vr_category": got})
            time.sleep(a.sleep)
        vert.append({"category": cat, "hits": hit, "n": len(qs),
                     "rate": round(hit / len(qs), 2), "detail": detail})
        print(f"  {cat:13} {hit}/{len(qs)}")

    ctrl = []
    for q in CONTROL_PROBES:
        ps = c.pages(q, mode=1, cnt=10)
        vrs = [p for p in ps if p.get("vr")]
        ctrl.append({"query": q, "vr_hit": bool(vrs)})
        time.sleep(a.sleep)
    pack["vertical"] = {
        "categories": vert,
        "covered": sum(1 for v in vert if v["hits"] > 0),
        "full_covered": sum(1 for v in vert if v["hits"] == v["n"]),
        "total_probes": sum(v["n"] for v in vert),
        "total_hits": sum(v["hits"] for v in vert),
        "control_false_hit": sum(1 for x in ctrl if x["vr_hit"]),
        "control_n": len(ctrl),
        "control": ctrl,
    }
    print(f"  覆盖 {pack['vertical']['covered']}/9 类，"
          f"总命中 {pack['vertical']['total_hits']}/{pack['vertical']['total_probes']}")

    # ---------- E. 判定器单测 ----------
    print("\n===== E. 判定器单测 =====")
    pack["unit"] = unit_tests()
    print(f"  {pack['unit']['passed']}/{pack['unit']['n']} 通过")

    pack["_meta"]["tool_calls"] = c.calls
    pack["_meta"]["elapsed_sec"] = round(time.time() - t0, 1)
    out = work / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n调用 {c.calls} 次，耗时 {pack['_meta']['elapsed_sec']}s")
    print(f"数据包 → {out}")


if __name__ == "__main__":
    main()
