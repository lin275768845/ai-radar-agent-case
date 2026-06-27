from __future__ import annotations

import logging
import os
import time
import uuid
import json
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings
from .feishu import FEISHU_BASE, FeishuClient, TransientFeishuError, _error_message, _response_body
from .feishu_result import FeishuResult

logger = logging.getLogger(__name__)


class FeishuDocxImportError(RuntimeError):
    def __init__(self, message: str, result: FeishuResult):
        super().__init__(message)
        self.result = result


class FeishuDocxImporter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.drive = FeishuClient(settings)

    def import_markdown(self, path: Path, title: str, timeout_seconds: int | None = None) -> FeishuResult:
        result = FeishuResult(output_mode="feishu_docx_import", docx_attempted=True, docx_title=title)
        timeout_seconds = timeout_seconds or self.settings.feishu_import_poll_timeout_seconds
        if not self.settings.feishu_folder_token:
            return self._fail(result, "FEISHU_FOLDER_TOKEN is required for Feishu docx import")
        if not self.settings.feishu_folder_token.startswith(("fld", "fldcn")):
            logger.warning("FEISHU_FOLDER_TOKEN may not be a folder token; expected folder token like fld...")

        temp_folder = self.settings.feishu_temp_folder_token or self.settings.feishu_folder_token
        temp_name = self._temporary_file_name(path)
        result.temp_file_name = temp_name
        try:
            upload_result = self.drive.upload_file(path, parent_folder_token=temp_folder, file_name=temp_name)
        except Exception as exc:  # noqa: BLE001
            return self._fail(result, f"temporary source upload failed: {exc}")
        file_token = _extract_file_token(upload_result)
        if not file_token:
            return self._fail(
                result,
                f"temporary source upload result did not include file_token; body={_summary(upload_result)}",
            )
        result.temp_file_token = file_token

        try:
            ticket = self._create_import_task(file_token=file_token, title=title)
        except Exception as exc:  # noqa: BLE001
            return self._fail(result, f"create import task failed: {exc}")
        result.docx_import_started = True

        try:
            raw_result = self._poll_import_task(ticket, timeout_seconds=timeout_seconds, result=result)
        except FeishuDocxImportError:
            raise
        except Exception as exc:  # noqa: BLE001
            return self._fail(result, f"poll import task failed: {exc}", delete_temp=True)
        result.docx_import_succeeded = True
        result.docx_raw_result_summary = _summary(raw_result)
        token = _extract_doc_token(raw_result)
        url = _extract_doc_url(raw_result)
        if not url and token:
            url = self._docx_url_from_token(token)
        source_deleted, warning = self._delete_temp_file(file_token)
        warnings = [warning] if warning else []
        result.docx_url = url
        result.docx_token = token
        result.temp_file_deleted = source_deleted
        result.temp_file_delete_error = warning
        result.warnings = warnings
        return result.finalize()

    def _fail(self, result: FeishuResult, message: str, *, delete_temp: bool = False) -> FeishuResult:
        if delete_temp and result.temp_file_token and not result.temp_file_deleted:
            deleted, warning = self._delete_temp_file(result.temp_file_token)
            result.temp_file_deleted = deleted
            result.temp_file_delete_error = warning
            if warning:
                result.warnings.append(warning)
        result.docx_error_summary = message[:300]
        raise FeishuDocxImportError(message, result)

    @staticmethod
    def _temporary_file_name(path: Path) -> str:
        run_id = os.getenv("GITHUB_RUN_ID") or uuid.uuid4().hex
        return f".tmp_{path.stem}_{run_id}{path.suffix}"

    def _delete_temp_file(self, file_token: str) -> tuple[bool, str]:
        try:
            self.drive.delete_file(file_token)
            return True, ""
        except Exception as exc:  # noqa: BLE001
            warning = f"Failed to delete temporary Feishu source md: {exc}"
            logger.warning(warning)
            return False, warning

    def _docx_url_from_token(self, token: str) -> str:
        base = self.settings.feishu_doc_base_url.rstrip("/") or "https://my.feishu.cn"
        return f"{base}/docx/{token}"

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(TransientFeishuError),
        reraise=True,
    )
    def _create_import_task(self, file_token: str, title: str) -> str:
        token = self.drive.tenant_access_token()
        url = f"{FEISHU_BASE}/drive/v1/import_tasks"
        payload = {
            "file_extension": "md",
            "file_token": file_token,
            "type": "docx",
            "file_name": title,
            "point": {"mount_type": 1, "mount_key": self.settings.feishu_folder_token},
        }
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"}
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise TransientFeishuError(f"Feishu import task failed: network_error={exc}") from exc

        body = _response_body(resp)
        if resp.status_code in {429} or resp.status_code >= 500:
            raise TransientFeishuError(_error_message("Feishu import task", resp, body))
        if resp.status_code >= 400:
            raise RuntimeError(_error_message("Feishu import task", resp, body))
        if not isinstance(body, dict) or body.get("code") != 0:
            raise RuntimeError(_error_message("Feishu import task", resp, body))
        ticket = (body.get("data") or {}).get("ticket")
        if not ticket:
            raise RuntimeError(f"Feishu import task failed: response missing ticket; body={body}")
        return ticket

    def _poll_import_task(self, ticket: str, timeout_seconds: int, result: FeishuResult) -> dict[str, Any]:
        start = time.monotonic()
        deadline = start + timeout_seconds
        attempt = 0
        while time.monotonic() < deadline:
            attempt += 1
            body = self._get_import_task(ticket)
            if isinstance(body, dict) and body.get("code") not in (None, 0):
                result.docx_poll_attempts = attempt
                result.docx_raw_result_summary = _summary(body)
                result.docx_poll_duration_seconds = round(time.monotonic() - start, 2)
                return self._fail(
                    result,
                    f"Feishu import task poll API failed: body={_summary(body)}",
                    delete_temp=True,
                )
            status = _extract_job_status(body)
            result.docx_poll_attempts = attempt
            result.docx_last_job_status = "" if status is None else str(status)
            result.docx_raw_result_summary = _summary(body)
            result.docx_poll_duration_seconds = round(time.monotonic() - start, 2)
            logger.info(
                "Feishu import task polling: ticket=%s, job_status=%s, attempt=%s",
                ticket,
                result.docx_last_job_status,
                attempt,
            )
            if status == 0:
                return body
            job_error = _extract_job_error_msg(body)
            if job_error:
                return self._fail(
                    result,
                    f"Feishu import task failed: job_status={result.docx_last_job_status}; "
                    f"job_error_msg={job_error}; body={_summary(body)}",
                    delete_temp=True,
                )
            if status in {1, 2}:
                interval = self.settings.feishu_import_poll_interval_seconds if attempt <= 5 else 5.0
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                time.sleep(min(interval, remaining))
                continue
            return self._fail(
                result,
                f"Feishu import task failed: job_status={result.docx_last_job_status}; body={_summary(body)}",
                delete_temp=True,
            )
        result.docx_poll_duration_seconds = round(time.monotonic() - start, 2)
        result.temp_file_deleted = False
        result.temp_file_delete_error = "not deleted because import task timed out while still processing"
        return self._fail(
            result,
            f"import task timed out while job_status={result.docx_last_job_status or 'unknown'}",
            delete_temp=False,
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(TransientFeishuError),
        reraise=True,
    )
    def _get_import_task(self, ticket: str) -> dict[str, Any]:
        token = self.drive.tenant_access_token()
        url = f"{FEISHU_BASE}/drive/v1/import_tasks/{ticket}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, headers=headers)
        except httpx.RequestError as exc:
            raise TransientFeishuError(f"Feishu import task poll failed: network_error={exc}") from exc

        body = _response_body(resp)
        if resp.status_code in {429} or resp.status_code >= 500:
            raise TransientFeishuError(_error_message("Feishu import task poll", resp, body))
        if resp.status_code >= 400:
            raise RuntimeError(_error_message("Feishu import task poll", resp, body))
        if not isinstance(body, dict) or body.get("code") != 0:
            raise RuntimeError(_error_message("Feishu import task poll", resp, body))
        return body


def _extract_file_token(data: dict[str, Any]) -> str:
    return str(
        data.get("file_token")
        or data.get("token")
        or ((data.get("file") or {}).get("file_token") if isinstance(data.get("file"), dict) else "")
        or ""
    )


def _extract_job_status(data: dict[str, Any]) -> int | None:
    result = (data.get("data") or {}).get("result") or data.get("result") or {}
    status = result.get("job_status", (data.get("data") or {}).get("job_status"))
    return int(status) if status is not None else None


def _extract_job_error_msg(data: dict[str, Any]) -> str:
    result = (data.get("data") or {}).get("result") or data.get("result") or {}
    return str(result.get("job_error_msg") or (data.get("data") or {}).get("job_error_msg") or "")


def _extract_doc_token(data: dict[str, Any]) -> str:
    return _find_first(data, {"token", "obj_token", "doc_token", "document_id", "document_token"})


def _extract_doc_url(data: dict[str, Any]) -> str:
    return _find_first(data, {"url", "doc_url"})


def _find_first(value: Any, keys: set[str]) -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys and item:
                return str(item)
        for item in value.values():
            found = _find_first(item, keys)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_first(item, keys)
            if found:
                return found
    return ""


def _summary(value: Any) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except TypeError:
        text = str(value)
    return text[:300]
