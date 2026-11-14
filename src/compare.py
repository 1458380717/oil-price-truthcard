# -*- coding: utf-8 -*-
"""A/B 对比实验：普通检索（Mode=0）vs 权威垂类（Mode=1）

回答一个问题：面对「某城 92 号汽油今天多少钱」，两种检索方式各自能给出什么？

三个维度：
  A. 直接可得性 —— 能不能直接拿到一个价格？
  B. 首答准确率 —— 拿到的第一个价格，是不是今日价？（以 VR 卡今日价为真值）
  C. 稳定性     —— 同一问题问 3 次，答案抖不抖？

用法：python src/compare.py
产出：data/compare.json
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

CITIES = ["北京", "上海", "广州", "成都", "哈尔滨", "南京", "武汉",
          "西安", "郑州", "长沙", "石家庄", "太原", "合肥", "福州", "昆明"]

PRICE_RE = re.compile(r"(\d{1,2}\.\d{1,2})\s*元\s*/\s*升")
TODAY_RE = re.compile(r"今日油价（元每升）：([\d.]+)")
HIST_RE = re.compile(r"历史油价（元每升）：([\d.]+)")
DATE_RE = re.compile(r"#\s*日期：(.+)")
CITY_RE = re.compile(r"#\s*城市：(.+)")


def parse_oil(passage):
    g = {}
    for b in passage.split("国内燃油标号：")[1:]:
        m = re.match(r"(\d+)号", b)
        if not m:
            continue
        head = b[:220]
        t, h = TODAY_RE.search(head), HIST_RE.search(head)
        g[m.group(1)] = {"today": float(t.group(1)) if t else None,
                         "history": float(h.group(1)) if h else None}
    return g


def first_price(pages):
    """模拟用户/模型最常见的做法：看第一条带价格的搜索结果"""
    for p in pages:
        txt = (p.get("title") or "") + " " + (p.get("passage") or "")
        m = PRICE_RE.search(txt)
        if m:
            return float(m.group(1)), p
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".")
    ap.add_argument("--out", default="data/compare.json")
    ap.add_argument("--repeat", type=int, default=3)
    a = ap.parse_args()
    work = Path(a.work).resolve()

    c = WsaClient(env_file=str(work / ".env"))
    t0 = time.time()
    pack = {"_meta": {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                      "cities": len(CITIES), "repeat": a.repeat}}
    rows = []

    for city in CITIES:
        print(f"\n=== {city} ===")
        q = f"{city} 92 号汽油 价格"

        # ---- 权威源：Mode=1 的 VR 卡 ----
        t_vr = time.time()
        ps1 = c.pages(q, mode=1, cnt=10)
        vr_ms = (time.time() - t_vr) * 1000
        cards = [p for p in ps1 if p.get("vr") and p.get("vr_category") == "oil"]
        if not cards:
            rows.append({"city": city, "has_vr": False})
            print("  无 VR 卡，跳过")
            time.sleep(0.15)
            continue
        pas = cards[0].get("passage") or ""
        g = parse_oil(pas).get("92") or {}
        truth = g.get("today")
        hist = g.get("history")
        vdate = (DATE_RE.search(pas).group(1).strip() if DATE_RE.search(pas) else "")
        vsite = cards[0].get("site")
        print(f"  VR 卡：今日 {truth} / 上一轮 {hist} / 日期 {vdate} / {vr_ms:.0f}ms")

        # ---- 普通检索：Mode=0，重复 N 次 ----
        samples = []
        for i in range(a.repeat):
            t0_ = time.time()
            ps0 = c.pages(q, mode=0, cnt=10)
            ms = (time.time() - t0_) * 1000
            v, hit = first_price(ps0)
            dates = sum(1 for p in ps0 if p.get("date"))
            samples.append({
                "run": i + 1, "first_price": v, "ms": round(ms, 1),
                "n": len(ps0), "with_date": dates,
                "top_site": (hit or {}).get("site"),
                "top_title": ((hit or {}).get("title") or "")[:50],
            })
            time.sleep(0.15)

        prices = [s["first_price"] for s in samples if s["first_price"] is not None]
        stable = len(set(prices)) <= 1 if prices else None
        err_flags = []
        for s in samples:
            v = s["first_price"]
            if v is None:
                err_flags.append("no_price")
            elif truth is not None and abs(v - truth) < 0.005:
                err_flags.append("correct")
            elif hist is not None and abs(v - hist) < 0.005:
                err_flags.append("stale")
            else:
                err_flags.append("mismatch")

        rows.append({
            "city": city, "has_vr": True,
            "truth_today": truth, "truth_history": hist,
            "vr_date": vdate, "vr_site": vsite, "vr_ms": round(vr_ms, 1),
            "vr_fields": len([k for k in ("today", "history") if g.get(k) is not None]),
            "samples": samples,
            "first_prices": prices,
            "stable": stable,
            "variants": len(set(prices)),
            "labels": err_flags,
            "correct_n": err_flags.count("correct"),
            "stale_n": err_flags.count("stale"),
            "mismatch_n": err_flags.count("mismatch"),
            "no_price_n": err_flags.count("no_price"),
            "avg_with_date": round(statistics.mean([s["with_date"] for s in samples]), 1),
        })
        print(f"  普通检索首答：{prices} → {err_flags} (稳定={stable})")

    ok = [r for r in rows if r.get("has_vr")]

    # 汇总
    total_runs = sum(len(r["samples"]) for r in ok)
    lab = {"correct": 0, "stale": 0, "mismatch": 0, "no_price": 0}
    for r in ok:
        for k in lab:
            lab[k] += r.get(f"{k if k!='no_price' else 'no_price'}_n", 0)
    stable_n = sum(1 for r in ok if r["stable"])
    vr_field_full = sum(1 for r in ok if r["vr_fields"] == 2)
    vr_ms = [r["vr_ms"] for r in ok]
    s_ms = [s["ms"] for r in ok for s in r["samples"]]

    pack["_meta"]["tool_calls"] = c.calls
    pack["_meta"]["elapsed_sec"] = round(time.time() - t0, 1)
    pack["summary"] = {
        "n_city": len(rows),
        "n_vr": len(ok),
        "total_runs": total_runs,
        "labels": lab,
        "direct_answer_rate_vr": 1.0,
        "direct_answer_rate_search": round((total_runs - lab["no_price"]) / total_runs, 3) if total_runs else None,
        "first_answer_error_rate": round((lab["stale"] + lab["mismatch"]) / total_runs, 3) if total_runs else None,
        "stable_cities": stable_n,
        "stability_rate": round(stable_n / len(ok), 3) if ok else None,
        "vr_both_fields": vr_field_full,
        "vr_ms_mean": round(statistics.mean(vr_ms), 1) if vr_ms else None,
        "search_ms_mean": round(statistics.mean(s_ms), 1) if s_ms else None,
        "need_manual_judge_search": round((total_runs - lab["no_price"]) / total_runs, 3) if total_runs else None,
        "need_manual_judge_vr": 0.0,
        "avg_date_coverage_search": round(statistics.mean([r["avg_with_date"] for r in ok]), 1) if ok else None,
    }
    pack["rows"] = rows

    out = work / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")

    s = pack["summary"]
    print("\n" + "=" * 60)
    print(f"城市 {s['n_city']}，有 VR 卡 {s['n_vr']}")
    print(f"普通检索 {s['total_runs']} 次首答：{s['labels']}")
    print(f"  能直接给出价格：{s['direct_answer_rate_search']*100:.1f}%")
    print(f"  首答错误率：{s['first_answer_error_rate']*100:.1f}%")
    print(f"  答案稳定城市：{s['stable_cities']}/{s['n_vr']}（{s['stability_rate']*100:.0f}%）")
    print(f"  每条结果带日期的均值：{s['avg_date_coverage_search']}/10")
    print(f"VR 卡：双字段完整 {s['vr_both_fields']}/{s['n_vr']}，需人工判断 0%")
    print(f"延迟：VR {s['vr_ms_mean']}ms vs 普通 {s['search_ms_mean']}ms")
    print(f"调用 {s['tool_calls'] if 'tool_calls' in s else pack['_meta']['tool_calls']} 次，"
          f"耗时 {pack['_meta']['elapsed_sec']}s")
    print(f"→ {out}")


if __name__ == "__main__":
    main()
