from __future__ import annotations

import argparse
import json
import logging
import os
import re
from datetime import date
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from . import __app_version__, __version__
from .brief import DeepSeekBriefGenerator, render_brief_markdown
from .collector import collect_evidence_with_audit
from .config import Settings
from .dates import previous_complete_day, window_for_date
from .evidence_gate import (
    EvidenceGateAudit,
    EvidenceGateResult,
    render_dropped_markdown,
    run_evidence_gate,
)
from .event_history import (
    EventHistoryMatchAudit,
    FinalTopDedupeAudit,
    append_event_history,
    build_history_prompt_context,
    dedupe_final_top_events,
    load_recent_event_history,
    mark_history_matches,
    render_event_history_context,
)
from .feishu import FeishuClient
from .feishu_bot import BotResult, ensure_bot_result, maybe_send_bot_card
from .feishu_docx import FeishuDocxImporter, FeishuDocxImportError
from .feishu_result import FeishuResult, ensure_feishu_result
from .fetchers.bocha_search import BochaFetcher
from .final_top_auditor import audit_final_top_with_llm
from .llm import DeepSeekGenerator, build_evidence_context
from .models import EvidenceItem
from .models import RecallAudit, TimeWindow
from .report import ensure_report_has_source_urls, save_report
from .report_lint import ReportLintResult, lint_report
from .report_reconcile import (
    drop_stale_final_top_from_candidate_metadata,
    drop_stale_final_top_from_evidence,
    reconcile_report_with_final_brief,
)
from .top_event_audit import audit_top_events
from .utils import evidence_to_markdown, save_json, setup_logging

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Radar Agent")
    parser.add_argument("--version", action="version", version=f"ai-radar-agent {__version__}")
    parser.add_argument("--date", help="Target Beijing natural day, e.g. 2026-06-01. Default: yesterday in RADAR_TIMEZONE")
    parser.add_argument("--dry-run", action="store_true", help="Collect evidence and write local files, but do not upload to Feishu")
    parser.add_argument("--skip-llm", action="store_true", help="Only collect evidence; useful for debugging source recall")
    parser.add_argument("--output-mode", choices=["none", "feishu_drive_md", "feishu_docx_import"])
    parser.add_argument("--send-bot", dest="send_bot", action="store_true", default=None)
    parser.add_argument("--no-send-bot", dest="send_bot", action="store_false")
    parser.add_argument("--force-republish", action="store_true", help="Publish again even if publish_result.json exists")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)
    load_dotenv()
    settings = Settings()
    if args.output_mode:
        settings.output_mode = args.output_mode
    if args.send_bot is not None:
        settings.send_bot = args.send_bot

    window = (
        window_for_date(date.fromisoformat(args.date), settings.radar_timezone)
        if args.date
        else previous_complete_day(tz_name=settings.radar_timezone)
    )
    print(f"Target window: {window.display_range}")

    if not args.skip_llm:
        settings.validate_for_generation()

    raw_evidence, audit = collect_evidence_with_audit(settings, window)
    evidence_dir = settings.output_dir / window.date_str
    evidence_dir.mkdir(parents=True, exist_ok=True)
    gate_result = _run_gate(settings, window, raw_evidence)
    evidence = gate_result.filtered
    history_events, history_match_audit = _run_event_history_matching(settings, window, evidence)
    evidence = _apply_event_history_filter_mode(settings, evidence, history_match_audit)
    history_summary = _event_history_summary(settings, history_match_audit, write_error="not_run")
    audit.total_evidence_count = len(evidence)
    save_json(evidence_dir / "evidence.json", [item.__dict__ for item in evidence])
    save_json(evidence_dir / "evidence_gate.json", gate_result.audit.to_dict())
    save_json(evidence_dir / "event_history_matches.json", history_match_audit.to_dict())
    (evidence_dir / "event_history_context.md").write_text(
        render_event_history_context(history_events, history_match_audit),
        encoding="utf-8",
    )
    (evidence_dir / "evidence_dropped.md").write_text(render_dropped_markdown(gate_result.audit), encoding="utf-8")
    llm_evidence_md = build_evidence_context(evidence, audit, gate_result.audit)
    history_prompt_context = build_history_prompt_context(history_events, history_match_audit)
    if history_prompt_context:
        llm_evidence_md = f"{llm_evidence_md}\n\n{history_prompt_context}"
    (evidence_dir / "evidence.md").write_text(
        evidence_to_markdown(evidence, audit, gate_result.audit, include_dropped=True),
        encoding="utf-8",
    )
    print(f"Collected evidence items: {len(evidence)}")
    if not evidence:
        _write_github_summary(
            window=window,
            audit=audit,
            output_mode=settings.output_mode,
            report_path=None,
            brief_path=None,
            feishu_result=_empty_feishu_result(settings.output_mode, skipped=True, reason="no_evidence"),
            bot_result={"sent": False, "skipped": True, "reason": "no_evidence"},
            print_feishu_url=getattr(settings, "print_feishu_url_in_summary", True),
            report_lint=None,
            evidence_gate_audit=gate_result.audit,
            event_history_summary={**history_summary, "event_history_write_error": "no_evidence"},
        )
        raise RuntimeError("No evidence collected from RSS, Bocha, or Tavily.")

    if args.skip_llm:
        print(f"Evidence saved to: {evidence_dir}")
        _write_github_summary(
            window=window,
            audit=audit,
            output_mode=settings.output_mode,
            report_path=None,
            brief_path=None,
            feishu_result=_empty_feishu_result(settings.output_mode, skipped=True, reason="skip_llm"),
            bot_result={"sent": False, "skipped": True, "reason": "bot skipped: skip_llm"},
            print_feishu_url=getattr(settings, "print_feishu_url_in_summary", True),
            report_lint=None,
            evidence_gate_audit=gate_result.audit,
            event_history_summary={**history_summary, "event_history_write_error": "skip_llm"},
        )
        return

    generator = DeepSeekGenerator(settings)
    report = generator.generate(window, llm_evidence_md)
    raw_generated_report = report
    report_path = save_report(settings.output_dir, window, report)
    report = ensure_report_has_source_urls(report, evidence)
    report_path.write_text(report, encoding="utf-8")
    print(f"Report saved locally: {report_path}")
    lint_policy = getattr(settings, "report_lint_policy", "warn")
    strict_lint = bool(getattr(settings, "strict_report_lint", False) or lint_policy == "strict")
    bot_block_on_lint_critical = bool(getattr(settings, "bot_block_on_lint_critical", False))

    brief = DeepSeekBriefGenerator(settings).generate(window, report, audit, doc_url="", evidence=evidence)
    final_top_dedupe_audit = FinalTopDedupeAudit(
        date=window.date_str,
        lookback_days=int(getattr(settings, "event_history_lookback_days", 5)),
        history_events_loaded=len(history_events),
    )
    if getattr(settings, "event_history_enabled", False):
        brief, final_top_dedupe_audit = dedupe_final_top_events(
            brief,
            history_events,
            target_date=window.date_str,
            lookback_days=int(getattr(settings, "event_history_lookback_days", 5)),
        )
    final_top_llm_audit_payload = {"enabled": bool(getattr(settings, "final_top_llm_audit_enabled", True))}
    if getattr(settings, "final_top_llm_audit_enabled", True):
        brief, final_top_dedupe_audit, final_top_llm_audit_payload = audit_final_top_with_llm(
            settings,
            brief,
            history_events,
            final_top_dedupe_audit,
        )
    brief = drop_stale_final_top_from_evidence(brief, evidence, window)
    brief = drop_stale_final_top_from_candidate_metadata(report, brief, window)
    brief_path = evidence_dir / "brief.json"
    brief_md_path = evidence_dir / "brief.md"
    save_json(evidence_dir / "final_top_dedupe.json", final_top_dedupe_audit.to_dict())
    save_json(evidence_dir / "final_top_llm_audit.json", final_top_llm_audit_payload)
    report = reconcile_report_with_final_brief(report, brief, window)
    brief = drop_stale_final_top_from_evidence(brief, evidence, window)
    brief = drop_stale_final_top_from_candidate_metadata(report, brief, window)
    report = reconcile_report_with_final_brief(report, brief, window)
    save_json(brief_path, brief)
    brief_md_path.write_text(render_brief_markdown(brief), encoding="utf-8")
    top_event_audit = audit_top_events(brief, evidence, window)
    save_json(evidence_dir / "top_event_audit.json", top_event_audit.to_dict())
    report = ensure_report_has_source_urls(report, evidence)
    report_path.write_text(report, encoding="utf-8")
    report_lint = lint_report(report, evidence, strict=strict_lint, target_date=window.date_str)
    report_lint = _merge_raw_generated_critical_lint(
        report_lint,
        raw_generated_report,
        evidence,
        strict=strict_lint,
        target_date=window.date_str,
    )
    save_json(evidence_dir / "report_lint.json", report_lint.to_dict())
    if strict_lint and (report_lint.errors or report_lint.critical_errors):
        _write_github_summary(
            window=window,
            audit=audit,
            output_mode=settings.output_mode,
            report_path=report_path,
            brief_path=brief_path,
            feishu_result=_empty_feishu_result(settings.output_mode, skipped=True, reason="report_lint_strict"),
            bot_result={"sent": False, "skipped": True, "reason": "bot skipped: report_lint_strict"},
            print_feishu_url=getattr(settings, "print_feishu_url_in_summary", True),
            report_lint=report_lint,
            report_lint_policy=lint_policy,
            bot_lint_action="blocked_by_errors" if report_lint.errors else "blocked_by_critical_errors",
            evidence_gate_audit=gate_result.audit,
            event_history_summary={**history_summary, "event_history_write_error": "report_lint_strict"},
        )
        raise RuntimeError("Report lint failed")

    feishu_result = _handle_feishu_output(
        settings,
        report_path,
        window,
        args.dry_run,
        force_republish=getattr(args, "force_republish", False),
    )
    feishu_result = ensure_feishu_result(feishu_result, settings.output_mode)
    brief["doc_url"] = feishu_result.canonical_url
    brief["canonical_type"] = feishu_result.canonical_type
    save_json(brief_path, brief)
    brief_md_path.write_text(render_brief_markdown(brief), encoding="utf-8")
    print(f"Brief saved locally: {brief_path}")

    should_send_bot = settings.send_bot and settings.output_mode not in {"none", "local"} and not args.dry_run
    bot_lint_action = _bot_lint_action(
        report_lint,
        lint_policy,
        bot_block_on_lint_critical=bot_block_on_lint_critical,
    )
    if bot_lint_action == "blocked_by_critical_errors":
        bot_result = {
            "attempted": False,
            "sent": False,
            "skipped": True,
            "reason": "report_lint_critical_errors",
            "card_title": "",
            "doc_url_present": bool(feishu_result.canonical_url),
            "link_target": feishu_result.canonical_type,
        }
    elif bot_lint_action == "blocked_by_errors":
        bot_result = {
            "attempted": False,
            "sent": False,
            "skipped": True,
            "reason": "report_lint_errors",
            "card_title": "",
            "doc_url_present": bool(feishu_result.canonical_url),
            "link_target": feishu_result.canonical_type,
        }
    else:
        bot_result = maybe_send_bot_card(settings, brief, dry_run=args.dry_run, skip_llm=False, send_bot=should_send_bot)

    history_summary = _write_event_history_after_success(
        settings,
        window,
        brief,
        feishu_result.canonical_url,
        dry_run=args.dry_run,
        skip_llm=args.skip_llm,
        match_audit=history_match_audit,
        final_top_dedupe_audit=final_top_dedupe_audit,
    )

    _write_github_summary(
        window=window,
        audit=audit,
        output_mode=settings.output_mode,
        report_path=report_path,
        brief_path=brief_path,
        feishu_result=feishu_result,
        bot_result=bot_result,
        print_feishu_url=getattr(settings, "print_feishu_url_in_summary", True),
        report_lint=report_lint,
        report_lint_policy=lint_policy,
        bot_lint_action=bot_lint_action,
        evidence_gate_audit=gate_result.audit,
        event_history_summary=history_summary,
    )


def _run_gate(settings: Settings, window: TimeWindow, raw_evidence: list[EvidenceItem]) -> EvidenceGateResult:
    if not getattr(settings, "evidence_gate_enabled", True):
        audit = EvidenceGateAudit(
            date=window.date_str,
            raw_evidence_count=len(raw_evidence),
            filtered_evidence_count=len(raw_evidence),
            event_history_enabled=getattr(settings, "event_history_enabled", True),
        )
        return EvidenceGateResult(filtered=raw_evidence, dropped=[], audit=audit)
    return run_evidence_gate(
        raw_evidence,
        window,
        source_quality_path=getattr(settings, "source_quality_path", Path("config/source_quality.yaml")),
        event_history_path=getattr(settings, "event_history_path", Path("state/event_history.jsonl")),
        event_history_enabled=False,
        event_history_lookback_days=getattr(settings, "event_history_lookback_days", 5),
        primary_source_enrichment_enabled=getattr(settings, "primary_source_enrichment_enabled", True),
        primary_source_max_queries=getattr(settings, "primary_source_max_queries", 8),
        primary_source_max_results_per_query=getattr(settings, "primary_source_max_results_per_query", 3),
        primary_source_search=_primary_source_search(settings),
        max_items=getattr(settings, "max_evidence_items", 80),
    )


def _run_event_history_matching(
    settings: Settings,
    window: TimeWindow,
    evidence: list[EvidenceItem],
) -> tuple[list[Any], EventHistoryMatchAudit]:
    lookback_days = int(getattr(settings, "event_history_lookback_days", 5))
    if not getattr(settings, "event_history_enabled", False):
        return [], EventHistoryMatchAudit(date=window.date_str, lookback_days=lookback_days)
    path = getattr(settings, "event_history_path", Path("state/event_history.jsonl"))
    try:
        history_events = load_recent_event_history(path, window.target_date, lookback_days)
    except Exception as exc:  # noqa: BLE001
        logger.warning("event history load failed: %s", str(exc)[:200])
        audit = EventHistoryMatchAudit(date=window.date_str, lookback_days=lookback_days)
        audit.warnings.append(f"load_failed: {str(exc)[:160]}")
        return [], audit
    audit = mark_history_matches(evidence, history_events, target_date=window.date_str, lookback_days=lookback_days)
    return history_events, audit


def _apply_event_history_filter_mode(
    settings: Settings,
    evidence: list[EvidenceItem],
    audit: EventHistoryMatchAudit,
) -> list[EvidenceItem]:
    mode = str(getattr(settings, "event_history_filter_mode", "mark") or "mark").lower()
    audit.filter_mode = mode
    audit.pre_llm_dropped_count = 0
    if mode != "drop":
        return evidence
    kept: list[EvidenceItem] = []
    for item in evidence:
        if item.date_status == "old_repeated" and item.not_core_eligible:
            audit.pre_llm_dropped_count += 1
            continue
        kept.append(item)
    return kept


def _event_history_summary(
    settings: Settings,
    match_audit: EventHistoryMatchAudit | None,
    *,
    write_succeeded: bool = False,
    write_error: str = "",
    final_top_dedupe_audit: FinalTopDedupeAudit | None = None,
) -> dict[str, object]:
    lookback_days = int(getattr(settings, "event_history_lookback_days", 5))
    path = getattr(settings, "event_history_path", Path("state/event_history.jsonl"))
    summary: dict[str, object] = {
        "event_history_enabled": bool(getattr(settings, "event_history_enabled", False)),
        "event_history_write_enabled": bool(getattr(settings, "event_history_write_enabled", False)),
        "event_history_path": str(path),
        "event_history_lookback_days": lookback_days,
        "event_history_filter_mode": str(getattr(settings, "event_history_filter_mode", "mark")),
        "event_history_events_loaded": 0,
        "event_history_matches_count": 0,
        "event_history_old_repeated_count": 0,
        "event_history_new_signal_count": 0,
        "event_history_dropped_from_core_count": 0,
        "event_history_observe_only_count": 0,
        "event_history_pre_llm_dropped_count": 0,
        "event_history_write_succeeded": write_succeeded,
        "event_history_write_error": write_error,
        "final_top_dedupe_matches_count": 0,
        "final_top_dedupe_dropped_count": 0,
        "final_top_dedupe_new_signal_count": 0,
        "final_top_p2_capped_count": 0,
        "final_top_p2_capped_titles_sample": "",
        "final_top_llm_audit_attempted": "false",
        "final_top_llm_audit_succeeded": "false",
        "final_top_llm_audit_failed": "false",
        "final_top_llm_audit_decisions_count": 0,
        "final_top_llm_audit_dropped_count": 0,
        "final_top_llm_audit_rejected_count": 0,
        "final_top_llm_audit_error": "",
        "final_top_llm_audit_dropped_titles_sample": "",
        "final_top_dedupe_cleared_core_judgments_count": 0,
        "final_top_dedupe_cleared_watch_signals_count": 0,
        "final_top_dedupe_dropped_titles_sample": "",
    }
    if match_audit:
        summary.update(match_audit.to_summary_dict())
    if final_top_dedupe_audit:
        summary.update(final_top_dedupe_audit.to_summary_dict())
    return summary


def _write_event_history_after_success(
    settings: Settings,
    window: TimeWindow,
    brief: dict[str, object],
    doc_url: str,
    *,
    dry_run: bool,
    skip_llm: bool,
    match_audit: EventHistoryMatchAudit,
    final_top_dedupe_audit: FinalTopDedupeAudit | None = None,
) -> dict[str, object]:
    if not getattr(settings, "event_history_enabled", False):
        return _event_history_summary(settings, match_audit, write_error="disabled", final_top_dedupe_audit=final_top_dedupe_audit)
    if not getattr(settings, "event_history_write_enabled", False):
        return _event_history_summary(settings, match_audit, write_error="write_disabled", final_top_dedupe_audit=final_top_dedupe_audit)
    if dry_run:
        return _event_history_summary(settings, match_audit, write_error="dry_run", final_top_dedupe_audit=final_top_dedupe_audit)
    if skip_llm:
        return _event_history_summary(settings, match_audit, write_error="skip_llm", final_top_dedupe_audit=final_top_dedupe_audit)
    if not doc_url:
        return _event_history_summary(settings, match_audit, write_error="missing_doc_url", final_top_dedupe_audit=final_top_dedupe_audit)
    try:
        append_event_history(getattr(settings, "event_history_path", Path("state/event_history.jsonl")), window.target_date, brief, doc_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("event history write failed: %s", str(exc)[:200])
        return _event_history_summary(settings, match_audit, write_error=str(exc)[:200], final_top_dedupe_audit=final_top_dedupe_audit)
    return _event_history_summary(settings, match_audit, write_succeeded=True, write_error="", final_top_dedupe_audit=final_top_dedupe_audit)


def _primary_source_search(settings: Settings):
    if not getattr(settings, "primary_source_enrichment_enabled", True) or not getattr(settings, "bocha_api_key", ""):
        return None
    fetcher = BochaFetcher(
        settings.bocha_api_key,
        base_url=getattr(settings, "bocha_base_url", "https://api.bochaai.com"),
        max_results=getattr(settings, "primary_source_max_results_per_query", 3),
        connect_timeout=getattr(settings, "bocha_connect_timeout", 5.0),
        read_timeout=getattr(settings, "bocha_read_timeout", 15.0),
        max_queries=getattr(settings, "primary_source_max_queries", 8),
    )

    def search(query: str, window: TimeWindow, max_results: int) -> list[EvidenceItem]:
        fetcher.max_results = min(max_results, getattr(settings, "primary_source_max_results_per_query", 3))
        return fetcher.search_queries([query], window, region_hint="global", source_basket="primary_source_enrichment")

    return search


def _handle_feishu_output(
    settings: Settings,
    report_path: Path,
    window: TimeWindow,
    dry_run: bool,
    *,
    force_republish: bool = False,
) -> FeishuResult:
    if dry_run:
        return _empty_feishu_result(settings.output_mode, skipped=True, reason="dry_run")
    if settings.output_mode in {"none", "local"}:
        return _empty_feishu_result(settings.output_mode, skipped=True, reason="output_mode=none")
    publish_path = _publish_result_path(report_path)
    if publish_path.exists() and not force_republish:
        return _feishu_result_from_publish_result(publish_path)
    result = publish_report(settings.output_mode, report_path, settings, window)
    _write_publish_result(publish_path, window, result)
    return result


def publish_report(output_mode: str, report_path: Path, settings: Settings, window: TimeWindow) -> FeishuResult:
    if output_mode == "feishu_drive_md":
        return _upload_drive_md(settings, report_path, output_mode=output_mode)
    if output_mode == "feishu_docx_import":
        settings.validate_for_feishu()
        title = f"AI Radar {window.date_str}"
        try:
            result = ensure_feishu_result(FeishuDocxImporter(settings).import_markdown(report_path, title=title), output_mode)
            print("Feishu docx import result:")
            print(json.dumps(result.safe_summary(), ensure_ascii=False, indent=2))
            if result.docx_import_succeeded and not result.docx_url:
                result.fallback_reason = "docx import succeeded but docx_url could not be resolved"
                logger.warning(result.fallback_reason)
                return _fallback_to_drive_md(settings, report_path, result)
            if settings.feishu_keep_md_archive:
                archive = ensure_feishu_result(
                    _upload_drive_md(settings, report_path, output_mode="feishu_drive_md"), "feishu_drive_md"
                )
                result.md_url = archive.md_url
                result.md_token = archive.md_token
                result.md_archive_used = True
                result.finalize()
            return result
        except FeishuDocxImportError as exc:
            logger.warning("Feishu docx import failed; falling back to feishu_drive_md: %s", exc)
            result = exc.result
            result.fallback_reason = result.docx_error_summary or str(exc)[:300]
            return _fallback_to_drive_md(settings, report_path, result)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Feishu docx import failed; falling back to feishu_drive_md: %s", exc)
            result = FeishuResult(
                output_mode="feishu_docx_import",
                docx_attempted=True,
                docx_error_summary=str(exc)[:300],
                fallback_reason=str(exc)[:300],
            )
            return _fallback_to_drive_md(settings, report_path, result)
    raise RuntimeError(f"Unsupported OUTPUT_MODE: {output_mode}")


def _fallback_to_drive_md(settings: Settings, report_path: Path, docx_result: FeishuResult) -> FeishuResult:
    fallback = ensure_feishu_result(
        _upload_drive_md(settings, report_path, output_mode="feishu_docx_import"), "feishu_docx_import"
    )
    docx_result.md_url = fallback.md_url
    docx_result.md_token = fallback.md_token
    docx_result.fallback_used = True
    if not docx_result.fallback_reason:
        docx_result.fallback_reason = docx_result.docx_error_summary or "docx import failed"
    return docx_result.finalize()


def _upload_drive_md(settings: Settings, report_path: Path, *, output_mode: str = "feishu_drive_md") -> FeishuResult:
    settings.validate_for_feishu()
    uploaded = FeishuClient(settings).upload_file(report_path)
    result = FeishuResult(
        output_mode=output_mode,
        md_url=_extract_url(uploaded),
        md_token=_extract_token(uploaded),
        fallback_used=False,
    ).finalize()
    print("Feishu upload result:")
    print(json.dumps(result.safe_summary(), ensure_ascii=False, indent=2))
    return result


def _extract_url(data: dict[str, Any]) -> str:
    return str(data.get("url") or data.get("file_url") or data.get("doc_url") or "")


def _extract_token(data: dict[str, Any]) -> str:
    return str(data.get("file_token") or data.get("token") or "")


def _empty_feishu_result(output_mode: str, *, skipped: bool, reason: str) -> FeishuResult:
    return FeishuResult(output_mode=output_mode, skipped=skipped, reason=reason).finalize()


def _bot_lint_action(
    report_lint: ReportLintResult,
    policy: str,
    *,
    bot_block_on_lint_critical: bool = False,
) -> str:
    if policy == "off":
        return "off"
    if report_lint.critical_errors:
        if policy == "warn" and not bot_block_on_lint_critical:
            return "ignored_critical_by_policy_warn"
        return "blocked_by_critical_errors"
    if policy == "block_bot" and report_lint.errors:
        return "blocked_by_errors"
    if policy == "strict" and report_lint.errors:
        return "blocked_by_errors"
    if policy == "warn" and report_lint.errors:
        return "ignored_by_policy_warn"
    return "passed"


def _merge_raw_generated_critical_lint(
    report_lint: ReportLintResult,
    raw_report: str,
    evidence: list[EvidenceItem],
    *,
    strict: bool,
    target_date: str,
) -> ReportLintResult:
    raw_lint = lint_report(raw_report, evidence, strict=False, target_date=target_date)
    existing = set(report_lint.critical_errors)
    critical_prefixes = (
        "placeholder found:",
        "report appears to be an LLM failure message",
    )
    for error in raw_lint.critical_errors:
        if not error.startswith(critical_prefixes):
            continue
        if error not in existing:
            report_lint.critical_errors.append(error)
            existing.add(error)
    return report_lint.finalize(strict=strict)


def _publish_result_path(report_path: Path) -> Path:
    return report_path.parent / "publish_result.json"


def _write_publish_result(path: Path, window: TimeWindow, result: FeishuResult) -> None:
    result.finalize()
    save_json(
        path,
        {
            "date": window.date_str,
            "output_mode": result.output_mode,
            "canonical_type": result.canonical_type,
            "canonical_url": result.canonical_url,
            "docx_url": result.docx_url,
            "md_url": result.md_url,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "github_run_id": os.getenv("GITHUB_RUN_ID", ""),
            "fallback_used": result.fallback_used,
        },
    )


def _feishu_result_from_publish_result(path: Path) -> FeishuResult:
    data = json.loads(path.read_text(encoding="utf-8"))
    return FeishuResult(
        output_mode=str(data.get("output_mode") or ""),
        docx_url=str(data.get("docx_url") or ""),
        md_url=str(data.get("md_url") or ""),
        canonical_url=str(data.get("canonical_url") or ""),
        canonical_type=str(data.get("canonical_type") or "none"),
        fallback_used=bool(data.get("fallback_used", False)),
        skipped=True,
        reason="reused_publish_result",
        reused_publish_result=True,
    ).finalize()


def _write_github_summary(
    *,
    window: TimeWindow,
    audit: RecallAudit,
    output_mode: str,
    report_path: Path | None,
    brief_path: Path | None,
    feishu_result: FeishuResult | dict[str, object],
    bot_result: BotResult | dict[str, Any],
    print_feishu_url: bool = True,
    report_lint: ReportLintResult | None = None,
    report_lint_policy: str = "warn",
    bot_lint_action: str = "passed",
    evidence_gate_audit: EvidenceGateAudit | None = None,
    event_history_summary: dict[str, object] | None = None,
) -> None:
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    result = ensure_feishu_result(feishu_result, output_mode)
    bot = ensure_bot_result(bot_result)
    bot_link_target = _bot_link_target(bot, result)
    brief_summary = _brief_summary(brief_path)
    gate_summary = _gate_summary(evidence_gate_audit)
    history_summary = _history_summary(event_history_summary)
    top_event_summary = _top_event_summary(brief_path)
    lines = [
        "## Daily AI Radar",
        "",
        f"- app_version: {__app_version__}",
        f"- github_sha: {os.getenv('GITHUB_SHA', '')}",
        f"- github_ref: {os.getenv('GITHUB_REF', '')}",
        f"- github_event_name: {os.getenv('GITHUB_EVENT_NAME', '')}",
        f"- target date: {window.date_str}",
        f"- output_mode: {output_mode}",
        f"- evidence count: {audit.total_evidence_count}",
        f"- RSS count: {audit.rss_item_count}",
        f"- RSS failed source count: {sum(1 for source in audit.rss_sources or [] if source.status in {'failed', 'timeout'})}",
        f"- Bocha count: {audit.bocha_item_count}",
        f"- Bocha status: {audit.bocha_status}",
        f"- Bocha error summary: {audit.bocha_error_summary[:300]}",
        f"- Tavily count: {audit.tavily_item_count}",
        f"- Tavily status: {audit.tavily_status}",
        f"- Tavily error summary: {audit.tavily_error_summary[:300]}",
        f"- RSS fallback used: {audit.rss_fallback_used}",
        f"- search providers used: {audit.search_providers_used}",
        f"- search_query_budget: {audit.search_query_budget}",
        f"- search_queries_used: {audit.search_queries_used}",
        f"- provider_queries_used: {audit.provider_queries_used or {}}",
        f"- provider_results_count: {audit.provider_results_count or {}}",
        f"- raw_evidence_count: {gate_summary['raw_evidence_count']}",
        f"- filtered_evidence_count: {gate_summary['filtered_evidence_count']}",
        f"- evidence_gate_dropped_count: {gate_summary['dropped_count']}",
        f"- dropped_old_repeated_count: {gate_summary['dropped_old_repeated_count']}",
        f"- dropped_out_of_window_count: {gate_summary['dropped_out_of_window_count']}",
        f"- dropped_low_source_fit_count: {gate_summary['dropped_low_source_fit_count']}",
        f"- primary_sources_count: {gate_summary['primary_sources_count']}",
        f"- official_sources_count: {gate_summary['official_sources_count']}",
        f"- authoritative_media_count: {gate_summary['authoritative_media_count']}",
        f"- aggregator_sources_count: {gate_summary['aggregator_sources_count']}",
        f"- primary_source_enrichment_attempted: {gate_summary['primary_source_enrichment_attempted']}",
        f"- primary_source_enrichment_added_count: {gate_summary['primary_source_enrichment_added_count']}",
        f"- evidence_gate_relaxed: {gate_summary['evidence_gate_relaxed']}",
        f"- event_history_enabled: {history_summary['event_history_enabled']}",
        f"- event_history_write_enabled: {history_summary['event_history_write_enabled']}",
        f"- event_history_path: {history_summary['event_history_path']}",
        f"- event_history_lookback_days: {history_summary['event_history_lookback_days']}",
        f"- event_history_filter_mode: {history_summary['event_history_filter_mode']}",
        f"- event_history_events_loaded: {history_summary['event_history_events_loaded']}",
        f"- event_history_matches_count: {history_summary['event_history_matches_count']}",
        f"- event_history_old_repeated_count: {history_summary['event_history_old_repeated_count']}",
        f"- event_history_new_signal_count: {history_summary['event_history_new_signal_count']}",
        f"- event_history_dropped_from_core_count: {history_summary['event_history_dropped_from_core_count']}",
        f"- event_history_observe_only_count: {history_summary['event_history_observe_only_count']}",
        f"- event_history_pre_llm_dropped_count: {history_summary['event_history_pre_llm_dropped_count']}",
        f"- event_history_write_succeeded: {history_summary['event_history_write_succeeded']}",
        f"- event_history_write_error: {history_summary['event_history_write_error']}",
        f"- final_top_dedupe_matches_count: {history_summary['final_top_dedupe_matches_count']}",
        f"- final_top_dedupe_dropped_count: {history_summary['final_top_dedupe_dropped_count']}",
        f"- final_top_dedupe_new_signal_count: {history_summary['final_top_dedupe_new_signal_count']}",
        f"- final_top_p2_capped_count: {history_summary['final_top_p2_capped_count']}",
        f"- final_top_p2_capped_titles_sample: {history_summary['final_top_p2_capped_titles_sample']}",
        f"- final_top_llm_audit_attempted: {history_summary['final_top_llm_audit_attempted']}",
        f"- final_top_llm_audit_succeeded: {history_summary['final_top_llm_audit_succeeded']}",
        f"- final_top_llm_audit_failed: {history_summary['final_top_llm_audit_failed']}",
        f"- final_top_llm_audit_decisions_count: {history_summary['final_top_llm_audit_decisions_count']}",
        f"- final_top_llm_audit_dropped_count: {history_summary['final_top_llm_audit_dropped_count']}",
        f"- final_top_llm_audit_rejected_count: {history_summary['final_top_llm_audit_rejected_count']}",
        f"- final_top_llm_audit_error: {history_summary['final_top_llm_audit_error']}",
        f"- final_top_llm_audit_dropped_titles_sample: {history_summary['final_top_llm_audit_dropped_titles_sample']}",
        f"- final_top_dedupe_cleared_core_judgments_count: {history_summary['final_top_dedupe_cleared_core_judgments_count']}",
        f"- final_top_dedupe_cleared_watch_signals_count: {history_summary['final_top_dedupe_cleared_watch_signals_count']}",
        f"- final_top_dedupe_dropped_titles_sample: {history_summary['final_top_dedupe_dropped_titles_sample']}",
        f"- top_events_count: {top_event_summary['top_events_count']}",
        f"- top_events_with_primary_source_count: {top_event_summary['top_events_with_primary_source_count']}",
        f"- top_events_with_s1_source_count: {top_event_summary['top_events_with_s1_source_count']}",
        f"- top_events_with_s1_or_s2_source_count: {top_event_summary['top_events_with_s1_or_s2_source_count']}",
        f"- top_events_with_low_source_count: {top_event_summary['top_events_with_low_source_count']}",
        f"- top_events_out_of_window_count: {top_event_summary['top_events_out_of_window_count']}",
        f"- top_events_old_repeated_count: {top_event_summary['top_events_old_repeated_count']}",
        f"- top_events_new_signal_count: {top_event_summary['top_events_new_signal_count']}",
        f"- top_event_audit_warnings_count: {top_event_summary['top_event_audit_warnings_count']}",
        f"- report path: {report_path or ''}",
        f"- brief path: {brief_path or ''}",
        f"- brief_generation_status: {brief_summary['brief_generation_status']}",
        f"- brief_error_summary: {brief_summary['brief_error_summary']}",
        f"- brief_repair_attempted: {brief_summary['brief_repair_attempted']}",
        f"- brief_repair_succeeded: {brief_summary['brief_repair_succeeded']}",
        f"- brief_parse_stage: {brief_summary['brief_parse_stage']}",
        f"- brief_raw_response_length: {brief_summary['brief_raw_response_length']}",
        f"- brief_raw_response_summary: {brief_summary['brief_raw_response_summary']}",
        f"- brief_json_parse_error: {brief_summary['brief_json_parse_error']}",
        f"- brief_normalization_error: {brief_summary['brief_normalization_error']}",
        f"- brief_source_resolution_status: {brief_summary['brief_source_resolution_status']}",
        f"- brief_invalid_source_ids_count: {brief_summary['brief_invalid_source_ids_count']}",
        f"- brief_items_count: {brief_summary['brief_items_count']}",
        f"- report_domestic_core_events_count: {brief_summary['report_domestic_core_events_count']}",
        f"- report_overseas_core_events_count: {brief_summary['report_overseas_core_events_count']}",
        f"- report_domestic_core_events_count_raw: {brief_summary['report_domestic_core_events_count_raw']}",
        f"- report_overseas_core_events_count_raw: {brief_summary['report_overseas_core_events_count_raw']}",
        f"- report_domestic_core_events_count_capped: {brief_summary['report_domestic_core_events_count_capped']}",
        f"- report_overseas_core_events_count_capped: {brief_summary['report_overseas_core_events_count_capped']}",
        f"- domestic_core_events_truncated: {brief_summary['domestic_core_events_truncated']}",
        f"- overseas_core_events_truncated: {brief_summary['overseas_core_events_truncated']}",
        f"- domestic_core_events_truncated_from: {brief_summary['domestic_core_events_truncated_from']}",
        f"- overseas_core_events_truncated_from: {brief_summary['overseas_core_events_truncated_from']}",
        f"- report_domestic_zero_core_explicit: {brief_summary['report_domestic_zero_core_explicit']}",
        f"- report_overseas_zero_core_explicit: {brief_summary['report_overseas_zero_core_explicit']}",
        f"- report_domestic_zero_core_conflict_resolved: {brief_summary['report_domestic_zero_core_conflict_resolved']}",
        f"- report_overseas_zero_core_conflict_resolved: {brief_summary['report_overseas_zero_core_conflict_resolved']}",
        f"- report_domestic_extraction_suspect: {brief_summary['report_domestic_extraction_suspect']}",
        f"- report_overseas_extraction_suspect: {brief_summary['report_overseas_extraction_suspect']}",
        f"- report_domestic_section_found: {brief_summary['report_domestic_section_found']}",
        f"- report_overseas_section_found: {brief_summary['report_overseas_section_found']}",
        f"- report_domestic_extraction_method: {brief_summary['report_domestic_extraction_method']}",
        f"- report_overseas_extraction_method: {brief_summary['report_overseas_extraction_method']}",
        f"- report_domestic_extracted_titles_sample: {brief_summary['report_domestic_extracted_titles_sample']}",
        f"- report_overseas_extracted_titles_sample: {brief_summary['report_overseas_extracted_titles_sample']}",
        f"- report_domestic_empty_reason: {brief_summary['report_domestic_empty_reason']}",
        f"- report_overseas_empty_reason: {brief_summary['report_overseas_empty_reason']}",
        f"- core event extraction warning: {brief_summary['core_event_extraction_warning']}",
        f"- brief_domestic_items_count: {brief_summary['brief_domestic_items_count']}",
        f"- brief_overseas_items_count: {brief_summary['brief_overseas_items_count']}",
        f"- brief_domestic_items_count_raw: {brief_summary['brief_domestic_items_count_raw']}",
        f"- brief_overseas_items_count_raw: {brief_summary['brief_overseas_items_count_raw']}",
        f"- brief_domestic_items_count_capped: {brief_summary['brief_domestic_items_count_capped']}",
        f"- brief_overseas_items_count_capped: {brief_summary['brief_overseas_items_count_capped']}",
        f"- brief_domestic_truncated: {brief_summary['brief_domestic_truncated']}",
        f"- brief_overseas_truncated: {brief_summary['brief_overseas_truncated']}",
        f"- brief_llm_domestic_items_count: {brief_summary['brief_llm_domestic_items_count']}",
        f"- brief_llm_overseas_items_count: {brief_summary['brief_llm_overseas_items_count']}",
        f"- brief_final_domestic_items_count: {brief_summary['brief_final_domestic_items_count']}",
        f"- brief_final_overseas_items_count: {brief_summary['brief_final_overseas_items_count']}",
        f"- brief_sources_count: {brief_summary['brief_sources_count']}",
        f"- brief_items_without_sources_count: {brief_summary['brief_items_without_sources_count']}",
        f"- brief_source_ids_requested_count: {brief_summary['brief_source_ids_requested_count']}",
        f"- brief_source_ids_resolved_count: {brief_summary['brief_source_ids_resolved_count']}",
        f"- brief_source_ids_unresolved_count: {brief_summary['brief_source_ids_unresolved_count']}",
        f"- brief_unresolved_source_ids_sample: {brief_summary['brief_unresolved_source_ids_sample']}",
        f"- brief_sources_filled_by_matching_count: {brief_summary['brief_sources_filled_by_matching_count']}",
        f"- brief_empty_placeholder_removed_count: {brief_summary['brief_empty_placeholder_removed_count']}",
        f"- brief_count_mismatch: {brief_summary['brief_count_mismatch']}",
        f"- brief_count_mismatch_type: {brief_summary['brief_count_mismatch_type']}",
        f"- brief_count_mismatch_handled: {brief_summary['brief_count_mismatch_handled']}",
        f"- brief_count_repair_attempted: {brief_summary['brief_count_repair_attempted']}",
        f"- brief_count_repair_succeeded: {brief_summary['brief_count_repair_succeeded']}",
        f"- brief_source_validation_warnings_count: {brief_summary['brief_source_validation_warnings_count']}",
        f"- report_lint_policy: {report_lint_policy}",
        f"- report_lint_passed: {_bool(report_lint.passed if report_lint else True)}",
        f"- report_lint warnings count: {len(report_lint.warnings) if report_lint else 0}",
        f"- report_lint errors count: {len(report_lint.errors) if report_lint else 0}",
        f"- report_lint critical_errors count: {len(report_lint.critical_errors) if report_lint else 0}",
        f"- report_lint critical_errors summary: {_critical_errors_summary(report_lint)}",
        f"- reused_publish_result: {_bool(result.reused_publish_result)}",
        f"- docx_attempted: {_bool(result.docx_attempted)}",
        f"- docx_import_started: {_bool(result.docx_import_started)}",
        f"- docx_import_succeeded: {_bool(result.docx_import_succeeded)}",
        f"- docx_last_job_status: {result.docx_last_job_status}",
        f"- docx_poll_attempts: {result.docx_poll_attempts}",
        f"- docx_poll_duration_seconds: {result.docx_poll_duration_seconds}",
        f"- docx_url exists: {_bool(result.docx_url)}",
        f"- docx_error_summary: {result.docx_error_summary[:300]}",
        f"- fallback_used: {_bool(result.fallback_used)}",
        f"- fallback_reason: {result.fallback_reason[:300]}",
        f"- md_url exists: {_bool(result.md_url)}",
        f"- md_archive_used: {_bool(result.md_archive_used)}",
        f"- canonical_type: {result.canonical_type}",
        f"- canonical_url exists: {_bool(result.canonical_url)}",
        f"- feishu url: {result.canonical_url if print_feishu_url else ''}",
        f"- temp_file_token exists: {_bool(result.temp_file_token)}",
        f"- temp_file_deleted: {_bool(result.temp_file_deleted)}",
        f"- temp_file_delete_error: {result.temp_file_delete_error[:300]}",
        f"- bot attempted: {_bool(bot.attempted)}",
        f"- bot sent: {_bool(bot.sent)}",
        f"- bot lint action: {bot_lint_action}",
        f"- bot skipped: {_bool(bot.skipped)}",
        f"- bot skipped/reason: {bot.reason}",
        f"- bot status_code: {bot.status_code if bot.status_code is not None else ''}",
        f"- bot response_code: {bot.response_code if bot.response_code is not None else ''}",
        f"- bot response_msg: {bot.response_msg}",
        f"- bot error_summary: {bot.error_summary}",
        f"- bot response_body_summary: {bot.response_body_summary}",
        f"- bot link target: {bot_link_target}",
        f"- bot card title: {bot.card_title}",
        f"- bot_domestic_items_input_count: {bot.domestic_items_input_count}",
        f"- bot_overseas_items_input_count: {bot.overseas_items_input_count}",
        f"- bot_domestic_items_rendered_count: {bot.domestic_items_rendered_count}",
        f"- bot_overseas_items_rendered_count: {bot.overseas_items_rendered_count}",
        f"- bot_domestic_items_truncated: {_bool(bot.domestic_items_truncated)}",
        f"- bot_overseas_items_truncated: {_bool(bot.overseas_items_truncated)}",
        f"- bot_card_items_truncated: {_bool(bot.card_items_truncated)}",
        f"- bot_card_truncated_reason: {bot.card_truncated_reason}",
        f"- bot_title_truncation_count: {bot.title_truncation_count}",
        f"- bot_title_truncation_examples: {', '.join(bot.title_truncation_examples or [])}",
        f"- bot doc_url present: {_bool(bot.doc_url_present or result.canonical_url)}",
        f"- bot text fallback attempted: {_bool(bot.text_fallback_attempted)}",
        f"- bot text fallback sent: {_bool(bot.text_fallback_sent)}",
        f"- bot text fallback reason: {bot.text_fallback_reason}",
        f"- bot text fallback status_code: {bot.text_fallback_status_code if bot.text_fallback_status_code is not None else ''}",
        f"- bot text fallback response_code: {bot.text_fallback_response_code if bot.text_fallback_response_code is not None else ''}",
        f"- bot text fallback response_msg: {bot.text_fallback_response_msg}",
        f"- bot text fallback error_summary: {bot.text_fallback_error_summary}",
        f"- bot text fallback body_summary: {bot.text_fallback_body_summary}",
        "",
    ]
    with Path(summary_path).open("a", encoding="utf-8") as f:
        f.write("\n".join(lines))


def _bool(value: object) -> str:
    return str(bool(value)).lower()


def _bot_link_target(bot: BotResult, result: FeishuResult) -> str:
    if bot.link_target and bot.link_target != "none":
        return bot.link_target
    if result.canonical_type and result.canonical_type != "none":
        return result.canonical_type
    return "none"


def _critical_errors_summary(report_lint: ReportLintResult | None) -> str:
    if not report_lint or not report_lint.critical_errors:
        return ""
    return " | ".join(_redact_summary_item(item)[:300] for item in report_lint.critical_errors[:3])


def _gate_summary(gate_audit: EvidenceGateAudit | None) -> dict[str, object]:
    defaults: dict[str, object] = {
        "raw_evidence_count": 0,
        "filtered_evidence_count": 0,
        "dropped_count": 0,
        "dropped_old_repeated_count": 0,
        "dropped_out_of_window_count": 0,
        "dropped_low_source_fit_count": 0,
        "primary_sources_count": 0,
        "official_sources_count": 0,
        "authoritative_media_count": 0,
        "aggregator_sources_count": 0,
        "primary_source_enrichment_attempted": "false",
        "primary_source_enrichment_added_count": 0,
        "evidence_gate_relaxed": "false",
        "event_history_enabled": "false",
        "event_history_repeated_count": 0,
    }
    if not gate_audit:
        return defaults
    data = gate_audit.to_dict()
    for key in list(defaults):
        value = data.get(key, defaults[key])
        defaults[key] = _bool(value) if isinstance(value, bool) else value
    return defaults


def _history_summary(summary: dict[str, object] | None) -> dict[str, object]:
    defaults: dict[str, object] = {
        "event_history_enabled": "false",
        "event_history_write_enabled": "false",
        "event_history_path": "state/event_history.jsonl",
        "event_history_lookback_days": 5,
        "event_history_filter_mode": "mark",
        "event_history_events_loaded": 0,
        "event_history_matches_count": 0,
        "event_history_old_repeated_count": 0,
        "event_history_new_signal_count": 0,
        "event_history_dropped_from_core_count": 0,
        "event_history_observe_only_count": 0,
        "event_history_pre_llm_dropped_count": 0,
        "event_history_write_succeeded": "false",
        "event_history_write_error": "",
        "final_top_dedupe_matches_count": 0,
        "final_top_dedupe_dropped_count": 0,
        "final_top_dedupe_new_signal_count": 0,
        "final_top_p2_capped_count": 0,
        "final_top_p2_capped_titles_sample": "",
        "final_top_llm_audit_attempted": "false",
        "final_top_llm_audit_succeeded": "false",
        "final_top_llm_audit_failed": "false",
        "final_top_llm_audit_decisions_count": 0,
        "final_top_llm_audit_dropped_count": 0,
        "final_top_llm_audit_rejected_count": 0,
        "final_top_llm_audit_error": "",
        "final_top_llm_audit_dropped_titles_sample": "",
        "final_top_dedupe_cleared_core_judgments_count": 0,
        "final_top_dedupe_cleared_watch_signals_count": 0,
        "final_top_dedupe_dropped_titles_sample": "",
    }
    if not summary:
        return defaults
    for key in list(defaults):
        value = summary.get(key, defaults[key])
        defaults[key] = _bool(value) if isinstance(value, bool) else value
    return defaults


def _top_event_summary(brief_path: Path | None) -> dict[str, int]:
    defaults = {
        "top_events_count": 0,
        "top_events_with_primary_source_count": 0,
        "top_events_with_s1_source_count": 0,
        "top_events_with_s1_or_s2_source_count": 0,
        "top_events_with_low_source_count": 0,
        "top_events_out_of_window_count": 0,
        "top_events_old_repeated_count": 0,
        "top_events_new_signal_count": 0,
        "top_event_audit_warnings_count": 0,
    }
    if not brief_path:
        return defaults
    path = brief_path.parent / "top_event_audit.json"
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return defaults
    for key in list(defaults):
        defaults[key] = int(data.get(key) or 0)
    return defaults


def _redact_summary_item(value: str) -> str:
    redacted = value
    redacted = re.sub(
        r'(?i)("?(?:webhook|sign|token|app_secret|secret|api[_-]?key)"?\s*[:=]\s*")([^"]+)(")',
        r'"redacted_field": "[REDACTED]"',
        redacted,
    )
    redacted = re.sub(
        r"(?i)((?:webhook|sign|token|app_secret|secret|api[_-]?key)\s*[:=]\s*)([^\s,;}&]+)",
        r"redacted_field=[REDACTED]",
        redacted,
    )
    return redacted


def _join_sample(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value[:5])
    return str(value or "")[:300]


def _brief_summary(brief_path: Path | None) -> dict[str, str | int]:
    summary: dict[str, str | int] = {
        "brief_generation_status": "",
        "brief_error_summary": "",
        "brief_repair_attempted": "false",
        "brief_repair_succeeded": "false",
        "brief_parse_stage": "",
        "brief_raw_response_length": 0,
        "brief_raw_response_summary": "",
        "brief_json_parse_error": "",
        "brief_normalization_error": "",
        "brief_source_resolution_status": "",
        "brief_invalid_source_ids_count": 0,
        "brief_items_count": 0,
        "report_domestic_core_events_count": 0,
        "report_overseas_core_events_count": 0,
        "report_domestic_core_events_count_raw": 0,
        "report_overseas_core_events_count_raw": 0,
        "report_domestic_core_events_count_capped": 0,
        "report_overseas_core_events_count_capped": 0,
        "domestic_core_events_truncated": "false",
        "overseas_core_events_truncated": "false",
        "domestic_core_events_truncated_from": 0,
        "overseas_core_events_truncated_from": 0,
        "report_domestic_zero_core_explicit": "false",
        "report_overseas_zero_core_explicit": "false",
        "report_domestic_zero_core_conflict_resolved": "",
        "report_overseas_zero_core_conflict_resolved": "",
        "report_domestic_extraction_suspect": "false",
        "report_overseas_extraction_suspect": "false",
        "report_domestic_section_found": "false",
        "report_overseas_section_found": "false",
        "report_domestic_extraction_method": "none",
        "report_overseas_extraction_method": "none",
        "report_domestic_extracted_titles_sample": "",
        "report_overseas_extracted_titles_sample": "",
        "report_domestic_empty_reason": "",
        "report_overseas_empty_reason": "",
        "core_event_extraction_warning": "",
        "brief_domestic_items_count": 0,
        "brief_overseas_items_count": 0,
        "brief_domestic_items_count_raw": 0,
        "brief_overseas_items_count_raw": 0,
        "brief_domestic_items_count_capped": 0,
        "brief_overseas_items_count_capped": 0,
        "brief_domestic_truncated": "false",
        "brief_overseas_truncated": "false",
        "brief_llm_domestic_items_count": 0,
        "brief_llm_overseas_items_count": 0,
        "brief_final_domestic_items_count": 0,
        "brief_final_overseas_items_count": 0,
        "brief_sources_count": 0,
        "brief_items_without_sources_count": 0,
        "brief_source_ids_requested_count": 0,
        "brief_source_ids_resolved_count": 0,
        "brief_source_ids_unresolved_count": 0,
        "brief_unresolved_source_ids_sample": "",
        "brief_sources_filled_by_matching_count": 0,
        "brief_empty_placeholder_removed_count": 0,
        "brief_count_mismatch": "false",
        "brief_count_mismatch_type": "none",
        "brief_count_mismatch_handled": "false",
        "brief_count_repair_attempted": "false",
        "brief_count_repair_succeeded": "false",
        "brief_source_validation_warnings_count": 0,
    }
    if not brief_path or not brief_path.exists():
        return summary
    try:
        data = json.loads(brief_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        summary["brief_generation_status"] = "invalid"
        return summary
    items = (data.get("domestic_top") or []) + (data.get("overseas_top") or [])
    source_counts = [len(item.get("sources") or []) for item in items if isinstance(item, dict)]
    summary["brief_generation_status"] = str(data.get("brief_generation_status") or "ok")
    summary["brief_error_summary"] = str(data.get("brief_error_summary") or "")[:300]
    summary["brief_repair_attempted"] = _bool(data.get("brief_repair_attempted", False))
    summary["brief_repair_succeeded"] = _bool(data.get("brief_repair_succeeded", False))
    summary["brief_parse_stage"] = str(data.get("brief_parse_stage") or "")
    summary["brief_raw_response_length"] = int(data.get("brief_raw_response_length") or 0)
    summary["brief_raw_response_summary"] = str(data.get("brief_raw_response_summary") or "")[:1000]
    summary["brief_json_parse_error"] = str(data.get("brief_json_parse_error") or "")[:300]
    summary["brief_normalization_error"] = str(data.get("brief_normalization_error") or "")[:300]
    summary["brief_source_resolution_status"] = str(data.get("brief_source_resolution_status") or "")
    summary["brief_invalid_source_ids_count"] = int(data.get("brief_invalid_source_ids_count") or 0)
    summary["brief_items_count"] = len(source_counts)
    summary["report_domestic_core_events_count"] = int(data.get("report_domestic_core_events_count") or 0)
    summary["report_overseas_core_events_count"] = int(data.get("report_overseas_core_events_count") or 0)
    summary["report_domestic_core_events_count_raw"] = int(
        data.get("report_domestic_core_events_count_raw") or summary["report_domestic_core_events_count"]
    )
    summary["report_overseas_core_events_count_raw"] = int(
        data.get("report_overseas_core_events_count_raw") or summary["report_overseas_core_events_count"]
    )
    summary["report_domestic_core_events_count_capped"] = int(
        data.get("report_domestic_core_events_count_capped") or summary["report_domestic_core_events_count"]
    )
    summary["report_overseas_core_events_count_capped"] = int(
        data.get("report_overseas_core_events_count_capped") or summary["report_overseas_core_events_count"]
    )
    summary["domestic_core_events_truncated"] = _bool(data.get("domestic_core_events_truncated", False))
    summary["overseas_core_events_truncated"] = _bool(data.get("overseas_core_events_truncated", False))
    summary["domestic_core_events_truncated_from"] = int(data.get("domestic_core_events_truncated_from") or 0)
    summary["overseas_core_events_truncated_from"] = int(data.get("overseas_core_events_truncated_from") or 0)
    summary["report_domestic_zero_core_explicit"] = _bool(data.get("report_domestic_zero_core_explicit", False))
    summary["report_overseas_zero_core_explicit"] = _bool(data.get("report_overseas_zero_core_explicit", False))
    summary["report_domestic_zero_core_conflict_resolved"] = str(data.get("report_domestic_zero_core_conflict_resolved") or "")
    summary["report_overseas_zero_core_conflict_resolved"] = str(data.get("report_overseas_zero_core_conflict_resolved") or "")
    summary["report_domestic_extraction_suspect"] = _bool(data.get("report_domestic_extraction_suspect", False))
    summary["report_overseas_extraction_suspect"] = _bool(data.get("report_overseas_extraction_suspect", False))
    summary["report_domestic_section_found"] = _bool(data.get("report_domestic_section_found", False))
    summary["report_overseas_section_found"] = _bool(data.get("report_overseas_section_found", False))
    summary["report_domestic_extraction_method"] = str(data.get("report_domestic_extraction_method") or "none")
    summary["report_overseas_extraction_method"] = str(data.get("report_overseas_extraction_method") or "none")
    summary["report_domestic_extracted_titles_sample"] = _join_sample(data.get("report_domestic_extracted_titles_sample"))
    summary["report_overseas_extracted_titles_sample"] = _join_sample(data.get("report_overseas_extracted_titles_sample"))
    summary["report_domestic_empty_reason"] = str(data.get("report_domestic_empty_reason") or "")
    summary["report_overseas_empty_reason"] = str(data.get("report_overseas_empty_reason") or "")
    warnings = []
    if data.get("report_domestic_extraction_suspect"):
        warnings.append("domestic core event extraction returned 0 without explicit no-core explanation")
    if data.get("report_overseas_extraction_suspect"):
        warnings.append("overseas core event extraction returned 0 without explicit no-core explanation")
    summary["core_event_extraction_warning"] = " | ".join(warnings)
    summary["brief_domestic_items_count"] = len([item for item in data.get("domestic_top") or [] if isinstance(item, dict)])
    summary["brief_overseas_items_count"] = len([item for item in data.get("overseas_top") or [] if isinstance(item, dict)])
    summary["brief_domestic_items_count_raw"] = int(
        data.get("brief_domestic_items_count_raw") or summary["brief_domestic_items_count"]
    )
    summary["brief_overseas_items_count_raw"] = int(
        data.get("brief_overseas_items_count_raw") or summary["brief_overseas_items_count"]
    )
    summary["brief_domestic_items_count_capped"] = int(
        data.get("brief_domestic_items_count_capped") or summary["brief_domestic_items_count"]
    )
    summary["brief_overseas_items_count_capped"] = int(
        data.get("brief_overseas_items_count_capped") or summary["brief_overseas_items_count"]
    )
    summary["brief_domestic_truncated"] = _bool(data.get("brief_domestic_truncated", False))
    summary["brief_overseas_truncated"] = _bool(data.get("brief_overseas_truncated", False))
    summary["brief_llm_domestic_items_count"] = int(data.get("brief_llm_domestic_items_count") or 0)
    summary["brief_llm_overseas_items_count"] = int(data.get("brief_llm_overseas_items_count") or 0)
    summary["brief_final_domestic_items_count"] = int(data.get("brief_final_domestic_items_count") or len(data.get("domestic_top") or []))
    summary["brief_final_overseas_items_count"] = int(data.get("brief_final_overseas_items_count") or len(data.get("overseas_top") or []))
    summary["brief_sources_count"] = sum(source_counts)
    summary["brief_items_without_sources_count"] = sum(1 for count in source_counts if count == 0)
    summary["brief_source_ids_requested_count"] = int(data.get("brief_source_ids_requested_count") or 0)
    summary["brief_source_ids_resolved_count"] = int(data.get("brief_source_ids_resolved_count") or 0)
    summary["brief_source_ids_unresolved_count"] = int(data.get("brief_source_ids_unresolved_count") or 0)
    unresolved_sample = data.get("brief_unresolved_source_ids_sample") or []
    if isinstance(unresolved_sample, list):
        summary["brief_unresolved_source_ids_sample"] = ", ".join(str(item) for item in unresolved_sample[:10])
    else:
        summary["brief_unresolved_source_ids_sample"] = str(unresolved_sample)[:300]
    summary["brief_sources_filled_by_matching_count"] = int(data.get("brief_sources_filled_by_matching_count") or 0)
    summary["brief_empty_placeholder_removed_count"] = int(data.get("brief_empty_placeholder_removed_count") or 0)
    summary["brief_count_mismatch"] = _bool(data.get("brief_count_mismatch", False))
    summary["brief_count_mismatch_type"] = str(data.get("brief_count_mismatch_type") or "none")
    summary["brief_count_mismatch_handled"] = _bool(data.get("brief_count_mismatch_handled", False))
    summary["brief_count_repair_attempted"] = _bool(data.get("brief_count_repair_attempted", False))
    summary["brief_count_repair_succeeded"] = _bool(data.get("brief_count_repair_succeeded", False))
    summary["brief_source_validation_warnings_count"] = len(data.get("brief_source_validation_warnings") or [])
    return summary


if __name__ == "__main__":
    main()
