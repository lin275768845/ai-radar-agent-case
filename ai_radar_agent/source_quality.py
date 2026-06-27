from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from .models import EvidenceItem


PROVIDER_LABELS = {"bocha", "tavily", "rss", "search", "unknown"}

DEFAULT_OFFICIAL_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "nvidia.com",
    "blogs.nvidia.com",
    "microsoft.com",
    "aws.amazon.com",
    "about.fb.com",
    "meta.com",
    "cloud.tencent.com",
    "aliyun.com",
    "qwenlm.github.io",
    "deepseek.com",
    "moonshot.cn",
    "volcengine.com",
    "minimax.io",
    "github.com",
    "huggingface.co",
}

DEFAULT_AUTHORITATIVE_MEDIA = {
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "theinformation.com",
    "techcrunch.com",
    "theverge.com",
    "stcn.com",
    "yicai.com",
    "cls.cn",
    "jiqizhixin.com",
    "qbitai.com",
    "36kr.com",
    "ithome.com",
    "ce.cn",
}

DEFAULT_DATA_SOURCES = {
    "openrouter.ai",
    "artificialanalysis.ai",
    "lmarena.ai",
    "chatbotarena.com",
    "swebench.com",
    "aider.chat",
    "similarweb.com",
    "sensortower.com",
    "github.com",
    "huggingface.co",
}

DEFAULT_AGGREGATOR_DOMAINS = {
    "baijiahao.baidu.com",
    "toutiao.com",
    "finance.sina.cn",
    "m.cfi.cn",
    "10jqka.com.cn",
    "sohu.com",
    "wallstreetcn.com",
}


@dataclass(frozen=True)
class SourceQuality:
    source_tier: str
    source_fit: str
    source_quality_score: int
    is_primary_source: bool
    source_quality_reason: str
    source_label: str
    host: str


@dataclass(frozen=True)
class SourceQualityConfig:
    official_domains: set[str]
    authoritative_media_domains: set[str]
    data_source_domains: set[str]
    aggregator_domains: set[str]


def load_source_quality_config(path: Path | None = None) -> SourceQualityConfig:
    data: dict[str, object] = {}
    if path and path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            data = loaded
    return SourceQualityConfig(
        official_domains=_as_domain_set(data.get("official_domains"), DEFAULT_OFFICIAL_DOMAINS),
        authoritative_media_domains=_as_domain_set(data.get("authoritative_media_domains"), DEFAULT_AUTHORITATIVE_MEDIA),
        data_source_domains=_as_domain_set(data.get("data_source_domains"), DEFAULT_DATA_SOURCES),
        aggregator_domains=_as_domain_set(data.get("aggregator_domains"), DEFAULT_AGGREGATOR_DOMAINS),
    )


def score_source(item: EvidenceItem, config: SourceQualityConfig | None = None) -> SourceQuality:
    config = config or load_source_quality_config()
    host = _host(item.url)
    label = normalize_source_label(item.source, item.url)
    host_for_match = _strip_mobile_prefix(host)
    if _is_search_result_url(host, item.url):
        return SourceQuality("S5", "low", 10, False, "search result page", label, host)
    if _domain_matches(host, config.aggregator_domains):
        return SourceQuality("S5", "low", 20, False, "aggregator or repost domain", label, host)
    if _domain_matches(host_for_match, config.official_domains):
        fit = "medium" if _has_mobile_prefix(host) else "high"
        score = 85 if fit == "medium" else 95
        reason = "official domain; downgraded for mobile URL" if fit == "medium" else "official domain"
        return SourceQuality("S1", fit, score, True, reason, label, host)
    if _domain_matches(host_for_match, config.authoritative_media_domains):
        fit = "medium" if _has_mobile_prefix(host) else "high"
        score = 68 if fit == "medium" else 82
        reason = "authoritative media; downgraded for mobile URL" if fit == "medium" else "authoritative media"
        return SourceQuality("S2", fit, score, False, reason, label, host)
    if _domain_matches(host_for_match, config.data_source_domains):
        fit = "medium" if _has_mobile_prefix(host) else "high"
        score = 72 if fit == "medium" else 88
        reason = "data source; downgraded for mobile URL" if fit == "medium" else "data source"
        return SourceQuality("S3", fit, score, False, reason, label, host)
    if _has_mobile_prefix(host):
        return SourceQuality("S4", "medium", 45, False, "mobile URL; downgraded", label, host)
    if not host:
        return SourceQuality("S5", "low", 15, False, "missing URL host", label, host)
    return SourceQuality("S4", "medium", 50, False, "unclassified source", label, host)


def apply_source_quality(item: EvidenceItem, config: SourceQualityConfig | None = None) -> EvidenceItem:
    quality = score_source(item, config)
    item.source = quality.source_label
    item.source_tier = quality.source_tier
    item.source_fit = quality.source_fit
    item.source_quality_score = quality.source_quality_score
    item.is_primary_source = quality.is_primary_source
    item.source_quality_reason = quality.source_quality_reason
    return item


def normalize_source_label(source: str, url: str) -> str:
    value = " ".join(str(source or "").strip().split())
    if value and value.lower() not in PROVIDER_LABELS:
        return value
    host = _host(url)
    if not host:
        return ""
    host = _strip_mobile_prefix(host)
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def source_quality_counts(items: list[EvidenceItem]) -> dict[str, int]:
    return {
        "primary_sources_count": sum(1 for item in items if item.is_primary_source),
        "official_sources_count": sum(1 for item in items if item.source_tier == "S1"),
        "authoritative_media_count": sum(1 for item in items if item.source_tier == "S2"),
        "aggregator_sources_count": sum(1 for item in items if item.source_tier == "S5" or item.source_fit == "low"),
    }


def _as_domain_set(value: object, defaults: set[str]) -> set[str]:
    if not isinstance(value, list):
        return set(defaults)
    output = {str(item).strip().lower() for item in value if str(item).strip()}
    return output or set(defaults)


def _host(url: str) -> str:
    try:
        return urlsplit(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return ""


def _strip_mobile_prefix(host: str) -> str:
    for prefix in ("m.", "wap.", "3g."):
        if host.startswith(prefix):
            return host[len(prefix) :]
    return host


def _has_mobile_prefix(host: str) -> bool:
    return host.startswith(("m.", "wap.", "3g."))


def _domain_matches(host: str, domains: set[str]) -> bool:
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def _is_search_result_url(host: str, url: str) -> bool:
    path = urlsplit(url).path.lower()
    return (
        (host.endswith("google.com") and "/search" in path)
        or (host.endswith("bing.com") and "/search" in path)
        or (host.endswith("baidu.com") and ("/s" in path or "wd=" in url))
    )
