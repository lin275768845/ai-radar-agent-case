#!/usr/bin/env python3
"""Validate the Week 2 AI Radar eval-case definitions.

This checker is intentionally static and local-only. It does not import
production code, call network APIs, invoke LLMs, trigger Feishu/GitHub/webhooks,
or read secrets, .env files, logs, localStorage, private notes, or outputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = ROOT / "evals" / "ai_radar_week2_eval_cases.jsonl"
SCHEMA_PATHS = [
    ROOT / "schemas" / "run_manifest.schema.json",
    ROOT / "schemas" / "tool_call.schema.json",
]

REQUIRED_FIELDS = {
    "case_id",
    "title",
    "objective",
    "category",
    "input_scenario",
    "execution_mode",
    "safety_mode",
    "allowed_actions",
    "forbidden_actions",
    "expected_behavior",
    "expected_gates",
    "expected_artifacts",
    "expected_manifest_assertions",
    "expected_tool_call_assertions",
    "no_external_side_effects",
    "sensitive_data_expectation",
    "implementation_status",
    "runtime_status",
    "related_docs",
    "related_schemas",
}

EXPECTED_IDS = [f"W2-EVAL-{i:03d}" for i in range(1, 11)]
REQUIRED_CATEGORIES = {
    "evidence_gate",
    "publish_gate",
    "tool_permission",
    "safety_mode",
    "schema_contract",
    "observability",
    "redaction",
    "failure_handling",
    "eval_static_check",
    "emergency_stop",
}
REQUIRED_FORBIDDEN_ACTIONS = {
    "feishu_publish",
    "github_workflow_dispatch",
    "webhook_call",
    "external_publish",
}


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def load_jsonl(errors: list[str]) -> list[dict]:
    if not EVAL_PATH.exists():
        add_error(errors, f"missing eval file: {EVAL_PATH.relative_to(ROOT)}")
        return []

    records: list[dict] = []
    non_empty_lines = 0
    for line_number, raw_line in enumerate(EVAL_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        non_empty_lines += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            add_error(errors, f"line {line_number}: invalid JSON: {exc}")
            continue
        if not isinstance(record, dict):
            add_error(errors, f"line {line_number}: record must be a JSON object")
            continue
        records.append(record)

    if non_empty_lines != 10:
        add_error(errors, f"expected exactly 10 non-empty JSONL records, found {non_empty_lines}")
    return records


def as_set(value: object) -> set[str]:
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {item for item in value if isinstance(item, str)}
    return set()


def validate_records(records: list[dict], errors: list[str]) -> None:
    seen_ids: set[str] = set()
    categories: set[str] = set()

    for index, record in enumerate(records, start=1):
        label = record.get("case_id", f"record {index}")
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            add_error(errors, f"{label}: missing required fields: {', '.join(missing)}")

        case_id = record.get("case_id")
        expected_id = EXPECTED_IDS[index - 1] if index <= len(EXPECTED_IDS) else None
        if case_id != expected_id:
            add_error(errors, f"{label}: expected case_id {expected_id}, found {case_id!r}")
        if isinstance(case_id, str):
            if case_id in seen_ids:
                add_error(errors, f"{label}: duplicate case_id")
            seen_ids.add(case_id)

        categories.update(as_set(record.get("category")))

        if record.get("no_external_side_effects") is not True:
            add_error(errors, f"{label}: no_external_side_effects must be true")

        forbidden = as_set(record.get("forbidden_actions"))
        if not forbidden:
            add_error(errors, f"{label}: forbidden_actions must be a non-empty string/list")
        missing_forbidden = sorted(REQUIRED_FORBIDDEN_ACTIONS - forbidden)
        if missing_forbidden:
            add_error(errors, f"{label}: forbidden_actions missing external-risk actions: {', '.join(missing_forbidden)}")

        related_docs = record.get("related_docs")
        if not isinstance(related_docs, list) or not related_docs:
            add_error(errors, f"{label}: related_docs must be a non-empty list")

        related_schemas = set(record.get("related_schemas") or [])
        required_schema_names = {"schemas/run_manifest.schema.json", "schemas/tool_call.schema.json"}
        if not required_schema_names.issubset(related_schemas):
            add_error(errors, f"{label}: related_schemas must include both Phase B schema files")

    if seen_ids != set(EXPECTED_IDS):
        missing_ids = sorted(set(EXPECTED_IDS) - seen_ids)
        extra_ids = sorted(seen_ids - set(EXPECTED_IDS))
        if missing_ids:
            add_error(errors, f"missing case ids: {', '.join(missing_ids)}")
        if extra_ids:
            add_error(errors, f"unexpected case ids: {', '.join(extra_ids)}")

    missing_categories = sorted(REQUIRED_CATEGORIES - categories)
    if missing_categories:
        add_error(errors, f"missing category coverage: {', '.join(missing_categories)}")


def validate_schemas(errors: list[str]) -> None:
    for path in SCHEMA_PATHS:
        if not path.exists():
            add_error(errors, f"missing schema: {path.relative_to(ROOT)}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add_error(errors, f"{path.relative_to(ROOT)}: invalid JSON: {exc}")


def main() -> int:
    errors: list[str] = []
    records = load_jsonl(errors)
    validate_records(records, errors)
    validate_schemas(errors)

    if errors:
        print("AI Radar Week 2 eval checker: FAIL")
        print(f"records_checked: {len(records)}")
        for error in errors:
            print(f"- {error}")
        return 1

    categories = sorted({category for record in records for category in as_set(record.get("category"))})
    print("AI Radar Week 2 eval checker: PASS")
    print(f"records_checked: {len(records)}")
    print(f"case_ids: {', '.join(record['case_id'] for record in records)}")
    print(f"category_coverage: {', '.join(categories)}")
    print("schema_json: valid")
    print("external_side_effects: forbidden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
