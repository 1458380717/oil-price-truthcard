# 油价真伪卡 · oil-price-truthcard

给一句「今天 92 号多少钱」的 AI 回答做验真：判断它报的是**今天的价**、**上一轮的价**，还是**两者都不是**。

核心区别在于：它不把所有错误都叫「幻觉」。上一轮的价当时是真的，工具会判 `stale`（已过期），而不是 `mismatch`（不符）。把真话判成谎话的工具，比没有工具更糟。

![实测报告页](shots/03_report.png)

## 它解决什么

2026 年 11 月这轮调价，全国 92 号汽油每升下调 0.52 元。同一天，AI 被问到「北京今天 92 号多少钱」时回答 7.85 元——而牌子上是 8.37 元。

8 个城市问下来，8 条回答全在 7.75~7.90 之间。这不是随机错误，是记忆整体停在了更早的年代。

网上的情况更麻烦：50 条搜索结果里，能判定的 27 条有 **70.4%** 不是今天的价。

## 数据从哪来

腾讯云元宝搜索 `SearchPro`，`Mode=1`（权威垂直信源），筛 `vr_category=oil` 的成品油 VR 卡。这类卡有个关键结构——**同一条数据里同时给出今日价和上一轮价**：

```
# 【北京今日油价】成品油零售价
# 日期：11月14日油价
# 城市：北京

国内燃油标号：92号
今日油价（元每升）：8.37
历史油价（元每升）：8.89
```

有对照组，判定就不用猜，是机械可比的。

## 四态判定

```python
def judge(asserted, today, history):
    if today is not None and abs(asserted - today) < 0.005:
        return "correct"     # 属实
    if history is not None and abs(asserted - history) < 0.005:
        return "stale"       # 已过期，曾经是真的
    return "mismatch"        # 两轮都不是
```

外加一个 `unknown`：城市没有 VR 卡时判存疑，不降级、不借邻省价。**查不到不等于假。**

## 快速开始

```bash
git clone https://github.com/yourname/oil-price-truthcard
cd oil-price-truthcard

cp .env.example .env          # 填 SecretId / SecretKey

python src/oil_pack.py        # 采集 → data/oil_pack.json（36 次调用，约 0.72 元）
python src/build_report.py    # 渲染 → docs/油价真伪卡.html
python src/build_article.py   # 出文章 → article.md
```

零第三方依赖。TC3-HMAC-SHA256 签名用标准库手写，不装腾讯云 SDK——为的是在干净环境里 clone 下来就能跑。Python 3.10+。

**密钥获取**：控制台开通元宝搜索标准版 → 访问管理 → API 密钥管理 → 新建密钥。腾讯云 2023 年起关闭 SecretKey 查询，只在创建时显示一次，务必当场存好。

## 实测结果

| 指标 | 值 |
|---|---|
| 断言验真（盲测） | 40 城 **40 条全错**，报价 7.74~8.10 与官方 8.26~9.48 **零重叠** |
| 网页时效 | 100 条审计，**76.7% 不是今日价**；标题去重后 89 条独立内容，**79.2%** |
| 转载去重 | 11 组同标题跨站转载，去重后错误率不降反升 |
| A/B 对比 | 15 城首答仅 **40%** 是今日价，VR 卡 **100%** 双字段 |
| 服务 | `python src/server.py` 本地 Web，四态判定 |
| 跨城价差 | 12 城极差 **1.45 元/升**（乌鲁木齐 8.17 ~ 阿里 9.62），一箱差 72.5 元 |
| 垂类召回 | 27 探针覆盖 6/9 类，oil 类仅 1/3 |
| 单元测试 | 10/10 通过，含浮点边界用例；CI 零密钥复核数据包 |
| 口径 | 全部数字标分母，见 `article.md` 第六节 |
| 边界 | 漠河无 VR 卡，判 `unknown` |
| 成本 | 149 次调用，约 3 元 |

完整明细见 `data/oil_pack.json`（带 `_meta.generated_at` 与 `tool_calls`）和 `docs/油价真伪卡.html`。

## 踩坑

1. **`Cnt` 只接受 10/20/30/40/50**。传 5 返回 `InvalidParameter: illegal Cnt`，但 HTTP 仍是 200，错误在 `Response.Error` 里、`Pages` 为空。不显式检查就会拿到空结果，额度照扣。
2. **`Pages` 是字符串数组**，每个元素要二次 `json.loads`。
3. **`Mode` 不传不带 VR 卡**，`vr` 全为 false。测垂类覆盖时最容易栽这条。
4. **`$DATE` 必须用 UTC**，北京时间 23:00 后属于 UTC 的「昨天」，报 `SignatureFailure` 却不说是日期问题。
5. **`历史油价` 是上一调价周期的价**，不是昨天的价。当「昨天」用，时效口径整个就错了。

## 不适用的场景

油价离散、行政调价、有唯一官方值，判定才干净。股价、汇率是连续变量，两条信息不一致不等于谁错，得按时间容差判，这套比对器搬不过去。

样本也有限：8 条断言是单模型单次作答，只能说明「这类查询上记忆型回答不可信」，不能推「某模型一定错」。

## 目录

```
src/server.py            本地 Web 服务（四态判定）
src/bigtest.py           大规模采集（40 城 + 100 条 + 27 探针）
src/compare.py           A/B 对比实验
src/build_dist.py        分布图生成
src/oil_pack.py          12 城快测（首轮）
src/wsa_client.py        SearchPro 客户端，TC3 签名手写
src/build_report.py      数据包 → 单文件 HTML 报告
answers/                 待验真的模型回答（JSON）
data/oil_pack.json       一次真实采集的完整数据包
docs/                    渲染好的报告页
shots/                   实测截图
```

MIT License.
