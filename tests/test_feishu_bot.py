import base64
import hashlib
import hmac

import httpx

from ai_radar_agent.config import Settings
from ai_radar_agent.feishu_bot import build_card_payload, build_text_payload, maybe_send_bot_card, sign, smart_title_for_card


def _brief():
    return {
        "date": "2026-06-01",
        "title": "AI Radar｜2026-06-01",
        "domestic_top": [{"title": "国内事件", "why": "重要", "priority": "P1"}],
        "overseas_top": [{"title": "海外事件", "why": "重要", "priority": "P2"}],
        "core_judgments": ["判断一"],
        "watch_signals": [],
        "doc_url": "https://example.feishu.cn/docx/a",
        "canonical_type": "docx",
        "evidence_count": 5,
    }


def _brief_with_sources():
    brief = _brief()
    brief["domestic_top"] = [
        {
            "title": "国内事件",
            "why": "重要",
            "priority": "P1",
            "sources": [
                {"title": "官方", "url": "https://example.com/a", "source": "OpenAI"},
                {"title": "媒体", "url": "https://example.com/b", "source": "TechCrunch"},
                {"title": "第三条", "url": "https://example.com/c", "source": "第三方"},
            ],
        }
    ]
    brief["overseas_top"] = [
        {
            "title": "海外事件",
            "why": "重要",
            "priority": "P2",
            "sources": [{"title": "The Verge", "url": "https://example.com/v", "source": ""}],
        }
    ]
    return brief


def _item(title, priority, why="重要", sources=None):
    return {"title": title, "why": why, "priority": priority, "sources": sources or []}


def test_bot_skips_when_webhook_missing():
    result = maybe_send_bot_card(Settings(), _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["skipped"] is True
    assert result["reason"] == "missing_webhook"


def test_bot_skips_for_flags():
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook")

    assert maybe_send_bot_card(settings, _brief(), dry_run=True, skip_llm=False, send_bot=True)["reason"] == "dry_run"
    assert maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=True, send_bot=True)["reason"] == "skip_llm"
    assert (
        maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=False)["reason"]
        == "send_bot=false"
    )


def test_bot_signature_matches_feishu_rule():
    timestamp = "123456"
    secret = "secret"
    expected = base64.b64encode(hmac.new(f"{timestamp}\n{secret}".encode("utf-8"), b"", hashlib.sha256).digest()).decode()

    assert sign(timestamp, secret) == expected


def test_bot_payload_uses_brief_doc_url():
    payload = build_card_payload(_brief())
    payload_text = str(payload)

    assert payload["msg_type"] == "interactive"
    assert payload["card"]["header"]["title"]["content"] == "AI Radar｜2026-06-01"
    assert payload["card"]["elements"][-1]["actions"][0]["url"] == "https://example.feishu.cn/docx/a"
    assert "Evidence" not in payload_text
    assert "evidence_count" not in payload_text
    assert "RSS count" not in payload_text
    assert "Tavily count" not in payload_text


def test_bot_card_title_uses_ai_radar_title_not_first_item():
    brief = _brief()
    brief["title"] = "AI Radar｜2026-06-01"
    brief["domestic_top"][0]["title"] = "豆包计划月内推出付费订阅"

    payload = build_card_payload(brief)

    assert payload["card"]["header"]["title"]["content"] == "AI Radar｜2026-06-01"


def test_bot_card_title_appends_stable_ref_suffix(monkeypatch):
    monkeypatch.setenv("GITHUB_REF_NAME", "stable/v0.2.0")

    payload = build_card_payload(_brief())

    assert payload["card"]["header"]["title"]["content"] == "AI Radar｜2026-06-01｜v0.2.0"


def test_bot_card_title_falls_back_when_brief_title_is_news_title():
    brief = _brief()
    brief["title"] = "豆包计划月内推出付费订阅"

    payload = build_card_payload(brief)

    assert payload["card"]["header"]["title"]["content"] == "AI Radar｜2026-06-01"


def test_bot_card_payload_includes_source_links():
    payload = build_card_payload(_brief_with_sources())
    payload_text = str(payload)

    assert "[OpenAI](https://example.com/a)" in payload_text
    assert "[TechCrunch](https://example.com/b)" in payload_text
    assert "https://example.com/c" not in payload_text
    assert "[The Verge](https://example.com/v)" in payload_text
    assert "evidence_count" not in payload_text
    assert "RSS count" not in payload_text
    assert "Tavily count" not in payload_text


def test_smart_title_does_not_cut_english_tokens():
    travelers = smart_title_for_card("Travelers全美部署OpenAI AI理赔助手", max_chars=18)
    nvidia = smart_title_for_card("NVIDIA将Agentic AI能力带到边缘设备", max_chars=18)

    assert not travelers.endswith("OpenA…")
    assert "OpenA｜" not in travelers
    assert "Agentic AI能" not in nvidia
    assert nvidia.endswith("…")


def test_bot_card_prefers_item_card_title():
    brief = _brief()
    brief["domestic_top"] = [
        {
            "title": "Travelers全美部署OpenAI AI理赔助手并扩展到全美业务线",
            "card_title": "Travelers部署OpenAI理赔助手",
            "why": "重要",
            "priority": "P1",
            "sources": [],
        }
    ]

    text = str(build_card_payload(brief))

    assert "Travelers部署OpenAI理赔助手" in text
    assert "Travelers全美部署OpenAI AI理赔助手并扩展" not in text


def test_bot_card_keeps_item_title_complete_without_ellipsis():
    brief = _brief()
    title = "Meta上线按Token收费的WhatsApp Business AI客服"
    brief["overseas_top"] = [_item(title, "P1")]

    text = str(build_card_payload(brief))

    assert title in text
    assert "Meta上线按Token收费的WhatsApp…" not in text


def test_bot_card_uses_card_title_and_card_why_without_truncating_full_fields():
    brief = _brief()
    brief["domestic_top"] = [
        {
            "title": "Meta上线按Token收费的WhatsApp Business AI客服完整标题",
            "card_title": "WhatsApp AI客服收费",
            "why": "这是一段完整解释，长度可以更长，用于 brief 或完整上下文，不应直接进入飞书卡片详情。",
            "card_why": "按Token收费验证AI客服商业化。",
            "priority": "P1",
            "sources": [],
        }
    ]

    text = str(build_card_payload(brief))

    assert "WhatsApp AI客服收费" in text
    assert "按Token收费验证AI客服商业化。" in text
    assert "完整标题" not in text
    assert "不应直接进入飞书卡片详情" not in text


def test_bot_card_why_falls_back_when_card_why_is_attribution_fragment():
    brief = _brief()
    brief["domestic_top"] = [
        {
            "title": "80%元宝用户使用混元大模型",
            "card_title": "80%元宝用户使用混元大模型",
            "why": "汤道生透露80%元宝用户使用混元大模型。",
            "card_why": "汤道生透露",
            "priority": "P2",
            "sources": [],
        }
    ]

    text = str(build_card_payload(brief))

    assert "汤道生透露80%元宝用户使用混元大模型。" in text


def test_bot_card_uses_core_and_watch_card_fields():
    brief = _brief()
    brief["core_judgments"] = ["完整核心判断很长，给 brief 使用。"]
    brief["core_judgments_card"] = ["核心判断卡片短句。"]
    brief["watch_signals"] = ["完整观察信号很长，给 brief 使用。"]
    brief["watch_signals_card"] = ["观察信号卡片短句。"]

    text = str(build_card_payload(brief))

    assert "核心判断卡片短句。" in text
    assert "观察信号卡片短句。" in text
    assert "完整核心判断很长" not in text
    assert "完整观察信号很长" not in text


def test_bot_card_why_uses_fallback_instead_of_truncating_overlong_text():
    brief = _brief()
    brief["domestic_top"] = [
        _item(
            "长why测试",
            "P1",
            why="这条新闻说明AI应用正在进入更复杂的商业化验证阶段，企业客户会先测试工作流效率、成本下降和用户留存情况，然后决定是否扩大采购，同时平台方还会继续观察付费转化、渠道成本和模型调用成本变化。",
        )
    ]

    text = str(build_card_payload(brief))

    assert "同时平台方还…" not in text
    assert "LLM返回超字数，请查看完整日报" in text


def test_bot_card_judgments_truncate_at_sentence_boundary():
    brief = _brief()
    brief["core_judgments"] = [
        "AI应用的用户入口争夺进入关键窗口，微信与支付宝两条线索同时强化。后续应持续观察C端AI付费转化和模型调用成本。",
    ]

    text = str(build_card_payload(brief))

    assert "后续应…" not in text
    assert "微信与支付宝两条线索同时强化。" in text


def test_bot_card_renders_all_items_and_sorts_by_priority():
    brief = _brief()
    brief["domestic_top"] = [
        _item("国内P2先", "P2"),
        _item("国内P1一", "P1"),
        _item("国内观察", "观察"),
        _item("国内P1二", "P1 战略转折点"),
        _item("国内未知", "其他"),
    ]
    brief["overseas_top"] = [
        _item("海外P2一", "P2"),
        _item("海外P1一", "P1"),
        _item("海外观察一", "OBSERVE"),
        _item("海外P2二", "P2 重要里程碑"),
        _item("海外P1二", "P1"),
        _item("海外观察二", "观察"),
    ]

    text = str(build_card_payload(brief))

    for title in ("国内P2先", "国内P1一", "国内观察", "国内P1二", "国内未知"):
        assert title in text
    for title in ("海外P2一", "海外P1一", "海外观察一", "海外P2二", "海外P1二", "海外观察二"):
        assert title in text
    assert text.index("国内P1一") < text.index("国内P1二") < text.index("国内P2先") < text.index("国内观察")
    assert text.index("海外P1一") < text.index("海外P1二") < text.index("海外P2一") < text.index("海外P2二") < text.index("海外观察一")
    assert "今日无强核心事件" not in text


def test_bot_card_caps_overseas_top_to_six_and_records_meta():
    brief = _brief()
    brief["overseas_top"] = [_item(f"海外{i}", "P1" if i in {2, 5} else "P2") for i in range(1, 13)]

    text = str(build_card_payload(brief))
    result = maybe_send_bot_card(Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook"), brief, dry_run=True, skip_llm=False, send_bot=True)

    for idx in range(1, 7):
        assert f"海外{idx}" in text
    for idx in range(7, 13):
        assert f"海外{idx}" not in text
    assert "更多详情见完整日报。" in text
    assert result["overseas_items_input_count"] == 12
    assert result["overseas_items_rendered_count"] == 6
    assert result["overseas_items_truncated"] is True
    assert result["card_items_truncated"] is True
    assert result["card_truncated_reason"] == "max_6_per_region"


def test_bot_card_payload_omits_source_label_when_sources_empty():
    payload = build_card_payload(_brief())

    assert "来源：" not in str(payload)


def test_bot_card_empty_domestic_section_never_shows_source_or_tavily():
    brief = _brief()
    brief["domestic_top"] = []
    brief["overseas_top"] = []
    brief["core_judgments"] = []
    brief["watch_signals"] = []

    text = str(build_card_payload(brief))

    assert "今日无强核心事件，不强行凑数。" in text
    assert "来源：" not in text
    assert "tavily" not in text.lower()


def test_bot_card_drops_fake_empty_item_with_sources():
    brief = _brief()
    brief["domestic_top"] = [
        {
            "title": "今日无强核心事件",
            "why": "不强行凑数",
            "priority": "观察",
            "sources": [{"title": "Tavily", "url": "https://techcrunch.com/a", "source": "tavily.tavily"}],
        }
    ]
    brief["overseas_top"] = []

    text = str(build_card_payload(brief))
    result = maybe_send_bot_card(Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook"), brief, dry_run=True, skip_llm=False, send_bot=True)

    assert "今日无强核心事件，不强行凑数。" in text
    assert "来源：" not in text
    assert "tavily" not in text.lower()
    assert result["domestic_items_input_count"] == 0
    assert result["domestic_items_rendered_count"] == 0


def test_bot_card_drops_region_no_core_placeholder_items():
    brief = _brief()
    brief["domestic_top"] = [
        {
            "title": "今日国内候选池无任何进入核心的事件。",
            "card_title": "当日无符合标准的国内核心事件",
            "why": "当日RSS召回及搜索未返回任何国内AI事件，无法构成有效候选池。",
            "priority": "观察",
        }
    ]
    brief["overseas_top"] = [
        {
            "title": "今日海外无核心事件",
            "card_title": "今日无海外核心事件",
            "why": "当日未发现海外强核心事件。",
            "priority": "观察",
        }
    ]

    text = str(build_card_payload(brief))
    result = maybe_send_bot_card(Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook"), brief, dry_run=True, skip_llm=False, send_bot=True)

    assert "今日国内候选池无任何进入核心的事件" not in text
    assert "当日无符合标准的国内核心事件" not in text
    assert "今日海外无核心事件" not in text
    assert "今日无海外核心事件" not in text
    assert "今日无强核心事件，不强行凑数。" in text
    assert result["domestic_items_input_count"] == 0
    assert result["overseas_items_input_count"] == 0


def test_bot_card_drops_dash_placeholder_item():
    brief = _brief()
    brief["domestic_top"] = [{"title": "—", "card_title": "—", "why": "详见完整日报。", "priority": "观察", "sources": []}]
    brief["overseas_top"] = []

    text = str(build_card_payload(brief))
    result = maybe_send_bot_card(Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook"), brief, dry_run=True, skip_llm=False, send_bot=True)

    assert "—｜观察" not in text
    assert "**—**" not in text
    assert "今日无强核心事件，不强行凑数。" in text
    assert result["domestic_items_input_count"] == 0
    assert result["domestic_items_rendered_count"] == 0


def test_bot_card_empty_overseas_section_never_shows_source_or_tavily():
    brief = _brief()
    brief["overseas_top"] = []

    text = str(build_card_payload(brief))

    assert "今日无强核心事件，不强行凑数。" in text
    assert "tavily" not in text.lower()


def test_bot_card_source_links_still_limited_to_two_per_item():
    brief = _brief()
    brief["domestic_top"] = [
        _item(
            "三来源事件",
            "P1",
            sources=[
                {"title": "官方", "url": "https://example.com/a", "source": "OpenAI"},
                {"title": "媒体", "url": "https://example.com/b", "source": "TechCrunch"},
                {"title": "第三条", "url": "https://example.com/c", "source": "第三方"},
            ],
        )
    ]

    text = str(build_card_payload(brief))

    assert "[OpenAI](https://example.com/a)" in text
    assert "[TechCrunch](https://example.com/b)" in text
    assert "https://example.com/c" not in text


def test_bot_card_cleans_source_labels_and_drops_tavily_without_url():
    brief = _brief()
    brief["domestic_top"] = [
        _item(
            "来源清洗",
            "P1",
            sources=[
                {"title": "TC article", "url": "https://techcrunch.com/ai", "source": "tavily.tavily", "provider": "tavily"},
                {"title": "Tavily only", "url": "", "source": "tavily", "provider": "tavily"},
                {"title": "重复", "url": "https://example.com/a", "source": "techcrunch.techcrunch"},
            ],
        )
    ]

    text = str(build_card_payload(brief))

    assert "[TechCrunch](https://techcrunch.com/ai)" in text
    assert "https://example.com/a" not in text
    assert "tavily.tavily" not in text.lower()
    assert "[tavily]" not in text.lower()


def test_bot_card_uses_domain_when_provider_is_tavily_without_source_label():
    brief = _brief()
    brief["domestic_top"] = [
        _item(
            "域名来源",
            "P1",
            sources=[{"title": "Some article title", "url": "https://techcrunch.com/ai", "provider": "tavily"}],
        )
    ]

    text = str(build_card_payload(brief))

    assert "[TechCrunch](https://techcrunch.com/ai)" in text
    assert "Some article title" not in text
    assert "tavily" not in text.lower()


def test_bot_card_maps_cn_finance_source_domains():
    brief = _brief()
    brief["domestic_top"] = [
        _item(
            "财经来源",
            "P1",
            sources=[
                {"title": "新闻", "url": "https://finance.sina.com.cn/tech/a", "source": "finance.sina.com.cn"},
                {"title": "新闻", "url": "https://wap.eastmoney.com/a/123", "source": "wap.eastmoney.com"},
            ],
        )
    ]

    text = str(build_card_payload(brief))

    assert "[新浪财经](https://finance.sina.com.cn/tech/a)" in text
    assert "[东方财富](https://wap.eastmoney.com/a/123)" in text
    assert "[finance.sina.com.cn]" not in text
    assert "[wap.eastmoney.com]" not in text


def test_bot_card_dedupes_source_labels_and_normalized_urls():
    brief = _brief()
    brief["domestic_top"] = [
        _item(
            "重复来源",
            "P1",
            sources=[
                {"title": "OpenAI News", "url": "https://openai.com/news/a?utm_source=x", "source": "OpenAI News"},
                {"title": "OpenAI News", "url": "https://openai.com/news/a", "source": "OpenAI News"},
                {"title": "OpenAI News", "url": "https://openai.com/news/b", "source": "OpenAI News"},
                {"title": "Reuters", "url": "https://reuters.com/technology/a", "source": "reuters.com"},
            ],
        )
    ]

    text = str(build_card_payload(brief))
    source_line = text.split("来源：", 1)[1].split("\\n", 1)[0]

    assert source_line.count("OpenAI News") == 1
    assert "[Reuters](https://reuters.com/technology/a)" in source_line


def test_bot_card_keeps_real_item_when_sources_empty():
    brief = _brief()
    brief["domestic_top"] = [{"title": "豆包订阅", "why": "商业化加速", "priority": "P1", "sources": []}]

    payload = build_card_payload(brief)
    text = str(payload)

    assert "豆包订阅" in text
    assert "商业化加速" in text
    assert "来源：" not in text
    assert "国内 Top**\\n今日无强核心事件" not in text


def test_bot_card_empty_section_shows_no_core_message():
    brief = _brief()
    brief["domestic_top"] = []

    payload = build_card_payload(brief)
    text = str(payload)

    assert "国内 Top" in text
    assert "今日无强核心事件，不强行凑数。" in text


def test_bot_card_shows_watch_signals_when_no_core_events():
    brief = _brief()
    brief["domestic_top"] = []
    brief["overseas_top"] = []
    brief["watch_signals"] = ["飞书Agent工作流分析：可能改变企业应用竞争。", "Trump AI预审查行政令：可能演化为强约束。"]

    payload = build_card_payload(brief)
    text = str(payload)

    assert "今日无强核心事件，不强行凑数。" in text
    assert "观察信号" in text
    assert "飞书Agent工作流分析" in text
    assert "Trump AI预审查行政令" in text
    assert "P1" not in text


def test_bot_card_keeps_watch_signals_separate_when_one_side_has_events():
    brief = _brief()
    brief["domestic_top"] = []
    brief["overseas_top"] = [_item("海外正式事件", "P1")]
    brief["watch_signals"] = ["一个观察信号"]

    text = str(build_card_payload(brief))

    assert "今日无强核心事件，不强行凑数。" in text
    assert "海外正式事件" in text
    assert "观察信号" in text
    assert "一个观察信号" in text


def test_bot_card_fallback_brief_uses_soft_message():
    brief = _brief()
    brief["brief_generation_status"] = "fallback"
    brief["domestic_top"] = []
    brief["overseas_top"] = []
    brief["core_judgments"] = ["今日简报摘要未能稳定生成，请查看完整日报。"]

    payload = build_card_payload(brief)
    text = str(payload)

    assert "今日简报摘要未能稳定生成，请查看完整日报。" in text
    assert "查看完整日报" in text
    assert "brief 生成失败" not in text
    assert "简报摘要生成异常" not in text


def test_bot_payload_can_link_md_when_doc_url_is_md():
    brief = _brief()
    brief["doc_url"] = "https://example.feishu.cn/file/md"
    brief["canonical_type"] = "md"

    payload = build_card_payload(brief)

    assert payload["card"]["elements"][-1]["actions"][0]["url"] == "https://example.feishu.cn/file/md"


def test_bot_payload_omits_button_when_doc_url_missing():
    brief = _brief()
    brief["doc_url"] = ""

    payload = build_card_payload(brief)

    assert "查看完整日报" not in str(payload)


def test_text_payload_is_short_and_links_doc():
    payload = build_text_payload(_brief())

    assert payload["msg_type"] == "text"
    assert "查看完整日报：https://example.feishu.cn/docx/a" in payload["content"]["text"]
    assert len(payload["content"]["text"]) <= 3500


def test_text_payload_includes_source_links():
    payload = build_text_payload(_brief_with_sources())
    text = payload["content"]["text"]

    assert "来源：[OpenAI](https://example.com/a) · [TechCrunch](https://example.com/b)" in text
    assert "https://example.com/c" not in text


def test_text_payload_renders_all_items_sorted():
    brief = _brief()
    brief["domestic_top"] = [
        _item("国内P2先", "P2"),
        _item("国内P1一", "P1"),
        _item("国内观察", "观察"),
        _item("国内P1二", "P1"),
        _item("国内P2二", "P2"),
    ]
    brief["overseas_top"] = [_item(f"海外{i}", "P1" if i in {2, 5} else "P2") for i in range(1, 7)]

    text = build_text_payload(brief)["content"]["text"]

    for title in ("国内P2先", "国内P1一", "国内观察", "国内P1二", "国内P2二"):
        assert title in text
    for idx in range(1, 7):
        assert f"海外{idx}" in text
    assert text.index("国内P1一") < text.index("国内P1二") < text.index("国内P2先") < text.index("国内P2二") < text.index("国内观察")


def test_text_payload_caps_each_region_to_six():
    brief = _brief()
    brief["overseas_top"] = [_item(f"海外{i}", "P2") for i in range(1, 13)]

    text = build_text_payload(brief)["content"]["text"]

    for idx in range(1, 7):
        assert f"海外{idx}" in text
    for idx in range(7, 13):
        assert f"海外{idx}" not in text
    assert "更多详情见完整日报。" in text


def test_text_payload_shows_watch_signals():
    brief = _brief()
    brief["domestic_top"] = []
    brief["overseas_top"] = []
    brief["watch_signals"] = ["观察一", "观察二"]

    text = build_text_payload(brief)["content"]["text"]

    assert "观察信号" in text
    assert "观察一" in text
    assert "观察二" in text


def test_text_payload_fallback_brief_uses_soft_message():
    brief = _brief()
    brief["brief_generation_status"] = "fallback"

    payload = build_text_payload(brief)
    text = payload["content"]["text"]

    assert "今日简报摘要未能稳定生成，请查看完整日报。" in text
    assert "查看完整日报：https://example.feishu.cn/docx/a" in text
    assert "brief 生成失败" not in text
    assert "简报摘要生成异常" not in text


class FakeClient:
    responses = []
    posts = []

    def __init__(self, timeout):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json):
        self.posts.append({"url": url, "json": json})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _install_fake_client(monkeypatch, *responses):
    FakeClient.responses = list(responses)
    FakeClient.posts = []
    monkeypatch.setattr("ai_radar_agent.feishu_bot.httpx.Client", FakeClient)
    return FakeClient


def test_bot_webhook_http_status_only_warns(monkeypatch):
    _install_fake_client(monkeypatch, httpx.Response(500, text="server token=secret"))
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook")

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["sent"] is False
    assert result["skipped"] is False
    assert result["reason"] == "webhook_http_status"
    assert result["status_code"] == 500
    assert "server" in result["response_body_summary"]
    assert "secret" not in result["response_body_summary"]


def test_bot_webhook_http_error_only_warns(monkeypatch):
    _install_fake_client(monkeypatch, httpx.ConnectError("connect failed"))
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook")

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["sent"] is False
    assert result["reason"] == "webhook_http_error"
    assert "ConnectError" in result["error_summary"]


def test_bot_webhook_code_error_records_details(monkeypatch):
    _install_fake_client(monkeypatch, httpx.Response(200, json={"code": 999, "msg": "unknown webhook failure"}))
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook", FEISHU_BOT_FALLBACK_TEXT=False)

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["sent"] is False
    assert result["reason"] == "webhook_error"
    assert result["status_code"] == 200
    assert result["response_code"] == 999
    assert result["response_msg"] == "unknown webhook failure"


def test_bot_signature_error_is_classified(monkeypatch):
    _install_fake_client(monkeypatch, httpx.Response(200, json={"code": 19024, "msg": "invalid signature"}))
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook", FEISHU_BOT_FALLBACK_TEXT=False)

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["reason"] == "signature_error"


def test_bot_keyword_mismatch_is_classified(monkeypatch):
    _install_fake_client(monkeypatch, httpx.Response(200, json={"code": 9499, "msg": "keywords not matched"}))
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook", FEISHU_BOT_FALLBACK_TEXT=False)

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["reason"] == "keyword_mismatch"


def test_bot_payload_invalid_is_classified(monkeypatch):
    _install_fake_client(monkeypatch, httpx.Response(200, json={"code": 10001, "msg": "invalid card payload"}))
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook", FEISHU_BOT_FALLBACK_TEXT=False)

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["reason"] == "payload_invalid"


def test_bot_card_failure_text_fallback_success(monkeypatch):
    fake = _install_fake_client(
        monkeypatch,
        httpx.Response(200, json={"code": 10001, "msg": "invalid card payload"}),
        httpx.Response(200, json={"code": 0, "msg": "ok"}),
    )
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook")

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["sent"] is True
    assert result["reason"] == "card_failed_text_fallback_sent"
    assert result["text_fallback_attempted"] is True
    assert result["text_fallback_sent"] is True
    assert fake.posts[0]["json"]["msg_type"] == "interactive"
    assert fake.posts[1]["json"]["msg_type"] == "text"


def test_bot_card_and_text_failure(monkeypatch):
    _install_fake_client(
        monkeypatch,
        httpx.Response(200, json={"code": 10001, "msg": "invalid card payload"}),
        httpx.Response(200, json={"code": 10001, "msg": "invalid text payload"}),
    )
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook")

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["sent"] is False
    assert result["reason"] == "card_and_text_failed"
    assert result["text_fallback_attempted"] is True
    assert result["text_fallback_reason"] == "payload_invalid"


def test_bot_invalid_json_response(monkeypatch):
    _install_fake_client(monkeypatch, httpx.Response(200, text="not-json token=secret"))
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook")

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["reason"] == "invalid_json_response"
    assert "not-json" in result["response_body_summary"]
    assert "secret" not in result["response_body_summary"]


def test_bot_signed_payload_contains_timestamp_and_sign(monkeypatch):
    fake = _install_fake_client(monkeypatch, httpx.Response(200, json={"code": 0, "msg": "ok"}))
    monkeypatch.setattr("ai_radar_agent.feishu_bot.time.time", lambda: 123456)
    settings = Settings(FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook", FEISHU_BOT_SECRET="secret")

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    assert result["sent"] is True
    payload = fake.posts[0]["json"]
    assert payload["timestamp"] == "123456"
    assert payload["sign"] == sign("123456", "secret")


def test_bot_response_summary_redacts_secrets(monkeypatch):
    body = {
        "code": 10001,
        "msg": "invalid card payload",
        "webhook": "https://example.com/webhook",
        "sign": "abc",
        "token": "boxcn",
        "app_secret": "app-secret",
        "api_key": "key",
    }
    _install_fake_client(monkeypatch, httpx.Response(200, json=body))
    settings = Settings(
        FEISHU_BOT_WEBHOOK_URL="https://example.com/webhook",
        FEISHU_BOT_SECRET="bot-secret",
        FEISHU_BOT_FALLBACK_TEXT=False,
    )

    result = maybe_send_bot_card(settings, _brief(), dry_run=False, skip_llm=False, send_bot=True)

    summary = result["response_body_summary"]
    assert "https://example.com/webhook" not in summary
    assert "abc" not in summary
    assert "boxcn" not in summary
    assert "app-secret" not in summary
    assert '"key"' not in summary
    assert "sign" not in summary.lower()
    assert "token" not in summary.lower()
