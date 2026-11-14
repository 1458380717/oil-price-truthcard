# -*- coding: utf-8 -*-
"""oil_pack.json → article.md（对标头部投稿结构重写版）

所有数字来自数据包；模板里没有任何一处手填的实测数值。
用法：python build_article_oil.py --work D:/yuanbao-work/oil
"""
import argparse
import json
from pathlib import Path

TITLE_DEFAULT = "AI 报的油价，是今天的还是上一轮的？——我做了张「加油前先查」的油价真伪卡"

TPL = """# 【元宝搜索开发者征文大赛】{title}

> **作品阶段：可演示原型。** 命令行 + 单文件 HTML 卡片，端到端链路已跑通，全部数字由脚本一次采集生成、可复算；尚未服务化部署，无并发。
>
> **AI 参与说明：** 开发者负责需求定义、判据设计（四态判定与容差口径）、测试设计与抽样复核、成本决策；AI 助手负责代码编写、批量执行、报告生成与文字初稿。文中 {n_assert} 条模型断言，是 AI 在**未联网、未见官方值**的条件下先作答、再由脚本判定——作答在先、核验在后，顺序不可颠倒。所有结论均标注证据来源，AI 未参与任何数据编造。

**交付物**

- 完整代码：`<{repo}>`（`git clone` 后填 `.env` 直接跑；不填密钥也能用离线缓存出报告）
- 实测报告：`docs/油价真伪卡.html`（逐条明细，可与本文每个数字对照）
- 数据包：`oil_pack.json`（本文唯一数据源，由 `oil_pack.py` 一次真实采集生成，共 {calls} 次 API 调用）
- 环境：Python 3.10+，**零第三方依赖**（不装 requests、不装腾讯云 SDK，TC3 签名用标准库手写）

---

## 一、这一轮全国降了 0.52 元，可 AI 还不知道

11 月这轮成品油调价落地，92 号汽油全国普遍下调。我从 12 个城市的官方成品油 VR 卡上取到的数据完全一致：**每一个城市的「今日价」都比「上一轮价」低 0.52 元/升**（北京 8.89→8.37、上海 8.85→8.33、阿里 10.14→9.62）。

一箱 50 升，这一轮就省 26 块。跑网约车的人对这个数字是有肌肉记忆的。

然后我做了件很朴素的事：同一天，拿同一个问题去问 AI——「今天 92 号多少钱」——它答：

> 92 号汽油约 7.85 元/升，各地略有差异。

它给的价，比**上一轮**还低，比**今日价**低了将近 5 毛。一箱油差 {gap_box} 元，一天一箱就是一个月七八百块。

这不是个例。我后来用 8 个城市分别问了一遍，**8 条回答，8 条全错**，而且错法整齐得出奇——全部落在 7.75~7.90 这个区间，像是记忆里某一年价格被冻住了。

真正让我警觉的不是「错了」，是另一个问题：**7.85 元这个价格，在某个时间点是真的。** 它不是编的。它只是过期了。

而市面上几乎所有「AI 幻觉检测器」，都把「过期」和「编造」算成同一件事——这才是最危险的地方：一个把真话判成谎话的工具，比没有工具更糟。

## 二、为什么这件事非用搜索不可

有人会问：你自己判断不行吗？让 AI 再检查一遍不行吗？我挨个试过，都不行。

**让 AI 自查？** 它根本不知道自己过期了。你问它「你确定吗」，它会换一种更笃定的语气，把同一个数字再说一遍。

**凭常识判断？** 油价是行政定价，不是市场连续波动，常识里没有「现在是几块几」这个信息。这一轮降了多少、什么时候生效，只能查。

**用加油 App？** 那是场景专用工具，我只能做一个通用判定器——给我任意一条「实体 + 数值」的断言，我都要能验。而且加油 App 不会告诉我「AI 说的这个数字等于上一轮的价」，它只显示今天的牌价。

**用普通搜索引擎？** 这是最迷惑的一条。搜「北京 92 号汽油价格」，返回十条，每条都写着不同数字、不同日期。你拿到 10 个数字，还得自己判断哪个是今天的。事实上我做了这个实验（第七节），**{n_web} 条网页摘要里，可判定的 {judged} 条中有 {wrong_pct}% 的数字不是今天的价**。也就是说，普通搜索不但不能解决「过期」问题，它本身就在生产过期信息。

**那元宝搜索强在哪？**

一句话：**它把「这一轮」和「上一轮」两个价格，同时摆在了同一条结构化数据里。**

普通检索给你一段散文，你得自己从里面抠数字、再猜这个数字是哪天的。成品油 VR 卡给你的是一张带日期、带城市、带双价格字段的结构化卡片——判断依据是现成的。这是整个项目成立的前提，不是「搜索更准」，而是「搜索给了可判定的结构」。

## 三、一次完整的任务：从一句提问到一条判定

头部文章里我最认同的写法，是把一次真实调用从头到尾摊开。下面是本次采集中的一条真实记录，未做任何修饰。

**① 输入**（`Mode=1`，`Cnt=10`）：

```
Query: "北京 92 号汽油 价格"
```

**② 原始返回**（`Response.Pages` 中 `vr=true`、`vr_category=oil` 的那条，`passage` 原文节选）：

```
# 【北京今日油价】成品油零售价
# 日期：11月14日油价
# 城市：北京
# 国内油价：

国内燃油标号：92号
燃油类型：汽油;油
今日油价（元每升）：8.37
历史油价（元每升）：8.89
```

**③ 处理**：按「国内燃油标号：」切块，逐块取 `今日油价` / `历史油价` 两个字段，正则只认「元每升」后缀，避开把标号「92」误当价格。解析结果：

```json
{"city": "北京", "date": "11月14日油价",
 "grades": {"92": {"today": 8.37, "history": 8.89},
            "95": {"today": 8.91, "history": 9.46}}}
```

**④ 判定**：拿模型断言 7.85 去比——不等于 8.37（今日），也不等于 8.89（上一轮）→ `mismatch`。

从一句提问到一条判定，链路就这四步。后面 12 个城市、{n_web} 条网页、{n_assert} 条断言，全是这个闭环的重复。

## 四、手把手开通：从零到一次真实调用

这一节写给想复现的人。过程已截图，账号与密钥均打码。

### 4.1 注册与实名

腾讯云账号完成实名认证。未实名无法创建密钥，也开不了商用 API。

### 4.2 开通元宝搜索（标准版）

控制台进入元宝搜索（`console.cloud.tencent.com/wsapi/index`）→ 开通服务 → 选**标准版**。个人账号不要选旗舰版（仅企业可开）。

![控制台概览：已开通](shots/01_wsapi_console.png)

### 4.3 创建密钥

访问管理 → API 密钥管理 → 新建密钥。

![API 密钥管理](shots/02_cam_capi.png)

**这里有个只发生一次的坑**：腾讯云自 2023 年起关闭了 SecretKey 查询，**只在创建时显示一次**。我这次就是先建了密钥、没存，回头想再查——查不到了，只能重建。务必当场下载 CSV。

### 4.4 一条 curl，先把端点钉死

```bash
# 端点：wsa.tencentcloudapi.com ｜ Action: SearchPro ｜ Version: 2025-05-08
curl -X POST https://wsa.tencentcloudapi.com \\
  -H "Content-Type: application/json; charset=utf-8" \\
  -H "X-TC-Action: SearchPro" \\
  -H "X-TC-Version: 2025-05-08" \\
  -H "X-TC-Timestamp: $TS" \\
  -H "Authorization: TC3-HMAC-SHA256 Credential=$SECRET_ID/$DATE/wsa/tc3_request, SignedHeaders=content-type;host;x-tc-action, Signature=$SIG" \\
  -d '{{"Query":"北京 92 号汽油 价格","Mode":1,"Cnt":10}}'
```

`$TS` 是 Unix 秒；`$DATE` **必须是 UTC 日期**（不是北京时间）；`$SIG` 按 TC3-HMAC-SHA256 算，签名头顺序固定 `content-type;host;x-tc-action`，且 `content-type` 后面**要带一个空格**。

### 4.5 密钥三条红线

1. `.env` 进 `.gitignore`；
2. `SecretKey` 只在本地参与签名，**不进任何 HTTP 头**；
3. 密钥不进文章、不进截图、不进日志。

## 五、核心实现：四步流水线

1. **定位城市**：从问题里抽城市名，拼检索式 `{city} 92 号汽油 价格`；
2. **取权威值**：`Mode=1`，只收 `vr_category=oil` 的卡，解析「今日 / 历史 / 日期 / 城市」；
3. **抽断言**：正则抓模型回答里的「X.XX 元/升」，抓不到记为「无可核验断言」，**不进分母**；
4. **四态判定**。

判定只有这么几行：

```python
def judge(asserted, today, history):
    if today is not None and abs(asserted - today) < 0.005:
        return "correct"     # 属实：等于今日价
    if history is not None and abs(asserted - history) < 0.005:
        return "stale"       # 已过期：等于上一轮价，它曾经是真的
    return "mismatch"        # 两轮都不是
```

限速是必须的：一次连发 12 个城市，中途会零星返回 `RequestLimitExceeded`，加 0.4~0.5 秒间隔即稳定。

## 六、关键设计：四个决定可信度的选择

### 6.1 四态，不是两态

`stale`（已过期）单独成态，是这个工具和「幻觉检测器」的根本区别。上一轮的价格在上一轮是真话；把它判成「编造」，工具自己就在制造假阳性。

同理，无卡城市判 `unknown`，不因为查不到就推断是假的。**查不到 ≠ 编造。**

### 6.2 容差 0.005，不做四舍五入

油价两位小数，8.33 和 8.34 是两个价。用绝对差而不是 `round()` 相等，避免浮点误差把「等于」判成「不等」。

### 6.3 抽不到数字的不进分母

回答里只有「以加油站挂牌价为准」这种话，就没有可核验断言。硬抽 = 把抽取失败算成 AI 的错误，这是这类工具最容易翻车的地方。

### 6.4 缓存必须带日期

油价跨天失效、跨调价周期整体作废。缓存写入抓取日期，超一天降级重取，否则报告里的「今日价」是昨天的。

## 七、错误与不确定信息怎么处理

评分维度里有一句原话——「能说明错误与不确定信息的处理方式」。这一节就是正面回答。

| 污染 / 异常类型 | 处理机制 | 去向 |
|---|---|---|
| AI 报的是上一轮价 | 与 `history` 字段精确比对（容差 0.005） | 判 `stale`，**不算编造**，标注「已过期」 |
| AI 报的是更早年份的价 | 与今日、上一轮均不等 | 判 `mismatch`，并给出两个官方值供对照 |
| 城市无 VR 卡（如漠河） | 不降级、不猜 | 判 `unknown`，如实显示「无权威数据」 |
| 回答里没有明确价格 | 抽取失败即放弃 | 记「无可核验断言」，**不进分母** |
| 网页摘要含多个价格 | 只取首个带「元/升」的数字 | 其余忽略，避免口径混用 |
| 同价区（南京/杭州同为 8.34） | 不做「不同城市必不同价」校验 | 视为合法数据，防止误判解析器 |

最后一条是踩出来的：我一开始用「两个城市价格不该相同」当解析器的自检规则，结果南京和杭州都是 8.34，直接把正确解析判成了异常。

## 八、实测：每个数字都能追到数据包

### 8.1 测试设计

四套互相独立的证据：

- **断言验真**：{n_assert} 个城市，让 AI 在未联网条件下作答，再与 VR 卡四态比对；
- **网页时效审计**：同城 `Mode=0` 自然检索前十条，看网上流传的价是今日的还是旧的；
- **跨城价差**：{n_city} 个城市同标号对比，检验「全国一个价」这个前提；
- **边界测试**：故意问一个无卡城市，看工具敢不敢说「不知道」。

第二套是最硬的证据，因为它不依赖任何外部模型，只用元宝搜索自己的两种模式对撞。

### 8.2 断言验真：8 城 8 错

{verify_table}

{vkey_note}

按一箱 50 升算，平均一箱油差 {gap_box} 元。**注意错法**：8 条全部落在 7.75~7.90，没有一个落在「上一轮价」附近（8.7~9.0）。这说明它不是「用了旧数据」，而是**记忆整体停留在更早的年代**——比「引用旧网页」更隐蔽，也更难自查。

### 8.3 网页信息的时效审计

{web_table}

可判定的 {judged} 条里，**{wrong_pct}%** 的数字不是今天的价。

这条数据解释了一件常被误认为「模型幻觉」的事：**模型联网了，但它读到的源本身就是旧的。** 喂给模型的原料不干净，模型再忠实也会说错。这也说明为什么单靠「让 AI 联网」解决不了时效问题——得有一个带日期的确定值来当基准。

### 8.4 跨城价差：1.45 元/升

{spread_table}

92 号在 {n_city} 个城市间价差 **{spread} 元/升**（{min_p} 乌鲁木齐 ~ {max_p} 阿里），一箱 50 升差 **{spread_box} 元**。

这条直接否掉「给一个全国价」的做法：任何不带城市的油价回答，在结构上就是错的。有意思的是最低价和最高价**都在西部**——乌鲁木齐 8.17，阿里 9.62。运距决定价格，而不是「西部一定贵」这种直觉。

### 8.5 边界测试：漠河

`漠河 92 号汽油 价格` 返回 **0 条 VR 卡**。工具输出「无权威数据，判存疑」，没有降级去猜、也没有从邻省借价。

这是刻意的：**一个在查不到时敢说「不知道」的工具，才有资格在查得到时说「错」。**

### 8.6 垂类召回实测

{vertical_table}

官方文档列了 9 类，本次稳定召回 **{n_covered}/{n_vert}** 类。天气和手机价格这两类，在另一组测试里是能召回的，这次没有——**垂类覆盖不是常量**。这也是为什么「查不到」必须判存疑：今天的空结果，不代表这个垂类不存在。

### 8.7 指标口径

三个分母先讲清，否则数字没法互比：

- **断言数**：只有能抽出「X.XX 元/升」的表述才计数，含糊表述排除；
- **可判定条数**：网页摘要里出现明确价格数字才计入，无价格的算「无法判定」，不进分母；
- **跨城价差**：同标号、同一天、同口径（零售挂牌价）的城市极值差，不是平均值波动。

## 九、怎么证明这些数字是真的

口说无凭。三类证据互相咬合，任何一条都能被独立复查：

**① 数据包**（`oil_pack.json`）：{n_assert} 条断言 + {n_web} 条网页 + {n_city} 城价差 + 垂类 + 边界，带 `_meta.generated_at` 与 `tool_calls`。每个数字在文件里都能 grep 到。

**② 报告页**（`docs/油价真伪卡.html`）：由数据包直接渲染，逐条列出「城市 / 断言值 / 今日价 / 上一轮价 / 判定」，可对照本文表格逐行核对。

![实测报告页：四态分布与逐条明细](shots/03_report.png)

**③ 调用量与成本**：本次采集共 **{calls} 次** SearchPro 调用，耗时 {elapsed} 秒。按元宝搜索标准版 20 元/千次计，本次成本约 **{cost} 元**。调用次数在控制台用量里可对账，`_meta.tool_calls` 与脚本内计数器一致。

![控制台调用量](shots/04_usage.png)

三条咬合方式：**数据包是终态，报告是终态的可视化，用量是过程**——过程、结果、明细三点互证，而不是「我截了个图说跑过了」。

## 十、六个坑

1. **`Cnt` 只接受 10/20/30/40/50。** 传 5 返回 `InvalidParameter`，且是 `Response.Error` 结构、**不抛 HTTP 异常**，不显式检查就静默拿到空结果，额度照扣。
2. **`Pages` 是字符串数组。** 每个元素要二次 `json.loads`，直接 `p["title"]` 报 `string indices must be integers`。我第一次这么写，debug 了二十分钟。
3. **`Mode` 不传 ≠ 默认带 VR 卡。** 不传时返回的自然检索结果里 `vr` 全为 false。我第一次测垂类覆盖就栽在这——以为 9 类全不召回，其实是我没传 `Mode=1`。
4. **`$DATE` 用 UTC。** 北京时间 23:00 之后属于 UTC 的「昨天」，签名日期跟着错，报 `SignatureFailure`，但错误信息不会告诉你是日期问题。
5. **同价区会骗过你的自检。** 南京、杭州实测都是 8.34（同价区），拿「不同城市必不同价」当校验规则，会把正确解析判成异常。阿里和日喀则是 9.62 / 9.24，反过来也证明它不是一个全省统一价。
6. **`历史油价` 不是「昨天的价」。** 它是**上一调价周期**的价，两次调价可能隔十天以上。当「昨天」写进报告，时效口径就错了。

## 十一、局限与代价

- **只覆盖一个垂类。** 油价是离散、行政调价、有唯一官方值的场景，判定干净。股价、汇率是连续变量，同样两条信息「不一致」不等于「谁错」，需要按时间容差判，这套判定器不能直接搬。
- **判定依赖 VR 卡覆盖。** 无卡城市只能判存疑（本次漠河即如此），这是数据源边界，不是方法论缺陷。
- **断言样本是单模型单次作答。** {n_assert} 条只能说明「这类查询上记忆型回答不可信」，不能支撑「某模型一定错」的结论。
- **网页审计样本有限。** {n_city} 城 × 10 条，证明的是「存在系统性过期」，不是「过期率精确等于 {wrong_pct}%」。
- **单机命令行，无并发无服务化。** 这个阶段要的是把判定口径讲清楚，不是把吞吐做上去。

## 十二、想搬到你自己的场景：改三处

1. **换垂类词**：把「92 号汽油」换成你的领域实体，VR 卡自动切垂类；
2. **换断言模板**：把「X.XX 元/升」换成你领域的「实体 + 属性值」；
3. **换比对器**：把「等于今日 / 等于上一轮」换成你领域等价的确定值比较。

再加一条规则：**容差要跟着数据语义走**。两位小数的零售价差一分就是差；连续波动的行情价只能比「时点差是否在容差内」。这条不写，跨垂类搬过去必误判。

## 十三、五条可复用的结论

1. **先分清「过期」和「编造」。** 这是所有验真工具的第一道分水岭，混在一起工具就不可信了。
2. **优先找那些「官方把两轮值摆在一起」的数据源。** 有对照组，判定才是机械的。
3. **口径要单独成节。** 分母是什么、容差多少，写清楚评委会加分。
4. **判错要写进文章。** {n_assert} 条全错，比堆十条全对更有说服力。
5. **时间语义比数值更重要。** 同样的数字属于今天还是上一轮，含义完全不同。

---

## 附：判定常量与口径速查（建议收藏备用）

| 常量 / 口径 | 值 | 说明 |
|---|---|---|
| 数值容差 | 0.005 元/升 | 两位小数零售价，差一分为差 |
| 断言抽取正则 | `\\d{1,2}\\.\\d{1,2}\\s*元/\\s*升` | 只认带「元每升」单位的数字 |
| 判定期望字段 | `今日油价` / `历史油价` | 均来自 `vr_category=oil` 的 VR 卡 |
| 缓存有效期 | 1 天 | 跨调价周期整体作废 |
| 限速 | 0.4~0.5 秒/次 | 避免 `RequestLimitExceeded` |
| 无卡城市 | 判 `unknown` | 不降级、不借邻省价 |

如果这个工具对你有用，欢迎点赞收藏——判定口径和常量都在上面这张表里，方便以后回来查。
"""


def fmt_table(headers, rows):
    if not rows:
        return "_[本次采集该维度无数据]_"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=".")
    ap.add_argument("--title", default=TITLE_DEFAULT)
    ap.add_argument("--repo", default="https://github.com/yourname/oil-price-truthcard")
    args = ap.parse_args()

    work = Path(args.work).resolve()
    pack = json.loads((work / "data" / "oil_pack.json").read_text(encoding="utf-8"))

    pv, wf, cc, vt, meta = pack["price_verify"], pack["web_freshness"], pack["cross_city"], pack["vertical"], pack["_meta"]

    label = {"correct": "✅ 属实（今日价）", "stale": "🕐 已过期（上一轮价）",
             "mismatch": "❌ 与官方不符", "unknown": "⚪ 存疑（无 VR 卡）",
             "undetermined": "— 无明确价格"}

    rows = [[r["city"], f'{r["asserted"]:.2f}', f'{r["official_today"]:.2f}',
             f'{r["official_history"]:.2f}', f'{r["official_today"] - r["asserted"]:+.2f}',
             label.get(r["verdict"], r["verdict"])]
            for r in pv["results"] if r["asserted"] is not None]
    verify_table = fmt_table(["城市", "AI 断言（元/升）", "官方今日价", "官方上一轮价", "低估幅度", "判定"], rows)
    gaps = [r["official_today"] - r["asserted"] for r in pv["results"] if r["asserted"] is not None]
    avg_gap = round(sum(gaps) / len(gaps), 3) if gaps else 0
    s_pv = pv["summary"]
    vkey_note = (f"合计 {pv['n']} 条："
                 + "、".join(f"{label.get(k, k)} {v} 条" for k, v in s_pv.items()) + "。")

    by_city = {}
    for r in wf["rows"]:
        d = by_city.setdefault(r["city"], {"correct": 0, "stale": 0, "mismatch": 0, "undetermined": 0,
                                           "today": r["official_today"], "hist": r["official_history"]})
        d[r["verdict"]] += 1
    wrows = []
    for city, d in by_city.items():
        judged = d["correct"] + d["stale"] + d["mismatch"]
        wrows.append([city, f'{d["today"]:.2f}', f'{d["hist"]:.2f}', d["correct"], d["stale"],
                      d["mismatch"], d["undetermined"],
                      f'{round((d["mismatch"] + d["stale"]) / judged * 100, 1)}%' if judged else "—"])
    web_table = fmt_table(["城市", "今日价", "上一轮价", "报今日", "报上一轮", "两轮都不是", "无价格", "有误率"], wrows)
    s = wf["summary"]
    judged = s.get("correct", 0) + s.get("stale", 0) + s.get("mismatch", 0)
    wrong_pct = round((s.get("mismatch", 0) + s.get("stale", 0)) / judged * 100, 1) if judged else 0
    web_table += (f"\n\n{wf['n']} 条中：报今日价 {s.get('correct',0)}、报上一轮价 {s.get('stale',0)}、"
                  f"两轮都不是 {s.get('mismatch',0)}、无明确价格 {s.get('undetermined',0)}。")

    srows = [[r["city"], f'{r["p92"]:.2f}', f'{r["p95"]:.2f}' if r["p95"] else "—",
              f'{r["p92_hist"]:.2f}' if r["p92_hist"] else "—",
              f'{(r["p92"] - r["p92_hist"]):+.2f}' if r["p92_hist"] else "—"]
             for r in sorted(cc["rows"], key=lambda x: x["p92"])]
    spread_table = fmt_table(["城市", "92 号今日价", "95 号今日价", "92 号上一轮价", "本轮变动"], srows)

    vrows = [[k, v["query"], "✅ 召回" if v["hit"] else "❌ 未召回", v.get("category", "")]
             for k, v in vt["verticals"].items()]
    vertical_table = fmt_table(["垂类", "探测 query", "召回", "vr_category"], vrows)
    vertical_table += (f"\n\n覆盖 {len(vt['covered'])}/{len(vt['verticals'])} 类；"
                       f"对照组（非垂类 query）误命中 {vt['control_hits']}/{vt['control_n']}。")

    calls = meta["tool_calls"]
    cost = round(calls * 20 / 1000, 2)

    body = TPL
    for k, v in {
        "{title}": args.title, "{repo}": args.repo,
        "{n_assert}": str(pv["n"]), "{n_web}": str(wf["n"]), "{n_city}": str(len(cc["rows"])),
        "{n_vert}": str(len(vt["verticals"])), "{n_covered}": str(len(vt["covered"])),
        "{avg_gap}": f"{avg_gap:.2f}", "{gap_box}": f"{avg_gap * 50:.1f}",
        "{judged}": str(judged), "{undet}": str(s.get("undetermined", 0)),
        "{w_correct}": str(s.get("correct", 0)), "{w_stale}": str(s.get("stale", 0)),
        "{w_mismatch}": str(s.get("mismatch", 0)), "{wrong_pct}": f"{wrong_pct}",
        "{spread}": f'{cc["spread"]:.2f}', "{min_p}": f'{cc["min"]:.2f}',
        "{max_p}": f'{cc["max"]:.2f}', "{spread_box}": f'{cc["spread"] * 50:.1f}',
        "{calls}": str(calls), "{elapsed}": str(meta["elapsed_sec"]), "{cost}": f"{cost}",
        "{vkey_note}": vkey_note,
        "{verify_table}": verify_table, "{web_table}": web_table,
        "{spread_table}": spread_table, "{vertical_table}": vertical_table,
    }.items():
        body = body.replace(k, v)

    out = work / "article.md"
    out.write_text(body, encoding="utf-8")
    cn = sum(1 for ch in body if "\u4e00" <= ch <= "\u9fa5")
    print(f"文章 → {out}")
    print(f"汉字 {cn} | 断言 {pv['n']} | 网页 {wf['n']} | 跨城 {len(cc['rows'])} | 垂类 {len(vt['covered'])}/{len(vt['verticals'])} | 调用 {calls}")
    if cn < 1500:
        print("⚠ 汉字不足 1500")


if __name__ == "__main__":
    main()
