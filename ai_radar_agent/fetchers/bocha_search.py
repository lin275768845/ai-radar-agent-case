from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from ..models import EvidenceItem, TimeWindow

logger = logging.getLogger(__name__)


class BochaConnectivityError(RuntimeError):
    pass


class BochaAuthError(RuntimeError):
    pass


class BochaBadRequestError(RuntimeError):
    pass


class BochaRateLimitError(RuntimeError):
    pass


class BochaServerError(RuntimeError):
    pass


class BochaFetcher:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.bochaai.com",
        max_results: int = 5,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        max_queries: int = 20,
        max_consecutive_connect_failures: int = 2,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_results = min(max_results, 10)
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_queries = max_queries
        self.max_consecutive_connect_failures = max_consecutive_connect_failures
        self.failed_count = 0
        self.status = "ok"
        self.error_summary = ""
        self.results_count = 0
        self.queries_used = 0
        self._errors: list[str] = []
        self._consecutive_connect_failures = 0

    def search_queries(
        self,
        queries: list[str],
        window: TimeWindow,
        region_hint: str,
        source_basket: str,
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for query in queries:
            if self.queries_used >= self.max_queries:
                logger.warning("Bocha max query limit reached: %s", self.max_queries)
                break
            self.queries_used += 1
            try:
                response = self._search_once(query, window)
            except BochaConnectivityError as exc:
                self.failed_count += 1
                self._consecutive_connect_failures += 1
                self.status = "connectivity_failed"
                self._record_error(exc)
                logger.warning("Bocha search failed for query=%r: %s", query, exc)
                if self._consecutive_connect_failures >= self.max_consecutive_connect_failures:
                    self.status = "skipped_after_consecutive_failures"
                    logger.warning("Bocha connectivity degraded; disabling Bocha for this run.")
                    break
                continue
            except BochaBadRequestError as exc:
                self.failed_count += 1
                self.status = "bad_request"
                self._record_error(exc)
                logger.warning("Bocha bad request for query=%r: %s", query, exc)
                continue
            except BochaAuthError as exc:
                self.failed_count += 1
                self.status = "auth_failed"
                self._record_error(exc)
                logger.warning("Bocha auth failed; stopping Bocha for this run: %s", exc)
                break
            except BochaRateLimitError as exc:
                self.failed_count += 1
                self.status = "rate_limited"
                self._record_error(exc)
                logger.warning("Bocha rate limited for query=%r: %s", query, exc)
                continue
            except BochaServerError as exc:
                self.failed_count += 1
                self.status = "server_error"
                self._record_error(exc)
                logger.warning("Bocha server error for query=%r: %s", query, exc)
                continue
            except Exception as exc:  # noqa: BLE001
                self.failed_count += 1
                self._record_error(exc)
                logger.warning("Bocha search failed for query=%r: %s", query, exc)
                continue

            self._consecutive_connect_failures = 0
            if self.status not in {"rate_limited", "server_error", "bad_request"}:
                self.status = "ok"
            results = self._extract_results(response)
            self.results_count += len(results)
            for result in results:
                item = self._to_evidence_item(result, region_hint=region_hint, source_basket=source_basket)
                if _within_window(item.published_at, window):
                    items.append(item)
        self.error_summary = " | ".join(self._errors)[:300]
        return items

    def _search_once(self, query: str, window: TimeWindow) -> dict[str, Any]:
        payload = {
            "query": query,
            "freshness": _freshness_for_window(window),
            "summary": True,
            "count": self.max_results,
        }
        resp = self._post(payload)
        body = self._response_body(resp)
        if resp.status_code == 200 and isinstance(body, dict):
            return body
        message = f"Bocha search failed: status_code={resp.status_code}; body={body}"
        if resp.status_code == 400:
            raise BochaBadRequestError(message)
        if resp.status_code in {401, 403}:
            raise BochaAuthError(message)
        if resp.status_code == 429:
            raise BochaRateLimitError(message)
        if resp.status_code >= 500:
            raise BochaServerError(message)
        raise RuntimeError(message)

    def _post(self, payload: dict[str, Any]) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        timeout = httpx.Timeout(connect=self.connect_timeout, read=self.read_timeout, write=5.0, pool=5.0)
        last_exc: Exception | None = None
        url = f"{self.base_url}/v1/web-search"
        for attempt in range(2):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(url, json=payload, headers=headers)
            except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise BochaConnectivityError(f"Bocha connectivity failed: {exc}") from exc
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"Bocha network error: {exc}") from exc
            if (resp.status_code == 429 or resp.status_code >= 500) and attempt == 0:
                time.sleep(1)
                continue
            return resp
        raise BochaConnectivityError(f"Bocha connectivity failed: {last_exc}")

    @staticmethod
    def _extract_results(body: dict[str, Any]) -> list[dict[str, Any]]:
        data = body.get("data") if isinstance(body.get("data"), dict) else body
        candidates = (
            data.get("webPages", {}).get("value") if isinstance(data.get("webPages"), dict) else None,
            data.get("webpages", {}).get("value") if isinstance(data.get("webpages"), dict) else None,
            data.get("results"),
            data.get("items"),
        )
        for candidate in candidates:
            if isinstance(candidate, list):
                return [item for item in candidate if isinstance(item, dict)]
        return []

    @staticmethod
    def _to_evidence_item(result: dict[str, Any], *, region_hint: str, source_basket: str) -> EvidenceItem:
        published_at = str(result.get("datePublished") or result.get("publishedTime") or result.get("published_at") or "")
        url = str(result.get("url") or result.get("link") or "")
        source = str(result.get("siteName") or result.get("site_name") or result.get("source") or _domain(url))
        return EvidenceItem(
            title=str(result.get("name") or result.get("title") or ""),
            url=url,
            content=str(result.get("summary") or result.get("snippet") or result.get("description") or ""),
            source=source,
            published_at=published_at,
            provider="bocha",
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            region_hint=region_hint,  # type: ignore[arg-type]
            source_basket=source_basket,
            source_type="bocha",
        )

    @staticmethod
    def _response_body(resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except ValueError:
            return resp.text

    def _record_error(self, exc: Exception) -> None:
        text = str(exc)
        if text:
            self._errors.append(text[:300])
            self.error_summary = " | ".join(self._errors)[:300]


def _within_window(published_at: str, window: TimeWindow) -> bool:
    if not published_at:
        return True
    try:
        value = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if value.tzinfo is None:
        value = value.replace(tzinfo=window.start.tzinfo)
    return window.start <= value.astimezone(window.start.tzinfo) <= window.end


def _freshness_for_window(window: TimeWindow) -> str:
    date_str = window.target_date.isoformat()
    return f"{date_str}..{date_str}"


def _domain(url: str) -> str:
    try:
        return httpx.URL(url).host or ""
    except Exception:  # noqa: BLE001
        return ""
