from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings

logger = logging.getLogger(__name__)

FEISHU_BASE = "https://open.feishu.cn/open-apis"


class TransientFeishuError(RuntimeError):
    pass


def _response_body(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text


def _header(resp: httpx.Response, name: str) -> str:
    return resp.headers.get(name, "")


def _error_message(action: str, resp: httpx.Response, body: Any) -> str:
    return (
        f"{action} failed: "
        f"status_code={resp.status_code}; "
        f"x_request_id={_header(resp, 'X-Request-Id')}; "
        f"x_tt_logid={_header(resp, 'X-Tt-Logid')}; "
        f"body={body}"
    )


class FeishuClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._tenant_access_token: str | None = None

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(TransientFeishuError),
        reraise=True,
    )
    def tenant_access_token(self) -> str:
        if self._tenant_access_token:
            return self._tenant_access_token
        url = f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.settings.feishu_app_id, "app_secret": self.settings.feishu_app_secret}
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=payload)
        except httpx.RequestError as exc:
            raise TransientFeishuError(f"Failed to get tenant_access_token: network_error={exc}") from exc

        data = _response_body(resp)
        if resp.status_code in {429} or resp.status_code >= 500:
            raise TransientFeishuError(_error_message("Failed to get tenant_access_token", resp, data))
        if resp.status_code >= 400:
            raise RuntimeError(_error_message("Failed to get tenant_access_token", resp, data))
        if not isinstance(data, dict) or data.get("code") != 0:
            raise RuntimeError(_error_message("Failed to get tenant_access_token", resp, data))
        self._tenant_access_token = data["tenant_access_token"]
        return self._tenant_access_token

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(TransientFeishuError),
        reraise=True,
    )
    def upload_file(self, path: Path, parent_folder_token: str | None = None, file_name: str | None = None) -> dict[str, Any]:
        parent = parent_folder_token or self.settings.feishu_folder_token
        if not parent:
            raise RuntimeError("FEISHU_FOLDER_TOKEN is required for Drive file upload")
        if not parent.startswith(("fld", "fldcn")):
            logger.warning("FEISHU_FOLDER_TOKEN may not be a folder token; expected folder token like fld...")
        token = self.tenant_access_token()
        url = f"{FEISHU_BASE}/drive/v1/files/upload_all"
        size = path.stat().st_size
        upload_name = file_name or path.name
        headers = {"Authorization": f"Bearer {token}"}
        logger.info("Uploading %s to Feishu Drive folder", upload_name)
        try:
            with path.open("rb") as f, httpx.Client(timeout=120) as client:
                resp = client.post(
                    url,
                    files={
                        "file_name": (None, upload_name),
                        "parent_type": (None, "explorer"),
                        "parent_node": (None, parent),
                        "size": (None, str(size)),
                        "file": (upload_name, f, "application/octet-stream"),
                    },
                    headers=headers,
                )
        except httpx.RequestError as exc:
            raise TransientFeishuError(f"Feishu upload failed: network_error={exc}") from exc

        result = _response_body(resp)
        if resp.status_code in {429} or resp.status_code >= 500:
            raise TransientFeishuError(_error_message("Feishu upload", resp, result))
        if resp.status_code >= 400:
            raise RuntimeError(_error_message("Feishu upload", resp, result))
        if not isinstance(result, dict) or result.get("code") != 0:
            raise RuntimeError(_error_message("Feishu upload", resp, result))
        return result.get("data", result)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(TransientFeishuError),
        reraise=True,
    )
    def delete_file(self, file_token: str) -> dict[str, Any]:
        if not file_token:
            raise RuntimeError("file_token is required for Feishu file delete")
        token = self.tenant_access_token()
        url = f"{FEISHU_BASE}/drive/v1/files/{file_token}"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.delete(url, params={"type": "file"}, headers=headers)
        except httpx.RequestError as exc:
            raise TransientFeishuError(f"Feishu delete failed: network_error={exc}") from exc

        result = _response_body(resp)
        if resp.status_code in {429} or resp.status_code >= 500:
            raise TransientFeishuError(_error_message("Feishu delete", resp, result))
        if resp.status_code >= 400:
            raise RuntimeError(_error_message("Feishu delete", resp, result))
        if isinstance(result, dict) and result.get("code") not in (None, 0):
            raise RuntimeError(_error_message("Feishu delete", resp, result))
        return result if isinstance(result, dict) else {"body": result}
