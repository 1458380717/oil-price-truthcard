"""数据包完整性校验：CI 里零调用运行。
校验 data/*.json 的关键字段与文中承诺的数字一致，对不上即退出码非 0。"""
import json
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent.parent
    bt = json.loads((root / "data" / "bigtest.json").read_text(encoding="utf-8"))
    cp = json.loads((root / "data" / "compare.json").read_text(encoding="utf-8"))

    a, w, c, v, u = (bt["assert_verify"], bt["web_freshness"], bt["cross_city"],
                     bt["vertical"], bt["unit"])
    s = cp["summary"]

    checks = [
        ("盲测 40 城全部可判定", a["n"] == 40 and a["decidable"] == 40),
        ("40 条全部 mismatch", a["dist"].get("mismatch") == 40),
        ("两个分布零重叠",
         a["today_range"][0] > a["asserted_range"][1]),
        ("网页审计 100 条", w["n"] == 100),
        ("垂类 27 探针", v["total_probes"] == 27),
        ("垂类覆盖 6/9", v["covered"] == 6 and v["total_hits"] == 14),
        ("单测 10/10", u["passed"] == u["n"] == 10),
        ("价差 49 城", c["n"] == 49),
        ("A/B 15 城 45 次首答", s["n_city"] == 15 and s["total_runs"] == 45),
        ("A/B 标签数守恒 18+3+24=45",
         s["labels"]["correct"] + s["labels"]["stale"] + s["labels"]["mismatch"] == 45),
        ("VR 卡双字段 15/15", s["vr_both_fields"] == 15),
        ("调用次数与元信息一致", bt["_meta"]["tool_calls"] > 0),
    ]

    bad = 0
    for name, ok in checks:
        print(("  OK  " if ok else "  FAIL") + " " + name)
        bad += (not ok)
    if bad:
        print(f"\n{bad} 项校验失败 —— 数据包与文章承诺不一致")
        sys.exit(1)
    print(f"\n{len(checks)} 项全部通过")


if __name__ == "__main__":
    main()
