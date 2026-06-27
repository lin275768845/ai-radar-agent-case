from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class FeishuResult:
    output_mode: str
    docx_attempted: bool = False
    docx_import_started: bool = False
    docx_import_succeeded: bool = False
    docx_url: str = ""
    docx_token: str = ""
    docx_title: str = ""
    docx_error_summary: str = ""
    docx_raw_result_summary: str = ""
    docx_last_job_status: str = ""
    docx_poll_attempts: int = 0
    docx_poll_duration_seconds: float = 0.0
    md_url: str = ""
    md_token: str = ""
    canonical_url: str = ""
    canonical_type: str = "none"
    fallback_used: bool = False
    fallback_reason: str = ""
    md_archive_used: bool = False
    temp_file_token: str = ""
    temp_file_name: str = ""
    temp_file_deleted: bool = False
    temp_file_delete_error: str = ""
    warnings: list[str] = field(default_factory=list)
    skipped: bool = False
    reason: str = ""
    reused_publish_result: bool = False

    def finalize(self) -> FeishuResult:
        if self.docx_url:
            self.canonical_url = self.docx_url
            self.canonical_type = "docx"
            self.fallback_used = False
        elif self.md_url:
            self.canonical_url = self.md_url
            self.canonical_type = "md"
        else:
            self.canonical_url = ""
            self.canonical_type = "none"
        return self

    def to_dict(self) -> dict[str, str | bool | int | float | list[str]]:
        self.finalize()
        return asdict(self)

    def safe_summary(self) -> dict[str, str | bool | int | float | list[str]]:
        self.finalize()
        return {
            "output_mode": self.output_mode,
            "docx_attempted": self.docx_attempted,
            "docx_import_started": self.docx_import_started,
            "docx_import_succeeded": self.docx_import_succeeded,
            "docx_last_job_status": self.docx_last_job_status,
            "docx_poll_attempts": self.docx_poll_attempts,
            "docx_poll_duration_seconds": self.docx_poll_duration_seconds,
            "docx_url_exists": bool(self.docx_url),
            "docx_error_summary": self.docx_error_summary,
            "md_url_exists": bool(self.md_url),
            "canonical_url_exists": bool(self.canonical_url),
            "canonical_type": self.canonical_type,
            "fallback_used": self.fallback_used,
            "fallback_reason": self.fallback_reason,
            "md_archive_used": self.md_archive_used,
            "temp_file_token_exists": bool(self.temp_file_token),
            "temp_file_deleted": self.temp_file_deleted,
            "temp_file_delete_error": self.temp_file_delete_error,
            "warnings": self.warnings,
            "skipped": self.skipped,
            "reason": self.reason,
            "reused_publish_result": self.reused_publish_result,
        }


def ensure_feishu_result(value: FeishuResult | dict[str, object], output_mode: str = "") -> FeishuResult:
    if isinstance(value, FeishuResult):
        return value.finalize()
    result = FeishuResult(output_mode=str(value.get("output_mode") or output_mode))
    for field_name in {
        "docx_url",
        "docx_attempted",
        "docx_import_started",
        "docx_import_succeeded",
        "docx_token",
        "docx_title",
        "docx_error_summary",
        "docx_raw_result_summary",
        "docx_last_job_status",
        "docx_poll_attempts",
        "docx_poll_duration_seconds",
        "md_url",
        "md_token",
        "canonical_url",
        "canonical_type",
        "fallback_used",
        "fallback_reason",
        "md_archive_used",
        "temp_file_token",
        "temp_file_name",
        "temp_file_deleted",
        "temp_file_delete_error",
        "warnings",
        "skipped",
        "reason",
        "reused_publish_result",
    }:
        if field_name in value:
            setattr(result, field_name, value[field_name])
    return result.finalize()
