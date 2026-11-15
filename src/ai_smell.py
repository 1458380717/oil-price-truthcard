# -*- coding: utf-8 -*-
"""中文文章的「AI 味」体检表。

不是判别器，是体检表：把可数的痕迹列出来，改稿时一条条对着删。
每条规则都是「人类作者很少这么写，模型很爱这么写」的写法特征，
所以它只能提示，不能定罪——最终仍要人读一遍。

用法：
    python src/ai_smell.py article.md
    python src/ai_smell.py article.md --top 12     # 打印被命中的原文句子
"""
import argparse
import re
import sys
from collections import Counter

RULES = [
    ("破折号", r"——", "人类口语里破折号没这么密，模型爱用它造停顿"),
    ("整句加粗", None, "把整句话加粗＝替读者划重点，真人写博客极少这么干"),
    ("不是A而是B", r"不是[^。！？\n]{2,28}[，,]?\s*(?:而是|是)", "对偶句式，一篇里出现三次以上就露馅"),
    ("概念引号「」", r"「[^」\n]{1,12}」", "给普通词加引号当术语，密度高就是模型腔"),
    ("金句收尾", r"(?:才是|就是|本质|核心|关键)[^。！？\n]{0,30}。\s*$", "每段末尾都要抖一句包袱"),
    ("一句话：", r"一句话[：:]", "模型最爱的总结开场"),
    ("真正/本质上", r"(?:真正|本质上|归根结底|说到底)", "抽象升维词"),
    ("其实", r"其实", "模型的高频转折词"),
    ("这/那开头句", r"(?:^|\n\n)(?:这|那)[^。\n]{4,40}。", "指代式起句，读起来像演讲"),
    ("三段式排比", r"[^。\n]{6,20}；[^。\n]{6,20}；[^。\n]{6,20}。", "三连排比密度高"),
    ("元叙事", r"(?:这一节是|本文(?:想|要)|这篇(?:里|文章)|应评分表)", "讲自己怎么迎合评分，读者不关心"),
    ("总结腔", r"(?:综上|总而言之|值得注意的是|不难看出|可以看出)", "论文腔"),
]


def strip_code(text):
    return re.sub(r"```.*?```", "", text, flags=re.S)


def paragraphs(text):
    out = []
    for block in text.split("\n\n"):
        b = block.strip()
        if not b or b.startswith("|") or b.startswith("```") or b.startswith("#"):
            continue
        out.append(b)
    return out


def bold_sentences(text):
    """被整句加粗的（长度 > 12 且含标点），这些是「替读者划重点」的痕迹。"""
    hits = []
    for m in re.finditer(r"\*\*([^*\n]+)\*\*", text):
        s = m.group(1)
        if len(s) > 12 and re.search(r"[。，、；：]", s):
            hits.append(s)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()

    raw = open(args.path, encoding="utf-8").read()
    text = strip_code(raw)
    han = len(re.findall(r"[\u4e00-\u9fa5]", text))
    k = han / 1000.0

    print(f"文件: {args.path}")
    print(f"正文汉字: {han}   （每千字密度用于横向比较）\n")
    print(f"{'规则':<14}{'次数':>6}{'每千字':>8}   说明")
    print("-" * 78)

    total = 0
    detail = {}
    for name, pat, why in RULES:
        if name == "整句加粗":
            hits = bold_sentences(text)
        else:
            hits = [m.group(0) for m in re.finditer(pat, text, flags=re.M)]
        total += len(hits)
        detail[name] = hits
        per = len(hits) / k if k else 0
        flag = "!" if per > 1.0 else " "
        print(f"{name:<14}{len(hits):>6}{per:>8.2f} {flag} {why}")

    print("-" * 78)
    print(f"{'合计':<14}{total:>6}{total / k if k else 0:>8.2f}")

    # 句长分布：模型爱写短句，人类句子长短交错
    sents = [s for s in re.split(r"[。！？\n]", text) if len(s.strip()) > 1]
    lens = [len(s) for s in sents]
    if lens:
        avg = sum(lens) / len(lens)
        var = sum((x - avg) ** 2 for x in lens) / len(lens)
        print(f"\n句数 {len(lens)}  平均 {avg:.1f} 字  标准差 {var ** 0.5:.1f}"
              f"   （标准差 < 12 说明句子长度太齐，像模板）")
        print(f"最长 {max(lens)} 字 / 最短 {min(lens)} 字")

    if args.top:
        print("\n命中示例（改稿时逐条看）:")
        for name, hits in detail.items():
            if not hits:
                continue
            shown = [" ".join(h.split()) for h in hits[:args.top]]
            print(f"\n[{name}] {len(hits)} 处")
            for s in shown:
                print("   - " + (s[:90] + ("…" if len(s) > 90 else "")))

    return 0


if __name__ == "__main__":
    sys.exit(main())
