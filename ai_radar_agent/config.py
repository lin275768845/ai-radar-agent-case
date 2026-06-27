from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    deepseek_api_key: str = Field(default="", validation_alias="DEEPSEEK_API_KEY")
    deepseek_base_url: str = Field(default="https://api.deepseek.com", validation_alias="DEEPSEEK_BASE_URL")
    deepseek_model: str = Field(default="deepseek-v4-pro", validation_alias="DEEPSEEK_MODEL")

    tavily_api_key: str = Field(default="", validation_alias="TAVILY_API_KEY")
    search_providers: str = Field(default="rss,bocha", validation_alias="SEARCH_PROVIDERS")

    bocha_api_key: str = Field(default="", validation_alias="BOCHA_API_KEY")
    bocha_enabled: bool = Field(default=False, validation_alias="BOCHA_ENABLED")
    bocha_base_url: str = Field(default="https://api.bochaai.com", validation_alias="BOCHA_BASE_URL")
    bocha_max_queries: int = Field(default=20, validation_alias="BOCHA_MAX_QUERIES")
    bocha_max_results_per_query: int = Field(default=5, validation_alias="BOCHA_MAX_RESULTS_PER_QUERY")
    bocha_connect_timeout: float = Field(default=5.0, validation_alias="BOCHA_CONNECT_TIMEOUT")
    bocha_read_timeout: float = Field(default=15.0, validation_alias="BOCHA_READ_TIMEOUT")

    tavily_enabled: bool = Field(default=False, validation_alias="TAVILY_ENABLED")
    tavily_connect_timeout: float = Field(default=5.0, validation_alias="TAVILY_CONNECT_TIMEOUT")
    tavily_read_timeout: float = Field(default=15.0, validation_alias="TAVILY_READ_TIMEOUT")
    tavily_max_queries: int = Field(default=8, validation_alias="TAVILY_MAX_QUERIES")
    tavily_max_results_per_query: int = Field(default=3, validation_alias="TAVILY_MAX_RESULTS_PER_QUERY")
    tavily_max_consecutive_connect_failures: int = Field(
        default=2, validation_alias="TAVILY_MAX_CONSECUTIVE_CONNECT_FAILURES"
    )

    feishu_app_id: str = Field(default="", validation_alias="FEISHU_APP_ID")
    feishu_app_secret: str = Field(default="", validation_alias="FEISHU_APP_SECRET")
    feishu_folder_token: str = Field(default="", validation_alias="FEISHU_FOLDER_TOKEN")
    feishu_temp_folder_token: str = Field(default="", validation_alias="FEISHU_TEMP_FOLDER_TOKEN")
    feishu_keep_md_archive: bool = Field(default=False, validation_alias="FEISHU_KEEP_MD_ARCHIVE")
    feishu_doc_base_url: str = Field(default="https://my.feishu.cn", validation_alias="FEISHU_DOC_BASE_URL")
    feishu_import_poll_timeout_seconds: int = Field(
        default=180, validation_alias="FEISHU_IMPORT_POLL_TIMEOUT_SECONDS"
    )
    feishu_import_poll_interval_seconds: float = Field(
        default=3.0, validation_alias="FEISHU_IMPORT_POLL_INTERVAL_SECONDS"
    )
    print_feishu_url_in_summary: bool = Field(default=True, validation_alias="PRINT_FEISHU_URL_IN_SUMMARY")
    feishu_bot_webhook_url: str = Field(default="", validation_alias="FEISHU_BOT_WEBHOOK_URL")
    feishu_bot_secret: str = Field(default="", validation_alias="FEISHU_BOT_SECRET")
    feishu_bot_fallback_text: bool = Field(default=True, validation_alias="FEISHU_BOT_FALLBACK_TEXT")
    brief_card_repair_max_attempts: int = Field(default=3, validation_alias="BRIEF_CARD_REPAIR_MAX_ATTEMPTS")
    brief_section_generation_enabled: bool = Field(default=True, validation_alias="BRIEF_SECTION_GENERATION_ENABLED")
    brief_section_repair_max_attempts: int = Field(default=3, validation_alias="BRIEF_SECTION_REPAIR_MAX_ATTEMPTS")

    radar_timezone: str = Field(default="Asia/Shanghai", validation_alias="RADAR_TIMEZONE")
    output_mode: Literal["local", "none", "feishu_drive_md", "feishu_docx_import"] = Field(
        default="feishu_docx_import", validation_alias="OUTPUT_MODE"
    )
    send_bot: bool = Field(default=True, validation_alias="SEND_BOT")
    max_search_queries_per_run: int = Field(default=30, validation_alias="MAX_SEARCH_QUERIES_PER_RUN")
    max_search_results_per_provider: int = Field(default=80, validation_alias="MAX_SEARCH_RESULTS_PER_PROVIDER")
    max_search_results_per_query: int = Field(default=5, validation_alias="MAX_SEARCH_RESULTS_PER_QUERY")
    max_evidence_items: int = Field(default=80, validation_alias="MAX_EVIDENCE_ITEMS")
    strict_report_lint: bool = Field(default=False, validation_alias="STRICT_REPORT_LINT")
    report_lint_policy: Literal["warn", "block_bot", "strict", "off"] = Field(
        default="block_bot", validation_alias="REPORT_LINT_POLICY"
    )
    bot_block_on_lint_critical: bool = Field(default=False, validation_alias="BOT_BLOCK_ON_LINT_CRITICAL")
    evidence_gate_enabled: bool = Field(default=True, validation_alias="EVIDENCE_GATE_ENABLED")
    event_history_enabled: bool = Field(default=True, validation_alias="EVENT_HISTORY_ENABLED")
    event_history_lookback_days: int = Field(default=5, validation_alias="EVENT_HISTORY_LOOKBACK_DAYS")
    event_history_write_enabled: bool = Field(default=True, validation_alias="EVENT_HISTORY_WRITE_ENABLED")
    event_history_commit_enabled: bool = Field(default=True, validation_alias="EVENT_HISTORY_COMMIT_ENABLED")
    event_history_filter_mode: Literal["mark", "drop"] = Field(default="mark", validation_alias="EVENT_HISTORY_FILTER_MODE")
    final_top_llm_audit_enabled: bool = Field(default=True, validation_alias="FINAL_TOP_LLM_AUDIT_ENABLED")
    final_top_llm_audit_max_history_events: int = Field(default=30, validation_alias="FINAL_TOP_LLM_AUDIT_MAX_HISTORY_EVENTS")
    final_top_llm_audit_max_tokens: int = Field(default=1200, validation_alias="FINAL_TOP_LLM_AUDIT_MAX_TOKENS")
    primary_source_enrichment_enabled: bool = Field(default=True, validation_alias="PRIMARY_SOURCE_ENRICHMENT_ENABLED")
    primary_source_max_queries: int = Field(default=8, validation_alias="PRIMARY_SOURCE_MAX_QUERIES")
    primary_source_max_results_per_query: int = Field(default=3, validation_alias="PRIMARY_SOURCE_MAX_RESULTS_PER_QUERY")

    prompt_path: Path = Path("prompts/radar_prompt.md")
    sources_path: Path = Path("config/sources.yaml")
    source_quality_path: Path = Path("config/source_quality.yaml")
    event_history_path: Path = Field(default=Path("state/event_history.jsonl"), validation_alias="EVENT_HISTORY_PATH")
    output_dir: Path = Path("outputs")

    def validate_for_generation(self) -> None:
        if not self.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is required")
        if not self.deepseek_base_url:
            raise RuntimeError("DEEPSEEK_BASE_URL is required")
        if not self.deepseek_model:
            raise RuntimeError("DEEPSEEK_MODEL is required")

    def validate_for_feishu(self) -> None:
        missing = [
            name
            for name, value in {
                "FEISHU_APP_ID": self.feishu_app_id,
                "FEISHU_APP_SECRET": self.feishu_app_secret,
                "FEISHU_FOLDER_TOKEN": self.feishu_folder_token,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing Feishu env vars: {', '.join(missing)}")
