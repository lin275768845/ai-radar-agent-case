from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import re
import time
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

import httpx

from .config import Settings

logger = logging.getLogger(__name__)

MAX_TOP_EVENTS_PER_REGION = 6
BAD_SOURCE_LABELS = {"tavily", "tavily.tavily", "rss", "rss.rss", "unknown", "unknown.unknown", "none", "none.none"}
DOMAIN_LABELS = {
    "finance.sina.com.cn": "新浪财经",
    "sina.com.cn": "新浪",
    "wap.eastmoney.com": "东方财富",
    "eastmoney.com": "东方财富",
    "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    "openai.com": "OpenAI",
    "anthropic.com": "Anthropic",
    "nvidia.com": "NVIDIA",
    "blogs.nvidia.com": "NVIDIA Blog",
    "microsoft.com": "Microsoft",
    "aws.amazon.com": "AWS",
    "aboutamazon.com": "Amazon",
    "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg",
    "theinformation.com": "The Information",
    "ft.com": "FT",
    "wsj.com": "WSJ",
    "github.com": "GitHub",
    "huggingface.co": "Hugging Face",
    "arxiv.org": "arXiv",
}
TITLE_MAX_CHARS = 28
CARD_FIELD_FALLBACK_TEXT = "LLM返回超字数，请查看完整日报"


@dataclass
class BotResult:
    attempted: bool = False
    sent: bool = False
    skipped: bool = False
    reason: str = ""
    status_code: int | None = None
    response_code: int | None = None
    response_msg: str = ""
    response_body_summary: str = ""
    error_summary: str = ""
    card_title: str = ""
    doc_url_present: bool = False
    link_target: str = "none"
    text_fallback_attempted: bool = False
    text_fallback_sent: bool = False
    text_fallback_reason: str = ""
    text_fallback_status_code: int | None = None
    text_fallback_response_code: int | None = None
    text_fallback_response_msg: str = ""
    text_fallback_error_summary: str = ""
    text_fallback_body_summary: str = ""
    domestic_items_input_count: int = 0
    overseas_items_input_count: int = 0
    domestic_items_rendered_count: int = 0
    overseas_items_rendered_count: int = 0
    domestic_items_truncated: bool = False
    overseas_items_truncated: bool = False
    card_items_truncated: bool = False
    card_truncated_reason: str = ""
    title_truncation_count: int = 0
    title_truncation_examples: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def get(self, key: str, default: Any = None) -> Any:
        return self.to_dict().get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.to_dict()[key]


def ensure_bot_result(value: BotResult | dict[str, Any]) -> BotResult:
    if isinstance(value, BotResult):
        return value
    result = BotResult()
    field_names = set(result.to_dict())
    for key, item in value.items():
        if key == "title":
            result.card_title = str(item or "")
        elif key == "canonical_type":
            result.link_target = str(item or "none")
        elif key == "doc_url_present":
            result.doc_url_present = bool(item)
        elif key in field_names:
            setattr(result, key, item)
    return result


def sign(timestamp: str, secret: str) -> str:
    digest = hmac.new(f"{timestamp}\n{secret}".encode("utf-8"), b"", digestmod=hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def build_card_payload(brief: dict[str, Any]) -> dict[str, Any]:
    payload, _meta = _build_card_payload_with_meta(brief)
    return payload


def _build_card_payload_with_meta(brief: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    title = _card_title(brief)
    elements: list[dict[str, Any]] = []
    meta = _render_meta(brief)

    if brief.get("brief_generation_status") == "fallback":
        elements.append({"tag": "markdown", "content": "今日简报摘要未能稳定生成，请查看完整日报。"})
        doc_url = str(brief.get("doc_url") or "")
        if doc_url:
            elements.append(
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "查看完整日报"},
                            "url": doc_url,
                            "type": "primary",
                        }
                    ],
                }
            )
        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
                "elements": elements,
            },
        }, meta

    def add_section(name: str, items: list[dict[str, Any]], region: str) -> None:
        rendered_items = _capped_top_items(items)
        truncated = len(_valid_items(items)) > len(rendered_items)
        if truncated:
            meta[f"{region}_items_truncated"] = True
            meta["card_items_truncated"] = True
            meta["card_truncated_reason"] = "max_6_per_region"
        text_lines = [f"**{name}**"]
        if not rendered_items:
            text_lines.append("今日无强核心事件，不强行凑数。")
        for idx, item in enumerate(rendered_items, start=1):
            title, title_truncated = _item_card_title(item)
            if title_truncated:
                meta["title_truncation_count"] += 1
                if len(meta["title_truncation_examples"]) < 5:
                    meta["title_truncation_examples"].append(f"{item.get('title', '')} -> {title}")
            why = _item_card_why(item, 70)
            text_lines.append(f"{idx}. **{title}**｜{item.get('priority', '观察')}")
            if why:
                text_lines.append(f"   {why}")
            source_text = _source_links(item.get("sources") or [])
            if source_text:
                text_lines.append(f"   来源：{source_text}")
        if truncated:
            text_lines.append("更多详情见完整日报。")
        content = "\n".join(text_lines)
        if len(content) > 7000:
            compact_lines = [text_lines[0]]
            if not rendered_items:
                compact_lines.append("今日无强核心事件，不强行凑数。")
            for idx, item in enumerate(rendered_items, start=1):
                title, _title_truncated = _item_card_title(item)
                compact_lines.append(f"{idx}. **{title}**｜{item.get('priority', '观察')}")
                why = _item_card_why(item, 45)
                if why:
                    compact_lines.append(f"   {why}")
                source_text = _source_links(item.get("sources") or [])
                if source_text:
                    compact_lines.append(f"   来源：{source_text}")
            if truncated:
                compact_lines.append("更多详情见完整日报。")
            content = "\n".join(compact_lines)
        if len(content) > 7000:
            meta["card_items_truncated"] = True
            meta["card_truncated_reason"] = meta["card_truncated_reason"] or "payload_too_long"
            content = _truncate(content, 6970) + "\n其余详情见完整日报"
        elements.append({"tag": "markdown", "content": content})

    add_section("国内 Top", brief.get("domestic_top") or [], "domestic")
    add_section("海外 Top", brief.get("overseas_top") or [], "overseas")

    judgments = brief.get("core_judgments") or []
    if judgments:
        elements.append({"tag": "markdown", "content": _card_bullet_section("今日核心判断", _card_bullets(brief, "core_judgments"))})

    watch_signals = brief.get("watch_signals") or []
    if watch_signals:
        elements.append({"tag": "markdown", "content": _card_bullet_section("观察信号", _card_bullets(brief, "watch_signals"))})

    doc_url = str(brief.get("doc_url") or "")
    if doc_url:
        elements.append(
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "查看完整日报"},
                        "url": doc_url,
                        "type": "primary",
                    }
                ],
            }
        )

    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
            "elements": elements,
        },
    }, meta


def build_text_payload(brief: dict[str, Any]) -> dict[str, Any]:
    lines = [_card_title(brief)]
    if brief.get("brief_generation_status") == "fallback":
        lines.append("今日简报摘要未能稳定生成，请查看完整日报。")
        doc_url = str(brief.get("doc_url") or "")
        if doc_url:
            lines.append(f"查看完整日报：{doc_url}")
        text = _truncate("\n".join(lines), 3500)
        return {"msg_type": "text", "content": {"text": text}}
    for name, key in (("国内 Top", "domestic_top"), ("海外 Top", "overseas_top")):
        lines.append(name)
        items = _capped_top_items(brief.get(key) or [])
        if not items:
            lines.append("今日无强核心事件，不强行凑数。")
        for item in items:
            title, _title_truncated = _item_card_title(item)
            lines.append(f"- [{item.get('priority', '观察')}] {title}：{_item_card_why(item, 55)}")
            source_text = _source_links(item.get("sources") or [])
            if source_text:
                lines.append(f"  来源：{source_text}")
        if len(_valid_items(brief.get(key) or [])) > len(items):
            lines.append("更多详情见完整日报。")
    watch_signals = brief.get("watch_signals") or []
    if watch_signals:
        lines.append("观察信号")
        for item in _card_bullets(brief, "watch_signals"):
            lines.append(f"- {item}")
    doc_url = str(brief.get("doc_url") or "")
    if doc_url:
        lines.append(f"查看完整日报：{doc_url}")
    text = _truncate("\n".join(lines), 3500)
    return {"msg_type": "text", "content": {"text": text}}


def maybe_send_bot_card(
    settings: Settings,
    brief: dict[str, Any],
    *,
    dry_run: bool,
    skip_llm: bool,
    send_bot: bool,
) -> BotResult:
    title = _card_title(brief)
    payload, render_meta = _build_card_payload_with_meta(brief)
    doc_url_exists = bool(brief.get("doc_url"))
    link_target = str(brief.get("canonical_type") or ("none" if not doc_url_exists else "unknown"))
    if dry_run:
        return _with_render_meta(_skipped("dry_run", title=title, doc_url_present=doc_url_exists, link_target=link_target), render_meta)
    if skip_llm:
        return _with_render_meta(_skipped("skip_llm", title=title, doc_url_present=doc_url_exists, link_target=link_target), render_meta)
    if not send_bot:
        return _with_render_meta(_skipped("send_bot=false", title=title, doc_url_present=doc_url_exists, link_target=link_target), render_meta)
    if not settings.feishu_bot_webhook_url:
        return _with_render_meta(_skipped("missing_webhook", title=title, doc_url_present=doc_url_exists, link_target=link_target), render_meta)
    if not brief.get("doc_url"):
        return _with_render_meta(_skipped("missing_doc_url", title=title, doc_url_present=doc_url_exists, link_target=link_target), render_meta)

    result = _post_payload(settings, payload, title=title, doc_url_present=doc_url_exists, link_target=link_target)
    _with_render_meta(result, render_meta)
    if result.sent:
        logger.info("Feishu bot status: bot sent=true canonical_type=%s doc_url exists=%s", link_target, _bool(doc_url_exists))
        return result

    if getattr(settings, "feishu_bot_fallback_text", True) and result.reason == "payload_invalid":
        card_failure_reason = result.reason
        text_result = _post_payload(
            settings,
            build_text_payload(brief),
            title=title,
            doc_url_present=doc_url_exists,
            link_target=link_target,
        )
        _with_render_meta(text_result, render_meta)
        result.text_fallback_attempted = True
        result.text_fallback_sent = text_result.sent
        result.text_fallback_reason = text_result.reason
        result.text_fallback_status_code = text_result.status_code
        result.text_fallback_response_code = text_result.response_code
        result.text_fallback_response_msg = text_result.response_msg
        result.text_fallback_error_summary = text_result.error_summary
        result.text_fallback_body_summary = text_result.response_body_summary
        if text_result.sent:
            result.sent = True
            result.reason = "card_failed_text_fallback_sent"
            result.error_summary = _truncate(
                f"card_failed reason={card_failure_reason}; card_msg={result.response_msg}; text_fallback sent=true",
                300,
            )
            logger.info("Feishu bot status: card failed but text fallback sent=true canonical_type=%s", link_target)
            return result
        result.reason = "card_and_text_failed"
        result.error_summary = _truncate(
            f"card_reason={result.response_msg or result.response_code or result.status_code}; "
            f"text_reason={text_result.reason}; text_msg={text_result.response_msg}",
            300,
        )

    logger.warning(
        "Feishu bot send failed: reason=%s status_code=%s response_code=%s response_msg=%s error=%s",
        result.reason,
        result.status_code,
        result.response_code,
        result.response_msg,
        result.error_summary,
    )
    logger.info("Feishu bot status: bot sent=false canonical_type=%s doc_url exists=%s", link_target, _bool(doc_url_exists))
    return result


def _post_payload(
    settings: Settings,
    payload: dict[str, Any],
    *,
    title: str,
    doc_url_present: bool,
    link_target: str,
) -> BotResult:
    signed_payload = _with_signature(payload, settings.feishu_bot_secret)
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(settings.feishu_bot_webhook_url, json=signed_payload)
    except httpx.RequestError as exc:
        return BotResult(
            attempted=True,
            sent=False,
            skipped=False,
            reason="webhook_http_error",
            error_summary=_truncate(f"{type(exc).__name__}: {exc}", 300),
            card_title=title,
            doc_url_present=doc_url_present,
            link_target=link_target,
        )

    body = _response_body(resp)
    summary = _body_summary(body, settings)
    result = BotResult(
        attempted=True,
        sent=False,
        skipped=False,
        status_code=resp.status_code,
        response_body_summary=summary,
        card_title=title,
        doc_url_present=doc_url_present,
        link_target=link_target,
    )
    if resp.status_code != 200:
        result.reason = "webhook_http_status"
        return result
    if not isinstance(body, dict):
        result.reason = "invalid_json_response"
        return result
    code = body.get("code")
    code_value = int(code) if isinstance(code, int | str) and str(code).lstrip("-").isdigit() else None
    msg = str(body.get("msg") or body.get("message") or "")
    result.response_code = code_value
    result.response_msg = _truncate(_redact_sensitive(msg, settings), 300)
    if code_value == 0:
        result.sent = True
        result.reason = "sent"
        return result
    result.reason = _classify_webhook_error(msg)
    return result


def _with_signature(payload: dict[str, Any], secret: str) -> dict[str, Any]:
    if not secret:
        return payload
    signed = dict(payload)
    timestamp = str(int(time.time()))
    signed["timestamp"] = timestamp
    signed["sign"] = sign(timestamp, secret)
    return signed


def _skipped(reason: str, *, title: str, doc_url_present: bool, link_target: str) -> BotResult:
    logger.info(reason)
    return BotResult(
        attempted=False,
        sent=False,
        skipped=True,
        reason=reason,
        card_title=title,
        doc_url_present=doc_url_present,
        link_target=link_target,
    )


def _with_render_meta(result: BotResult, meta: dict[str, Any]) -> BotResult:
    result.domestic_items_input_count = int(meta.get("domestic_items_input_count") or 0)
    result.overseas_items_input_count = int(meta.get("overseas_items_input_count") or 0)
    result.domestic_items_rendered_count = int(meta.get("domestic_items_rendered_count") or 0)
    result.overseas_items_rendered_count = int(meta.get("overseas_items_rendered_count") or 0)
    result.domestic_items_truncated = bool(meta.get("domestic_items_truncated", False))
    result.overseas_items_truncated = bool(meta.get("overseas_items_truncated", False))
    result.card_items_truncated = bool(meta.get("card_items_truncated", False))
    result.card_truncated_reason = str(meta.get("card_truncated_reason") or "")
    result.title_truncation_count = int(meta.get("title_truncation_count") or 0)
    result.title_truncation_examples = list(meta.get("title_truncation_examples") or [])
    return result


def _render_meta(brief: dict[str, Any]) -> dict[str, Any]:
    if brief.get("brief_generation_status") == "fallback":
        domestic_input_count = domestic_count = 0
        overseas_input_count = overseas_count = 0
    else:
        domestic_input_count = len(_valid_items(brief.get("domestic_top") or []))
        overseas_input_count = len(_valid_items(brief.get("overseas_top") or []))
        domestic_count = min(domestic_input_count, MAX_TOP_EVENTS_PER_REGION)
        overseas_count = min(overseas_input_count, MAX_TOP_EVENTS_PER_REGION)
    return {
        "domestic_items_input_count": domestic_input_count,
        "overseas_items_input_count": overseas_input_count,
        "domestic_items_rendered_count": domestic_count,
        "overseas_items_rendered_count": overseas_count,
        "domestic_items_truncated": domestic_input_count > domestic_count,
        "overseas_items_truncated": overseas_input_count > overseas_count,
        "card_items_truncated": False,
        "card_truncated_reason": "",
        "title_truncation_count": 0,
        "title_truncation_examples": [],
    }


def _response_body(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text


def _body_summary(body: Any, settings: Settings) -> str:
    if isinstance(body, str):
        text = body
    else:
        text = json.dumps(body, ensure_ascii=False, sort_keys=True)
    return _truncate(_redact_sensitive(text, settings), 1000)


def _redact_sensitive(text: str, settings: Settings) -> str:
    redacted = text
    for secret in (settings.feishu_bot_webhook_url, settings.feishu_bot_secret):
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    redacted = re.sub(
        r'(?i)("?(?:sign|token|app_secret|secret|api[_-]?key)"?\s*[:=]\s*")([^"]+)(")',
        r'"redacted_field": "[REDACTED]"',
        redacted,
    )
    redacted = re.sub(
        r"(?i)((?:sign|token|app_secret|secret|api[_-]?key)\s*[:=]\s*)([^\s,;}&]+)",
        r"redacted_field=[REDACTED]",
        redacted,
    )
    return redacted


def _classify_webhook_error(msg: str) -> str:
    lowered = msg.lower()
    if "sign" in lowered or "signature" in lowered:
        return "signature_error"
    if "keyword" in lowered or "key word" in lowered or "关键词" in msg:
        return "keyword_mismatch"
    if "ip" in lowered and ("allow" in lowered or "white" in lowered or "白名单" in msg):
        return "ip_not_allowed"
    if any(text in lowered for text in ("payload", "card", "invalid", "bad request", "format")) or any(
        text in msg for text in ("参数", "格式", "卡片")
    ):
        return "payload_invalid"
    return "webhook_error"


def _source_links(sources: list[dict[str, Any]]) -> str:
    links = []
    seen_urls: set[str] = set()
    seen_labels: set[str] = set()
    for source in sources:
        url = str(source.get("url") or "")
        if not url:
            continue
        if _is_disallowed_source_url(url):
            continue
        normalized_url = _normalize_url(url)
        if normalized_url in seen_urls:
            continue
        label = _source_label(source)
        if not label:
            continue
        normalized_label = label.lower()
        if normalized_label in seen_labels:
            continue
        seen_urls.add(normalized_url)
        seen_labels.add(normalized_label)
        links.append(f"[{label}]({url})")
        if len(links) == 2:
            break
    return " · ".join(links)


def _valid_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in items if isinstance(item, dict) and not _is_empty_placeholder_item(item)]


def _capped_top_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _sort_top_items(items)[:MAX_TOP_EVENTS_PER_REGION]


def _sort_top_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    indexed = [(idx, item) for idx, item in enumerate(items) if isinstance(item, dict) and not _is_empty_placeholder_item(item)]
    indexed.sort(key=lambda row: (_priority_rank(row[1].get("priority")), row[0]))
    return [item for _idx, item in indexed]


def _priority_rank(priority: Any) -> int:
    raw = str(priority or "")
    text = raw.upper()
    if "P1" in text:
        return 0
    if "P2" in text:
        return 1
    if "观察" in raw or "OBSERVE" in text:
        return 2
    return 9


def _is_empty_placeholder_item(item: dict[str, Any]) -> bool:
    title = str(item.get("title") or "")
    card_title = str(item.get("card_title") or "")
    why = str(item.get("why") or "")
    card_why = str(item.get("card_why") or "")
    return _is_no_core_text(title) or _is_no_core_text(card_title) or (
        title.strip() in {"—", "-", "–", "--"} and ("详见完整日报" in why or "详见完整日报" in card_why)
    ) or ("无强核心事件" in title and "不强行凑数" in why)


def _is_no_core_text(value: str) -> bool:
    text = str(value or "").strip()
    if text in {"—", "-", "–", "--", "无", "无。", "N/A", "n/a", "NA", "na", "None", "none"}:
        return True
    compact = re.sub(r"\s+", "", text)
    if (
        re.search(r"无(国内|海外)?强?核心事件", compact)
        or re.search(r"(国内|海外)无强?核心事件", compact)
        or re.search(r"无.{0,12}(国内|海外)?.{0,6}核心事件", compact)
        or re.search(r"未发现.{0,20}(国内|海外)?.{0,8}核心事件", compact)
        or re.search(r"无.{0,16}核心.{0,8}事件", compact)
    ):
        return True
    return any(
        marker in text
        for marker in ("无强核心事件", "不强行凑数", "无 P1/P2", "无P1/P2", "本日无入选核心事件", "详见完整日报")
    )


def _source_label(source: dict[str, Any]) -> str:
    provider = source.get("provider") or source.get("source_type")
    explicit_label = str(source.get("source") or source.get("source_name") or "").strip()
    if explicit_label and not _is_bad_source_label(explicit_label):
        raw_value = explicit_label
    elif _is_bad_source_label(str(provider or "")):
        raw_value = ""
    else:
        raw_value = source.get("title")
    label = _clean_source_label(
        raw_value,
        str(source.get("url") or ""),
        provider=provider,
    )
    if label:
        return label
    return ""


def _clean_source_label(value: Any, url: str = "", *, provider: Any = "") -> str:
    if _is_disallowed_source_url(url):
        return ""
    label = _dedupe_label(str(value or "").strip())
    provider_label = _dedupe_label(str(provider or "").strip())
    if _is_bad_source_label(label):
        label = ""
    if label:
        label = _human_source_label(label)
    if not label and url:
        label = _human_source_label(_domain(url))
    if not label and not _is_bad_source_label(provider_label):
        label = _human_source_label(provider_label)
    return _truncate(label, 24)


def _dedupe_label(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    parts = [part for part in re.split(r"[.\s]+", text) if part]
    if len(parts) == 2 and parts[0].lower() == parts[1].lower():
        return parts[0]
    return text


def _is_bad_source_label(value: str) -> bool:
    cleaned = value.strip().lower()
    return cleaned in BAD_SOURCE_LABELS or cleaned.startswith("tavily") or cleaned.startswith("rss")


def _human_source_label(value: str) -> str:
    cleaned = _clean_domain_label_key(value)
    return DOMAIN_LABELS.get(cleaned, DOMAIN_LABELS.get(_root_domain(cleaned), value.strip()))


def _clean_domain_label_key(value: str) -> str:
    cleaned = value.lower().strip().removeprefix("www.")
    for prefix in ("m.", "wap.", "mobile."):
        cleaned = cleaned.removeprefix(prefix)
    return cleaned


def _root_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in {"com", "net", "org", "co"}:
        return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def _domain(url: str) -> str:
    return urlsplit(str(url or "")).netloc.lower().replace("www.", "")


def _is_disallowed_source_url(url: str) -> bool:
    host = _domain(url)
    return bool(host and ("tavily" in host or host in {"google.com", "bing.com", "search.yahoo.com"}))


def _normalize_url(url: str) -> str:
    cleaned = unquote(str(url or "").rstrip(".,;，。；/"))
    parts = urlsplit(cleaned)
    if not parts.netloc:
        return ""
    query = urlencode(
        [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if not key.lower().startswith("utm_")
        ]
    )
    return urlunsplit(("https", parts.netloc.lower(), parts.path.rstrip("/"), query, ""))


def _item_card_title(item: dict[str, Any]) -> tuple[str, bool]:
    raw = str(item.get("card_title") or item.get("title") or "").strip()
    title = re.sub(r"\s+", " ", raw)
    return title, title != raw


def _item_card_why(item: dict[str, Any], max_len: int) -> str:
    for value in (item.get("card_why"), item.get("why")):
        raw = re.sub(r"\s+", " ", str(value or "").strip())
        if not raw or _bad_card_why_fragment(raw):
            continue
        return raw if len(raw) <= max_len else CARD_FIELD_FALLBACK_TEXT
    return ""


def _bad_card_why_fragment(value: str) -> bool:
    text = re.sub(r"\s+", "", str(value or "").strip(" ：:；;，,。"))
    if not text:
        return True
    if text in {"当前内容为空", "内容为空", "暂无摘要"}:
        return True
    if re.fullmatch(r"\d+[.)、]?", text):
        return True
    if re.search(r"\|\s*P[12]\s*\|", text):
        return True
    return bool(re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9·]{0,12}(透露|表示|称|披露|发布|宣布|报道|指出)", text))


def smart_title_for_card(title: str, max_chars: int = TITLE_MAX_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(title or "").strip())
    if len(text) <= max_chars:
        return text
    limit = max(1, max_chars - 1)
    cut = _smart_cut_index(text, limit)
    return text[:cut].rstrip(" ，,、；;：:。.-") + "…"


def _smart_cut_index(text: str, limit: int) -> int:
    punct = "，,、；;：:。.!！?？)"
    for idx in range(limit, max(0, limit - 10), -1):
        if idx <= 0:
            break
        prev = text[idx - 1]
        current = text[idx] if idx < len(text) else ""
        if prev.isspace() or prev in punct:
            return idx
        if not _is_ascii_word(prev) and current and _is_ascii_word(current):
            return idx
        if _is_ascii_word(prev) and current and not _is_ascii_word(current):
            return idx
    cut = min(limit, len(text))
    while cut > 0 and cut < len(text) and _is_ascii_word(text[cut - 1]) and _is_ascii_word(text[cut]):
        cut -= 1
    return cut or limit


def _is_ascii_word(char: str) -> bool:
    return bool(re.match(r"[A-Za-z0-9]", char or ""))


def _card_title(brief: dict[str, Any]) -> str:
    fallback = f"AI Radar｜{brief.get('date', '')}".strip()
    title = str(brief.get("title") or "").strip()
    suffix = _card_title_ref_suffix()
    if title.startswith("AI Radar｜"):
        return _truncate(_append_title_suffix(title, suffix), 60)
    return _truncate(_append_title_suffix(fallback or title or "AI Radar", suffix), 60)


def _card_title_ref_suffix() -> str:
    ref = (os.getenv("GITHUB_REF_NAME") or os.getenv("GITHUB_REF") or "").strip()
    ref = ref.removeprefix("refs/heads/").removeprefix("refs/tags/")
    if not ref:
        return ""
    if ref.startswith(("stable/", "release/", "hotfix/")):
        return ref.rsplit("/", 1)[-1]
    return ref


def _append_title_suffix(title: str, suffix: str) -> str:
    if not suffix or title.endswith(f"｜{suffix}"):
        return title
    return f"{title}｜{suffix}"


def _card_bullet_section(title: str, items: list[Any]) -> str:
    lines = [f"**{title}**"]
    for item in items[:3]:
        text = _card_text_value(item)
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines)


def _card_bullets(brief: dict[str, Any], field: str) -> list[str]:
    values = brief.get(f"{field}_card") or brief.get(field) or []
    output = []
    for item in values:
        text = _card_text_value(item)
        if text:
            output.append(text)
        if len(output) >= 3:
            break
    return output


def _card_text_value(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("card") or value.get("full") or value.get("text") or ""
    return re.sub(r"\s+", " ", str(value or "").strip())


def _truncate_card_text(value: str, max_len: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    if len(text) <= max_len:
        return text
    limit = max(1, max_len - 1)
    cut = _card_cut_index(text, limit)
    clipped = text[:cut].rstrip(" ，,、；;：:。.-")
    return (clipped or text[:limit].rstrip()) + "…"


def _card_cut_index(text: str, limit: int) -> int:
    limit = min(limit, len(text))
    for punct in ("。.!！?？", "；;", "，,", " "):
        for idx in range(limit - 1, max(-1, limit - 35), -1):
            if text[idx] in punct:
                return idx if text[idx].isspace() else idx + 1
    return _smart_cut_index(text, limit)


def _truncate(value: str, max_len: int) -> str:
    return value if len(value) <= max_len else value[: max_len - 1] + "…"


def _bool(value: object) -> str:
    return str(bool(value)).lower()
