from __future__ import annotations

from pathlib import Path

from .models import EvidenceItem
from .models import TimeWindow
from .utils import safe_filename


URL_MARKER = "## 附录：本次证据来源索引"


def save_report(output_dir: Path, window: TimeWindow, content: str) -> Path:
    folder = output_dir / window.date_str
    folder.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(f"AI_radar_{window.date_str}.md")
    path = folder / filename
    path.write_text(content, encoding="utf-8")
    return path


def ensure_report_has_source_urls(report_md: str, evidence_items: list[EvidenceItem], *, max_sources: int = 30) -> str:
    if "http://" in report_md or "https://" in report_md:
        return report_md
    sources = [item for item in evidence_items if item.url][:max_sources]
    if not sources:
        return report_md
    lines = [
        "",
        "",
        URL_MARKER,
        "",
    ]
    for idx, item in enumerate(sources, start=1):
        title = str(item.title or item.source or f"Evidence {idx}").strip()
        source = str(item.source or item.source_type or "").strip()
        suffix = f" — {source}" if source else ""
        lines.append(f"- [E{idx}] [{title}]({item.url}){suffix}")
    return report_md.rstrip() + "\n".join(lines) + "\n"
