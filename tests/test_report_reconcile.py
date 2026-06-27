from datetime import date

from ai_radar_agent.dates import window_for_date
from ai_radar_agent.report_reconcile import (
    drop_stale_final_top_from_candidate_metadata,
    drop_stale_final_top_from_evidence,
    reconcile_report_with_final_brief,
)


def test_reconcile_report_syncs_candidate_table_and_empty_region():
    report = """
## 候选事件筛选表

### 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| Kimi估值飙升至300亿美元 | 国内 | 候选 | 多家媒体摘要报道 |
| 微信Agent入口获资本市场重估 | 国内 | 候选 | 券商解读 |

### 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| Anthropic 发布 Claude Fable 5 并公开定价 | 海外 | 候选 | 官方发布 |
| Datadog老兵创立AI编程新星Niteshift | 海外 | 候选 | 种子轮融资 |

## AI 前沿能力与应用雷达 - 国内版【2026年06月10日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Kimi估值飙升至300亿美元 | L3 | P1 | 中 | 利好 |

### 二、逐条深度解读

1. **Kimi估值飙升至300亿美元**

## AI 前沿能力与应用雷达 - 海外版【2026年06月10日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Anthropic 发布 Claude Fable 5 并公开定价 | L1 | P1 | 高 | 利好 |
| Datadog老兵创立AI编程新星Niteshift | L3 | P2 | 中 | 观察 |

### 二、逐条深度解读

1. **Anthropic 发布 Claude Fable 5 并公开定价**

2. **Datadog老兵创立AI编程新星Niteshift**
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "Anthropic 发布 Claude Fable 5 并公开定价",
                "priority": "P1",
                "why": "官方定价会影响海外模型商业化预期。",
                "sources": [{"source": "Anthropic", "url": "https://example.com/anthropic"}],
            }
        ],
    }
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| Kimi估值飙升至300亿美元 | 国内 | 否 | 未进入最终 Top：属于媒体总结/分析观点或第三方数据，缺少当日直接官方进展。 |" in reconciled
    assert "| 微信Agent入口获资本市场重估 | 国内 | 否 | 未进入最终 Top：属于媒体总结/分析观点或第三方数据，缺少当日直接官方进展。 |" in reconciled
    assert "| Anthropic 发布 Claude Fable 5 并公开定价 | 海外 | 是 | 官方发布 |" in reconciled
    assert "| Datadog老兵创立AI编程新星Niteshift | 海外 | 否 | 未进入最终 Top：相对当日最终 Top 的新增性、确定性或影响强度不足。 |" in reconciled
    assert "1. **Kimi估值飙升至300亿美元**" not in reconciled
    assert "| 今日国内无强核心事件 | - | - | - | 不强行凑数 |" in reconciled
    assert reconciled.count("Datadog老兵创立AI编程新星Niteshift") == 1
    assert "海外正式雷达共保留 1 条最终 Top" in reconciled
    assert "[Anthropic](https://example.com/anthropic)" in reconciled


def test_reconcile_removes_future_candidate_rows_for_target_day():
    report = """
## 国内候选事件筛选表

| 事件 | 地区 | event_date | report_date | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|
| Kimi K2.7 Code高速版上线 | 国内 | 2026-06-15 | 2026-06-15 | 候选 | 官方发布 |

## 海外候选事件筛选表

| 事件 | 地区 | event_date | report_date | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|
| OpenAI合作伙伴网络 | 海外 | 2026-06-15 | 2026-06-15 | 候选 | 官方发布 |
| Barret Zoph离开OpenAI | 海外 | 2026-06-19 | 2026-06-19 | 候选 | 媒体报道 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Kimi K2.7 Code高速版上线 | L1 | P2 | 高 | 速度分层 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 今日海外无强核心事件 | - | - | - | 不强行凑数 |
""".strip()
    brief = {
        "domestic_top": [{"title": "Kimi K2.7 Code高速版上线", "priority": "P2"}],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "Kimi K2.7 Code高速版上线" in reconciled
    assert "OpenAI合作伙伴网络" in reconciled
    assert "Barret Zoph离开OpenAI" not in reconciled
    assert "2026-06-19" not in reconciled


def test_reconcile_drops_pre_candidate_formal_and_normalizes_loose_region_sections():
    report = """
# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Kimi高速版 | - | P1 | - | 被压缩的影响… |

## 国内候选事件筛选表

| 事件 | 地区 | event_date | report_date | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|
| Kimi高速版 | 国内 | 2026-06-15 | 2026-06-15 | 候选 | 官方发布 |

## 海外候选事件筛选表

| 事件 | 地区 | event_date | report_date | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|
| OpenAI合作伙伴网络 | 海外 | 2026-06-15 | 2026-06-15 | 候选 | 官方发布 |

# 一、今日总览 - 国内版 2026年06月15日

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Kimi高速版 | L1 | P1 | 高 | 编程模型速度分层 |

# 二、逐条深度解读 - 国内版

**1. Kimi高速版**
- **影响/So what**：
  1. 速度分层改善开发者体验。
- **来源**：[IT之家](https://example.com/kimi)

# 三、观察信号 - 国内版

- 飞书多维表格 AI 登顶 TableBench。

# 五、输出前自我检查清单 - 国内版

- [x] 区域自检。

# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 今日海外无强核心事件 | - | - | - | 不强行凑数 |
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "Kimi高速版",
                "priority": "P1",
                "why": "Kimi高速版改善开发者体验。",
                "sources": [{"source": "IT之家", "url": "https://example.com/kimi"}],
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert reconciled.index("## 国内候选事件筛选表") < reconciled.index("# AI 前沿能力与应用雷达 - 国内版")
    assert reconciled.count("# AI 前沿能力与应用雷达 - 国内版") == 1
    assert "今日总览 - 国内版" not in reconciled
    assert "输出前自我检查清单 - 国内版" not in reconciled
    assert "速度分层改善开发者体验" in reconciled
    assert "被压缩的影响…" not in reconciled
    assert "## 输出前自我检查清单" in reconciled


def test_reconcile_inserts_missing_empty_domestic_formal_section_before_overseas():
    report = """
## 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 国内观察事件 | 国内 | 候选 | 观察信号 |

## 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 美国FERC新规为AI数据中心并网开绿灯 | 海外 | 候选 | 官方规则 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月19日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 美国FERC新规为AI数据中心并网开绿灯 | L3 | P1 | 高 | 基础设施 |
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "美国FERC新规为AI数据中心并网开绿灯",
                "priority": "P1",
                "confidence": "高",
                "why": "并网规则直接影响AI数据中心用电扩张。",
                "sources": [{"source": "FERC", "url": "https://example.com/ferc"}],
            }
        ],
    }
    window = window_for_date(date(2026, 6, 19), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "# AI 前沿能力与应用雷达 - 国内版【2026年06月19日】" in reconciled
    assert reconciled.index("# AI 前沿能力与应用雷达 - 国内版") < reconciled.index("# AI 前沿能力与应用雷达 - 海外版")
    assert "| 今日国内无强核心事件 | - | - | - | 不强行凑数 |" in reconciled
    assert "## 输出前自我检查清单" in reconciled


def test_reconcile_inserts_missing_overseas_formal_section_from_final_top():
    report = """
## 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 国内核心事件 | 国内 | 候选 | 官方发布 |

## 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 海外核心事件 | 海外 | 候选 | 官方博客 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月19日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 国内核心事件 | L3 | P2 | 高 | 应用 |
""".strip()
    brief = {
        "domestic_top": [{"title": "国内核心事件", "priority": "P2"}],
        "overseas_top": [
            {
                "title": "海外核心事件",
                "priority": "P1",
                "why": "进入最终 Top。",
                "sources": [{"source": "Official", "url": "https://example.com/official"}],
            }
        ],
    }
    window = window_for_date(date(2026, 6, 19), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "# AI 前沿能力与应用雷达 - 海外版【2026年06月19日】" in reconciled
    assert "| 海外核心事件 | - | P1 | - | 进入最终 Top。 |" in reconciled
    assert "[Official](https://example.com/official)" in reconciled


def test_reconcile_fallback_formal_section_preserves_full_why():
    report = """
## 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 国内核心事件 | 国内 | 候选 | 官方发布 |
""".strip()
    full_why = (
        "该事件不是普通产品更新，而是把模型服务从单一能力定价推向速度、吞吐和成本结构分层。"
        "开发者在选择编程模型时，过去主要比较准确率和上下文长度，现在会更直接比较同一任务下的响应速度、"
        "单位Token成本以及并发体验。对模型厂商来说，这意味着推理基础设施、缓存策略和服务级别协议会成为"
        "产品竞争的一部分，而不是隐藏在后台的工程指标。这也是回归测试尾句，必须完整保留。"
    )
    brief = {
        "domestic_top": [
            {
                "title": "国内核心事件",
                "priority": "P2",
                "why": full_why,
                "sources": [{"source": "Official", "url": "https://example.com/official"}],
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 19), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "这也是回归测试尾句，必须完整保留。" in reconciled
    assert f"为什么重要：{full_why}" in reconciled


def test_reconcile_preserves_existing_deep_dive_content_when_filtering_final_top():
    report = """
## 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 金山办公将于下月推出组织级 AI 办公产品“企业大脑”WPS Comate | 国内 | 候选 | S2 来源 |
| 微信正在灰度测试 AI助手“小微” | 国内 | 候选 | S4 来源 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月20日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 金山办公将于下月推出组织级 AI 办公产品“企业大脑”WPS Comate | L3 | P2 | 高 | 组织级办公 Agent |
| 微信正在灰度测试 AI助手“小微” | L4 | P2 | 中 | 超级应用入口 |

### 二、逐条深度解读

1. **金山办公将于下月推出组织级 AI 办公产品“企业大脑”WPS Comate**

   金山办公这次不是给个人用户增加一个简单的文档助手，而是把 AI 能力推到组织知识、流程协同和跨应用调用层。它的关键意义在于，办公 AI 的竞争重心开始从“单点提效”转向“企业内部工作流入口”：谁能理解组织上下文、沉淀业务知识、连接审批和文档生产，谁就更接近企业级 Agent 的付费理由。这类产品如果能在权限、知识库和流程编排上跑通，会比单纯的写作助手更接近可持续商业化。

   - 来源：[IT之家](https://example.com/wps)

2. **微信正在灰度测试 AI助手“小微”**

   微信入口足够大，但当前证据仍来自聚合媒体和客服口径，缺少官方产品说明、灰度规模和能力边界。因此它更适合作为观察信号，而不是当天正式核心判断。
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "金山办公将推“企业大脑”",
                "card_title": "金山办公将推企业大脑WPS Comate",
                "why": "办公AI从个人提效走向组织级Agent，验证企业AI工作流产品化路径",
                "priority": "P2",
                "sources": [{"source": "IT之家", "url": "https://example.com/wps"}],
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 20), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "办公 AI 的竞争重心开始从“单点提效”转向“企业内部工作流入口”" in reconciled
    assert "如果能在权限、知识库和流程编排上跑通" in reconciled
    assert "微信入口足够大" not in reconciled
    assert "为什么重要：办公AI从个人提效走向组织级Agent" not in reconciled
    assert "| 金山办公将于下月推出组织级 AI 办公产品“企业大脑”WPS Comate | L3 | P2 | 高 | 组织级办公 Agent |" in reconciled
    assert "| 微信正在灰度测试 AI助手“小微” | L4 | P2 | 中 | 超级应用入口 |" not in reconciled
    assert "国内正式雷达共保留 1 条最终 Top" in reconciled


def test_reconcile_fills_empty_so_what_in_preserved_deep_dive():
    report = """
## 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| Kimi代码模型推高速版 | 国内 | 候选 | S2 来源 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Kimi代码模型推高速版 | L1 | P2 | 高 | 编程 Agent |

### 二、逐条深度解读

1. 标题：Kimi代码模型推高速版
   - **概述**：月之暗面上线 Kimi K2.7 Code 高速版。
   - **影响 / So what**:
   - 来源：[IT之家](https://example.com/kimi)
""".strip()
    why = "月之暗面通过高速版把模型竞争从单纯能力分数推向推理效率、开发者体验和分层定价。"
    brief = {
        "domestic_top": [
            {
                "title": "Kimi代码模型推高速版",
                "why": why,
                "priority": "P2",
                "sources": [{"source": "IT之家", "url": "https://example.com/kimi"}],
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert f"- **影响 / So what**：{why}" in reconciled
    assert "- **影响 / So what**:\n" not in reconciled


def test_reconcile_appends_source_when_block_only_mentions_source_text():
    report = """
# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Kimi代码模型推高速版 | L1 | P2 | 高 | 编程 Agent |

### 二、逐条深度解读

1. 标题：Kimi代码模型推高速版
   - **概述**：月之暗面上线 Kimi K2.7 Code 高速版。
   - **可信度**：信息来源于 IT之家。
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "Kimi代码模型推高速版",
                "why": "高速版提升编程模型响应速度。",
                "priority": "P2",
                "sources": [{"source": "IT之家", "url": "https://example.com/kimi"}],
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "信息来源于 IT之家" in reconciled
    assert "来源：[IT之家](https://example.com/kimi)" in reconciled


def test_reconcile_regenerates_core_judgment_from_final_top():
    report = """
# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Anthropic工程团队画像曝光 | L1 | P2 | 中 | 组织能力 |
| OpenAI合作伙伴网络 | L3 | P2 | 高 | 企业生态 |

### 二、逐条深度解读

1. **Anthropic工程团队画像曝光**

   Anthropic团队结构更偏基础设施工程。

   - 来源：[36氪](https://example.com/anthropic)

### 三、观察信号

- OpenAI合作伙伴网络可继续作为观察信号。

### 四、今日核心判断

- OpenAI 正式打响企业服务生态战。
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "Anthropic工程团队画像曝光",
                "why": "工程化能力成为 Anthropic 后续模型迭代和产品交付的关键变量。",
                "priority": "P2",
                "sources": [{"source": "36氪", "url": "https://example.com/anthropic"}],
            }
        ],
    }
    window = window_for_date(date(2026, 6, 15), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)
    overseas_section = reconciled.split("# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】", 1)[1]

    assert "OpenAI合作伙伴网络可继续作为观察信号" in overseas_section
    assert "OpenAI 正式打响企业服务生态战" not in overseas_section
    assert "工程化能力成为 Anthropic 后续模型迭代和产品交付的关键变量" in overseas_section


def test_reconcile_empty_top_preserves_existing_observation_and_judgment_tail():
    report = """
# AI 前沿能力与应用雷达 - 海外版【2026年06月20日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Claude Code数据显示非程序员编程成功率惊人 | L3 | P2 | 中 | 采用度观察 |

### 二、逐条深度解读

1. **Claude Code数据显示非程序员编程成功率惊人**

   第三方样本显示非程序员也能完成部分编程任务，但来源层级不足，不能作为正式核心事件。

### 三、观察信号

- Claude Code 的非程序员成功率值得继续跟踪，尤其是样本口径、任务复杂度与付费转化。
- 企业 AI Token 成本控制开始成为采用度扩张后的运营约束。

### 四、今日核心判断

- 海外 AI 应用进入采用度验证期，但今天缺少足够强的一手来源支撑正式 Top。
""".strip()
    brief = {"domestic_top": [], "overseas_top": []}
    window = window_for_date(date(2026, 6, 20), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 今日海外无强核心事件 | - | - | - | 不强行凑数 |" in reconciled
    assert "Claude Code 的非程序员成功率值得继续跟踪" in reconciled
    assert "企业 AI Token 成本控制开始成为采用度扩张后的运营约束" in reconciled
    assert "海外 AI 应用进入采用度验证期" not in reconciled
    assert "海外未形成可发布的最终 Top" in reconciled
    assert "第三方样本显示非程序员也能完成部分编程任务" not in reconciled


def test_reconcile_strips_llm_preamble_before_first_heading():
    report = """
我会在严格锁定时间范围、遵循所有原则和规则的前提下，完成这份雷达日报。

首先检查证据列表页面跳转情况，优先使用已提供URL的完整文本作为筛选依据。

## 国内候选事件筛选表
国内核心事件：不强行凑数。

## 海外候选事件筛选表
海外核心事件：不强行凑数。

## 国内版正式雷达
无。

## 海外版正式雷达
无。
""".strip()
    brief = {"domestic_top": [], "overseas_top": []}
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert reconciled.startswith("## 国内候选事件筛选表")
    assert "我会在严格锁定时间范围" not in reconciled
    assert "首先检查证据列表" not in reconciled


def test_reconcile_strips_strict_preamble_and_candidate_table_prose():
    report = """
以下严格按指令，仅基于给定证据列表生成 2026 年 6 月 21 日日报。先输出候选事件筛选表，再分别输出国内版和海外版正式雷达。

---

## 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 微信小微灰度上线 | 国内 | 候选 | S4 来源，不应入选 |

用户提供的证据中，国内部分缺乏来自S1/S2的强一手数据事件。微信小微战略意义重大，破格入选。

## 海外候选事件筛选表

海外核心事件：不强行凑数。

## 国内版正式雷达
无。

## 海外版正式雷达
无。
""".strip()
    brief = {"domestic_top": [], "overseas_top": []}
    window = window_for_date(date(2026, 6, 21), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert reconciled.startswith("## 国内候选事件筛选表")
    assert "以下严格按指令" not in reconciled
    assert "用户提供的证据中" not in reconciled
    assert "破格入选" not in reconciled
    assert (
        "| 微信小微灰度上线 | 国内 | 否 | 未进入最终 Top：来源层级或 source_fit 不足，可继续作为观察信号跟踪。 |"
        in reconciled
    )


def test_reconcile_drops_non_daily_core_judgment_section_from_observations():
    report = """
## 国内候选事件筛选表
国内核心事件：不强行凑数。

## 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 苹果iOS 27系统级AI路径显现 | 海外 | 候选 | 强来源 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月21日】
无。

# AI 前沿能力与应用雷达 - 海外版【2026年06月21日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 苹果iOS 27系统级AI路径显现 | L4 | P1 | 高 | 利好 |

### 二、逐条深度解读

1. **苹果iOS 27系统级AI路径显现**
   - **影响 / So what**：苹果将 AI 嵌入系统底层。
   - **来源**：[TechCrunch](https://example.com/apple)

### 三、观察信号

（无）

#### **四、本周核心判断**

- **AI商业模式的结构性矛盾已浮出水面**：这不是当日 final Top。
- **人才暗战揭示未来权力版图**：这不是当日 final Top。

### 四、今日核心判断

- 苹果iOS 27系统级AI路径显现：AI 从单点功能升级为操作系统底座。
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "苹果iOS 27系统级AI路径显现",
                "why": "苹果将 AI 能力深度嵌入系统底层，AI 从单点功能升级为操作系统底座。",
                "priority": "P1",
                "sources": [{"source": "TechCrunch", "url": "https://example.com/apple"}],
            }
        ],
    }
    window = window_for_date(date(2026, 6, 21), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "本周核心判断" not in reconciled
    assert "AI商业模式的结构性矛盾" not in reconciled
    assert "人才暗战揭示未来权力版图" not in reconciled
    assert "### 三、观察信号" in reconciled
    assert "（无）" in reconciled
    assert "- **苹果iOS 27系统级AI路径显现**：苹果将 AI 能力深度嵌入系统底层" in reconciled


def test_reconcile_strips_llm_transition_before_formal_report():
    report = """
## 国内候选事件筛选表
国内核心事件：不强行凑数。

现在，我将基于筛选出的核心事件，生成正式日报。

---

## 国内版正式雷达
无。

## 海外候选事件筛选表
海外核心事件：不强行凑数。

## 海外版正式雷达
无。
""".strip()
    brief = {"domestic_top": [], "overseas_top": []}
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "现在，我将基于筛选出的核心事件" not in reconciled
    assert "## 国内候选事件筛选表" in reconciled
    assert "# AI 前沿能力与应用雷达 - 国内版【2026年06月10日】" in reconciled


def test_reconcile_preserves_candidate_table_after_formal_sections():
    report = """
# AI 前沿能力与应用雷达 - 国内版【2026年06月10日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 国内弱来源事件 | L3 | P2 | 中 | 观察 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月10日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 海外正式事件 | L1 | P1 | 高 | 利好 |
| 海外未保留事件 | L3 | P2 | 中 | 观察 |

## 候选事件筛选表

### 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 国内弱来源事件 | 国内 | 候选 | S4 来源 |

### 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 海外正式事件 | 海外 | 候选 | 官方发布 |
| 海外未保留事件 | 海外 | 候选 | 后置 gate 删除 |

## 来源附录

- [S1](https://example.com/source)
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [{"title": "海外正式事件", "priority": "P1"}],
    }
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "## 国内候选事件筛选表" in reconciled
    assert "## 海外候选事件筛选表" in reconciled
    assert "| 国内弱来源事件 | 国内 | 否 | 未进入最终 Top：来源层级或 source_fit 不足，可继续作为观察信号跟踪。 |" in reconciled
    assert "| 海外正式事件 | 海外 | 是 | 官方发布 |" in reconciled
    assert "| 海外未保留事件 | 海外 | 否 | 未进入最终 Top：后置 gate/brief 未保留，可继续作为观察信号跟踪。 |" in reconciled
    assert "## 来源附录" in reconciled


def test_reconcile_uses_row_context_to_avoid_synthetic_final_top_rows():
    report = """
## 国内候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 私域AI客服3Chat.ai | domestic | S2 | IT之家 | high | application/adoption | 2026-06-26 | 2026-06-26 | 2026-06-26 | 否 | L3 | 终端应用工具 | P2 | 高 | media summary | 否 | 未进入最终 Top：属于媒体总结/分析观点或第三方数据，缺少当日直接官方进展。 |

## 海外候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GPT-5.6 Sol预览 | overseas | S1 | OpenAI官方 | high | model/capability | 2026-06-26 | 2026-06-26 | 2026-06-26 | 否 | L1 | 原生基座模型 | P1 | 高 | official actual | 否 | 未进入最终 Top：相对当日最终 Top 的新增性、确定性或影响强度不足。 |
| OpenAI内部Agent采用 | overseas | S2 | 36氪 | high | agent/workflow, adoption | 2026-06-26 | 2026-06-26 | 2026-06-26 | 否 | L4 | 全局智能体 | P1 | 高 | official actual (引用OpenAI博客) | 否 | 未进入最终 Top：相对当日最终 Top 的新增性、确定性或影响强度不足。 |
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "企微群聊AI客服实现上下文理解",
                "priority": "P2",
                "sources": [
                    {
                        "title": "私域 AI 客服怎么选?企微群聊 AI 客服正在成为社群运营的新标配",
                        "source": "IT之家",
                        "url": "https://example.com/private-service",
                        "evidence_id": "E18",
                    }
                ],
            }
        ],
        "overseas_top": [
            {
                "title": "OpenAI预览GPT-5.6 Sol",
                "priority": "P1",
                "sources": [
                    {
                        "title": "Previewing GPT-5.6 Sol: a next-generation model",
                        "source": "OpenAI News",
                        "url": "https://example.com/gpt-5-6",
                        "evidence_id": "E1",
                    }
                ],
            },
            {
                "title": "Codex接管OpenAI 99.8% Token输出",
                "priority": "P1",
                "sources": [
                    {
                        "title": "造ChatGPT的人,已经不用ChatGPT干活了",
                        "source": "36氪",
                        "url": "https://example.com/codex-agent",
                        "evidence_id": "E54",
                    }
                ],
            },
        ],
    }
    window = window_for_date(date(2026, 6, 26), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 私域AI客服3Chat.ai | domestic | S2 | IT之家 | high | application/adoption | 2026-06-26 | 2026-06-26 | 2026-06-26 | 否 | L3 | 终端应用工具 | P2 | 高 | media summary | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert "| GPT-5.6 Sol预览 | overseas | S1 | OpenAI官方 | high | model/capability | 2026-06-26 | 2026-06-26 | 2026-06-26 | 否 | L1 | 原生基座模型 | P1 | 高 | official actual | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert "| OpenAI内部Agent采用 | overseas | S2 | 36氪 | high | agent/workflow, adoption | 2026-06-26 | 2026-06-26 | 2026-06-26 | 否 | L4 | 全局智能体 | P1 | 高 | official actual (引用OpenAI博客) | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert "| 企微群聊AI客服实现上下文理解 | 国内 | - | final_top |" not in reconciled
    assert "| OpenAI预览GPT-5.6 Sol | 海外 | - | final_top |" not in reconciled
    assert "| Codex接管OpenAI 99.8% Token输出 | 海外 | - | final_top |" not in reconciled


def test_reconcile_replaces_yes_no_placeholder_reasons():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 入选事件 | 国内 | 候选 | 是 |
| 未入选事件 | 国内 | 候选 | 否 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月10日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 入选事件 | L3 | P2 | 高 | 利好 |
""".strip()
    brief = {
        "domestic_top": [{"title": "入选事件", "priority": "P2"}],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 入选事件 | 国内 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert "| 未入选事件 | 国内 | 否 | 未进入最终 Top：相对当日最终 Top 的新增性、确定性或影响强度不足。 |" in reconciled


def test_reconcile_rewrites_exclusion_reasons_by_candidate_metadata():
    report = """
### 海外候选事件筛选表

| 事件 | 地区 | 是否前延回看 | 初步优先级 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|
| OpenAI降价传闻 | 海外 | 否 | P1 | media-reported estimate | 候选 | 可能重塑价格体系 |
| 前日模型发布后续 | 海外 | 是（昨日发布） | P2 | official actual | 候选 | 模型速度提升 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月11日】
""".strip()
    brief = {"domestic_top": [], "overseas_top": []}
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| OpenAI降价传闻 | 海外 | 否 | P1 | media-reported estimate | 否 | 未进入最终 Top：仍属传闻或待确认信息，缺少足够官方证据。 |" in reconciled
    assert "| 前日模型发布后续 | 海外 | 是（昨日发布） | P2 | official actual | 否 | 未进入最终 Top：属于前延/后续报道，新增性不足。 |" in reconciled


def test_reconcile_does_not_treat_observation_signal_as_top_decision_reason():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 今日核心判断 | 信号类型 | 初步优先级 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|
| 核心但未发布事件 | 国内 | 今日核心 | 观察信号 | P3 | 候选 | 观察信号，持续跟踪 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月11日】
""".strip()
    brief = {"domestic_top": [], "overseas_top": []}
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "初步优先级为 P3/观察信号，未达当日核心事件阈值" not in reconciled
    assert "核心但未发布事件" not in reconciled
    assert " P3 " not in reconciled
    assert "候选事件可能包含核心判断或观察信号" in reconciled


def test_reconcile_matches_compressed_final_top_titles_without_common_prefix_false_positive():
    report = """
## 候选事件筛选表

### 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| NVIDIA机密计算助力Apple私有云 | 海外 | 候选 | 官方博客 |
| Decart发布世界模型Oasis3 | 海外 | 候选 | 权威媒体 |
| OpenAI计划收购Ona，为Codex扩展企业级云环境 | 海外 | 候选 | 官方博客 |
| OpenAI正考虑大幅降低Token价格 | 海外 | 候选 | 同品牌但不是同一事件 |
| Claude Fable 5不回答基础生物问题 | 海外 | 候选 | 同模型但不是同一事件 |
| 海外未保留事件 | 海外 | 候选 | 后置 gate 删除 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月10日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| NVIDIA机密计算助力Apple私有云 | L0 | P2 | 高 | 利好 |
| Decart发布世界模型Oasis3 | L1 | P2 | 中 | 利好 |
| 海外未保留事件 | L3 | P2 | 中 | 观察 |
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "NVIDIA机密计算落地Apple AI推理",
                "card_title": "NVIDIA机密计算助力Apple AI推理",
                "priority": "P2",
            },
            {
                "title": "Decart发布实时驾驶世界模型",
                "card_title": "Decart发布实时驾驶世界模型Oasis 3",
                "priority": "P2",
            },
            {"title": "OpenAI收购Ona扩展Codex Agent", "priority": "P1"},
            {"title": "Microsoft限制内部使用Claude Fable 5", "priority": "P2"},
        ],
    }
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| NVIDIA机密计算助力Apple私有云 | 海外 | 是 | 官方博客 |" in reconciled
    assert "| Decart发布世界模型Oasis3 | 海外 | 是 | 权威媒体 |" in reconciled
    assert "| OpenAI计划收购Ona，为Codex扩展企业级云环境 | 海外 | 是 | 官方博客 |" in reconciled
    assert "| OpenAI正考虑大幅降低Token价格 | 海外 | 否 | 未进入最终 Top：与最终 Top 不是同一事件，可继续作为观察信号跟踪。 |" in reconciled
    assert "| Claude Fable 5不回答基础生物问题 | 海外 | 否 | 未进入最终 Top：与最终 Top 不是同一事件，可继续作为观察信号跟踪。 |" in reconciled
    assert "| 海外未保留事件 | 海外 | 否 | 未进入最终 Top：后置 gate/brief 未保留，可继续作为观察信号跟踪。 |" in reconciled
    assert "| Microsoft限制内部使用Claude Fable 5 | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled


def test_reconcile_updates_real_title_variants_without_duplicate_final_top_rows():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 36氪发文探讨中国大模型商业化关键赛道“编程和办公” | 国内 | 候选 | 行业分析 |

### 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| OpenAI与BBVA合作，ChatGPT Enterprise扩展到10万员工 | 海外 | 候选 | 企业采用 |
| DoorDash推出AI聊天机器人Ask DoorDash | 海外 | 候选 | 产品发布 |
| Claude Fable 5不回答基础生物问题 | 海外 | 候选 | 同模型但不是同一事件 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月11日】

# AI 前沿能力与应用雷达 - 海外版【2026年06月11日】
""".strip()
    brief = {
        "domestic_top": [{"title": "36氪发文警示AI战略方向", "priority": "P2"}],
        "overseas_top": [
            {"title": "BBVA大规模部署ChatGPT Enterprise", "priority": "P1"},
            {"title": "DoorDash推出AI点餐助手", "priority": "P2"},
            {"title": "Microsoft限制内部使用Claude Fable 5", "priority": "P2"},
        ],
    }
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 36氪发文探讨中国大模型商业化关键赛道“编程和办公” | 国内 | 是 | 行业分析 |" in reconciled
    assert "| 36氪发文警示AI战略方向 | 国内 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" not in reconciled
    assert "| OpenAI与BBVA合作，ChatGPT Enterprise扩展到10万员工 | 海外 | 是 | 企业采用 |" in reconciled
    assert "| BBVA大规模部署ChatGPT Enterprise | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" not in reconciled
    assert "| DoorDash推出AI聊天机器人Ask DoorDash | 海外 | 是 | 产品发布 |" in reconciled
    assert "| DoorDash推出AI点餐助手 | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" not in reconciled
    assert "| Claude Fable 5不回答基础生物问题 | 海外 | 否 | 未进入最终 Top：与最终 Top 不是同一事件，可继续作为观察信号跟踪。 |" in reconciled
    assert "| Microsoft限制内部使用Claude Fable 5 | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled


def test_reconcile_matches_final_top_to_candidate_rows_by_evidence_source():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 是否前延回看 | 初步优先级 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|
| 豆包大模型 2.1 Pro 发布，跨越生产级质变点（E49） | domestic | 否 | P1 | 候选 | 官方披露 |
| AI进入产业现场 飞书与大湾区企业共探数智化转型（E35） | domestic | 否 | P2 | 候选 | 企业采用 |
| 豆包 2.1 Pro 发布 | 国内 | - | - | 是 | 进入最终 Top；由后置 gate/brief 回写。 |
| 飞书大湾区峰会 | 国内 | - | - | 是 | 进入最终 Top；由后置 gate/brief 回写。 |

### 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 造ChatGPT的人,已经不用ChatGPT干活了（E54） | overseas | 否 | 未进入最终 Top：相对当日最终 Top 的新增性、确定性或影响强度不足。 |
| Codex 取代 ChatGPT | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月26日】

# AI 前沿能力与应用雷达 - 海外版【2026年06月26日】
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "豆包 2.1 Pro 发布",
                "sources": [{"title": "豆包大模型 2.1 Pro 发布,跨越生产级质…", "evidence_id": "E49"}],
                "priority": "P1",
            },
            {
                "title": "飞书大湾区峰会",
                "sources": [{"title": "AI进入产业现场 飞书与大湾区企业共探数智化转…", "evidence_id": "E35"}],
                "priority": "P2",
            },
        ],
        "overseas_top": [
            {
                "title": "Codex 取代 ChatGPT",
                "sources": [{"title": "造ChatGPT的人,已经不用ChatGPT干…", "evidence_id": "E54"}],
                "priority": "P1",
            },
        ],
    }
    window = window_for_date(date(2026, 6, 26), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 豆包大模型 2.1 Pro 发布，跨越生产级质变点（E49） | domestic | 否 | P1 | 是 | 官方披露 |" in reconciled
    assert "| AI进入产业现场 飞书与大湾区企业共探数智化转型（E35） | domestic | 否 | P2 | 是 | 企业采用 |" in reconciled
    assert "| 造ChatGPT的人,已经不用ChatGPT干活了（E54） | overseas | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert "| 豆包 2.1 Pro 发布 | 国内 | - | - | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" not in reconciled
    assert "| 飞书大湾区峰会 | 国内 | - | - | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" not in reconciled
    assert "| Codex 取代 ChatGPT | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" not in reconciled


def test_reconcile_matches_private_service_title_variant_without_synthetic_row():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 私域AI客服成为社群运营新标配 | 国内 | S2 | IT之家 | 高 | 应用场景/商业化 | 2026-06-26 | 2026-06-26 | N/A | 否 | L3 | 应用 | P2 | 中 | media summary | 否 | 未进入最终 Top：属于媒体总结/分析观点或第三方数据，缺少当日直接官方进展。 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月26日】
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "企微私域AI客服场景崛起",
                "card_title": "企微群聊AI客服成私域运营新标配",
                "sources": [{"title": "私域 AI 客服怎么选?企微群聊 AI 客服正…", "evidence_id": "E18"}],
                "priority": "P2",
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 26), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 私域AI客服成为社群运营新标配 | 国内 | S2 | IT之家 | 高 | 应用场景/商业化 | 2026-06-26 | 2026-06-26 | N/A | 否 | L3 | 应用 | P2 | 中 | media summary | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert "| 企微私域AI客服场景崛起 | 国内 | - | final_top |" not in reconciled


def test_reconcile_matches_feishu_roi_title_variant_without_synthetic_row():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 飞书大湾区峰会：AI进入产业现场，披露德赛西威ROI数据 | 国内 | S2 | 中国经济网 | 高 | 应用落地/商业化 | 2026-06-25 | 2026-06-26 | 2026-06-26 | 是 | L3 | 终端应用 | P2 | 高 | media summary | 否 | 未进入最终 Top：属于前延/后续报道，新增性不足。 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月26日】
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "飞书AI智能体进入制造业产研流程，年省5800万",
                "sources": [{"title": "AI进入产业现场 飞书与大湾区企业共探数智化转型", "evidence_id": "E35"}],
                "priority": "P2",
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 26), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 飞书大湾区峰会：AI进入产业现场，披露德赛西威ROI数据 | 国内 | S2 | 中国经济网 | 高 | 应用落地/商业化 | 2026-06-25 | 2026-06-26 | 2026-06-26 | 是 | L3 | 终端应用 | P2 | 高 | media summary | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert "| 飞书AI智能体进入制造业产研流程，年省5800万 | 国内 | - | final_top |" not in reconciled


def test_reconcile_drops_stale_cross_language_final_top_variant_from_brief():
    report = """
### 海外候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| The White House is asking OpenAI to slow roll GPT-5.6 | 海外 | S2 | TechCrunch | 高 | 治理/发布策略 | 2026-06-25 | 2026-06-26 | N/A | 是 | L1 | 治理影响 | P2 | 高 | media-reported estimate | 否 | 未进入最终 Top：仍属传闻或待确认信息，缺少足够官方证据。 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月26日】
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "白宫要求OpenAI缓释新模型",
                "card_title": "白宫要求OpenAI推迟GPT-5.6发布",
                "sources": [{"title": "OpenAI will delay GPT-5.", "evidence_id": "E10"}],
                "priority": "P2",
            }
        ],
        "brief_final_domestic_items_count": 0,
        "brief_final_overseas_items_count": 1,
        "brief_items_count": 1,
    }
    window = window_for_date(date(2026, 6, 26), "Asia/Shanghai")

    filtered_brief = drop_stale_final_top_from_candidate_metadata(report, brief, window)
    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert filtered_brief["overseas_top"] == []
    assert filtered_brief["brief_final_overseas_items_count"] == 0
    assert filtered_brief["brief_items_count"] == 0
    assert "| 白宫要求OpenAI缓释新模型 | 海外 | - | final_top |" not in reconciled
    assert "| 今日海外无强核心事件 | - | - | - | 不强行凑数 |" in reconciled


def test_reconcile_drops_stale_final_top_without_same_day_signal():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | event_date | report_date | 是否前延回看 | 初步优先级 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|
| 豆包大模型 2.1 Pro 发布，跨越生产级质变点（E49） | domestic | S2 | authoritative_media | 2026-06-23 | 2026-06-26 | 是 | P1 | 是 | 字节官方大会发布新一代旗舰模型及关键调用量数据，代表国内最强基座模型能力迭代和规模化采用信号。 |
| 豆包 2.1 Pro 发布 | 国内 | - | final_top | - | - | - | P1 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月26日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 豆包 2.1 Pro 发布 | L1 | P1 | 高 | 利好 |

### 二、逐条深度解读

1. 豆包 2.1 Pro 发布
   - 来源：E49
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "豆包 2.1 Pro 发布",
                "sources": [{"title": "豆包大模型 2.1 Pro 发布,跨越生产级质…", "evidence_id": "E49"}],
                "priority": "P1",
            }
        ],
        "overseas_top": [],
        "brief_final_domestic_items_count": 1,
        "brief_final_overseas_items_count": 0,
        "brief_items_count": 1,
    }
    window = window_for_date(date(2026, 6, 26), "Asia/Shanghai")

    filtered_brief = drop_stale_final_top_from_candidate_metadata(report, brief, window)
    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert filtered_brief["domestic_top"] == []
    assert filtered_brief["brief_final_domestic_items_count"] == 0
    assert filtered_brief["brief_items_count"] == 0
    assert "| 豆包大模型 2.1 Pro 发布，跨越生产级质变点（E49） | domestic | S2 | authoritative_media | 2026-06-23 | 2026-06-26 | 是 | P1 | 否 | 未进入最终 Top：属于前延/后续报道，新增性不足。 |" in reconciled
    assert "| 豆包 2.1 Pro 发布 | 国内 | - | final_top | - | - | - | P1 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" not in reconciled
    assert "| 今日国内无强核心事件 | - | - | - | 不强行凑数 |" in reconciled
    assert "豆包 2.1 Pro 发布 | L1 | P1" not in reconciled


def test_drop_stale_final_top_from_evidence_drops_old_release_without_new_signal():
    brief = {
        "domestic_top": [
            {
                "title": "豆包2.1 Pro发布，日均Tokens调用突破180万亿",
                "sources": [{"title": "豆包大模型 2.1 Pro 发布,跨越生产级质变点", "evidence_id": "E1"}],
                "priority": "P1",
            },
            {
                "title": "飞书广州峰会披露AI落地ROI，年省5832万",
                "sources": [{"title": "飞书广州峰会落地", "evidence_id": "E2"}],
                "priority": "P2",
            },
        ],
        "overseas_top": [],
        "brief_final_domestic_items_count": 2,
        "brief_items_count": 2,
    }
    evidence = [
        {
            "title": "豆包大模型 2.1 Pro 发布,跨越生产级质变点,AI 生产力进入规模化新阶段",
            "url": "https://example.com/doubao",
            "content": "6\u200f月\u200f\n23\u200f日，火山引擎 FORCE 大会集中发布豆包大模型 2.1 Pro，日均 Tokens 调用突破 180 万亿。",
        },
        {
            "title": "飞书广州峰会落地,聚焦制造业AI协作升级",
            "url": "https://example.com/feishu",
            "content": "6月25日，飞书广州峰会举行。6月26日新披露德赛西威产研智能体年节省5832万元。",
        },
    ]
    window = window_for_date(date(2026, 6, 26), "Asia/Shanghai")

    filtered = drop_stale_final_top_from_evidence(brief, evidence, window)

    assert [item["title"] for item in filtered["domestic_top"]] == ["飞书广州峰会披露AI落地ROI，年省5832万"]
    assert filtered["brief_final_domestic_items_count"] == 1
    assert filtered["brief_items_count"] == 1


def test_reconcile_inserts_candidate_sections_when_llm_omits_them():
    report = """
# AI 前沿能力与应用雷达 - 国内版【2026年06月11日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 今日国内无强核心事件 | - | - | - | 不强行凑数 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月11日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| OpenAI收购Ona | L4 | P1 | 高 | Agent云环境 |
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [{"title": "OpenAI收购Ona：为Codex添加持久云环境", "priority": "P1"}],
    }
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "## 国内候选事件筛选表" in reconciled
    assert "## 海外候选事件筛选表" in reconciled
    assert "| OpenAI收购Ona：为Codex添加持久云环境 | 海外 | - | final_top | - | final_top | - | - | - | - | - | - | P1 | - | - | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert reconciled.index("## 国内候选事件筛选表") < reconciled.index("# AI 前沿能力与应用雷达 - 国内版")


def test_reconcile_canonicalizes_candidate_headings_and_removes_combined_prelude():
    report = """
## 候选事件筛选表：国内版

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| 京东发布智能体自主支付协议 | 国内 | 候选 | S4来源 |

## 候选事件筛选表：海外版

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| OpenAI 计划收购 Ona，扩展Codex持久化云环境 | 海外 | 候选 | 官方博客 |
| DoorDash推出AI聊天机器人 | 海外 | 候选 | 未最终保留 |

---

## 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 京东发布智能体自主支付协议 | L4 | P1 | 中 | 不应残留 |
| DoorDash推出AI聊天机器人 | L3 | P2 | 中 | 不应残留 |

## 二、逐条深度解读

### 【国内版】

原始国内内容

### 【海外版】

原始海外内容
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [{"title": "OpenAI计划收购Ona，扩展Codex持久化云环境", "priority": "P1"}],
    }
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "## 国内候选事件筛选表" in reconciled
    assert "## 海外候选事件筛选表" in reconciled
    assert "## 候选事件筛选表：国内版" not in reconciled
    assert "## 一、今日总览\n\n| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |\n|---|---|---|---|---|\n| 京东发布智能体自主支付协议" not in reconciled
    assert "DoorDash推出AI聊天机器人 | L3" not in reconciled
    assert "| OpenAI 计划收购 Ona，扩展Codex持久化云环境 | 海外 | 是 | 官方博客 |" in reconciled
    assert "| DoorDash推出AI聊天机器人 | 海外 | 否 | 未进入最终 Top：后置 gate/brief 未保留，可继续作为观察信号跟踪。 |" in reconciled


def test_reconcile_appends_missing_final_top_to_wide_candidate_table():
    report = """
### 海外版候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| NVIDIA机密计算助力Apple私有云 | 海外 | S1 | 官方源 | 高 | 新事件 | 2026-06-10 | 2026-06-10 | 2026-06-10 | 否 | L0 | 基础设施 | P2 | 高 | official actual | 候选 | 官方博客 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月10日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| NVIDIA机密计算助力Apple私有云 | L0 | P2 | 高 | 利好 |
| OpenAI发布PRC网络行动报告 | L4 | P2 | 高 | 治理 |
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {"title": "NVIDIA助力Apple云侧推理隐私计算", "priority": "P2"},
            {"title": "OpenAI发布PRC网络行动报告", "priority": "P2"},
        ],
    }
    window = window_for_date(date(2026, 6, 10), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| NVIDIA机密计算助力Apple私有云 | 海外 | S1 | 官方源 | 高 | 新事件 | 2026-06-10 | 2026-06-10 | 2026-06-10 | 否 | L0 | 基础设施 | P2 | 高 | official actual | 是 | 官方博客 |" in reconciled
    assert "| OpenAI发布PRC网络行动报告 | 海外 | - | final_top | - | final_top | - | - | - | - | - | - | P2 | - | - | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled


def test_reconcile_does_not_append_final_top_when_title_variant_row_exists():
    report = """
### 国内候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 阿里千问输入法上线 macOS 版 | 国内 | S2 | authoritative_media | high | model/capability | 2026-06-27 | 2026-06-27 | N/A | 否 | L3 | AI应用/新交互入口 | P2 | 高 | 不适用 | 候选 | P2里程碑，体现AI在系统级输入法入口的新应用范式 |

# AI 前沿能力与应用雷达 - 国内版【2026年06月27日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| 千问输入法macOS版上线 | L3 | P2 | 高 | 系统级入口 |
""".strip()
    brief = {
        "domestic_top": [
            {
                "title": "千问输入法macOS版上线",
                "card_title": "千问输入法macOS版上线",
                "priority": "P2",
                "source_ids": ["E10"],
                "sources": [{"evidence_id": "E10", "title": "阿里千问输入法上线 macOS 版，最快 30 秒理解用户语气"}],
            }
        ],
        "overseas_top": [],
    }
    window = window_for_date(date(2026, 6, 27), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 阿里千问输入法上线 macOS 版 | 国内 | S2 | authoritative_media | high | model/capability | 2026-06-27 | 2026-06-27 | N/A | 否 | L3 | AI应用/新交互入口 | P2 | 高 | 不适用 | 是 | P2里程碑，体现AI在系统级输入法入口的新应用范式 |" in reconciled
    assert "| 千问输入法macOS版上线 | 国内 | - | final_top |" not in reconciled


def test_reconcile_does_not_append_final_top_for_mixed_language_anchor_variant():
    report = """
### 海外候选事件筛选表

| 事件 | 地区 | 来源层级 | 来源类型 | source_fit | 信号类型 | event_date | report_date | signal_date | 是否前延回看 | 层级 | 类别 | 初步优先级 | 可信度 | 数据口径 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 美国政府授权100+实体使用Anthropic Mythos 5 | 海外 | S2 | authoritative_media | 高 | 商业化/治理 | 2026-06-27 | 2026-06-27 | - | 否 | L1 | 基座模型 | P1 | 高 | official actual | 候选 | 媒体报道 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月27日】

### 一、今日总览

| 标题 | 层级 | 优先级 | 可信度 | 影响方向 |
|---|---|---|---|---|
| Mythos 5获政府授权有限恢复，AI成战略资源 | L1 | P1 | 高 | 模型治理 |
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {
                "title": "Mythos 5获政府授权有限恢复，AI成战略资源",
                "card_title": "Mythos 5获政府授权有限恢复",
                "priority": "P1",
                "sources": [
                    {"evidence_id": "E1", "title": "Trump Admin releases Anthropic Mythos to be used by more than 100 US companies"}
                ],
            }
        ],
    }
    window = window_for_date(date(2026, 6, 27), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| 美国政府授权100+实体使用Anthropic Mythos 5 | 海外 | S2 | authoritative_media | 高 | 商业化/治理 | 2026-06-27 | 2026-06-27 | - | 否 | L1 | 基座模型 | P1 | 高 | official actual | 是 | 媒体报道 |" in reconciled
    assert "| Mythos 5获政府授权有限恢复，AI成战略资源 | 海外 | - | final_top |" not in reconciled


def test_reconcile_appends_missing_rows_before_table_break():
    report = """
### 海外候选事件筛选表

| 事件 | 地区 | 是否入选 | 入选/剔除原因 |
|---|---|---|---|
| Anthropic为Claude Fable 5隐形护栏道歉 | 海外 | 候选 | 官方回应 |

# AI 前沿能力与应用雷达 - 海外版【2026年06月11日】
""".strip()
    brief = {
        "domestic_top": [],
        "overseas_top": [
            {"title": "Anthropic为Claude Fable 5隐藏护栏道歉", "priority": "P2"},
            {"title": "DoorDash推出AI点餐机器人", "priority": "P2"},
        ],
    }
    window = window_for_date(date(2026, 6, 11), "Asia/Shanghai")

    reconciled = reconcile_report_with_final_brief(report, brief, window)

    assert "| DoorDash推出AI点餐机器人 | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |" in reconciled
    assert (
        reconciled.index("| DoorDash推出AI点餐机器人 | 海外 | 是 | 进入最终 Top；由后置 gate/brief 回写。 |")
        < reconciled.index("# AI 前沿能力与应用雷达 - 海外版")
    )
