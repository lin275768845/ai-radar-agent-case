from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

import httpx

from ..models import EvidenceItem, TimeWindow

logger = logging.getLogger(__name__)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilyConnectivityError(RuntimeError):
    pass


class TavilyAuthError(RuntimeError):
    pass


class TavilyBadRequestError(RuntimeError):
    pass


class TavilyRateLimitError(RuntimeError):
    pass


class TavilyServerError(RuntimeError):
    pass


class TavilyFetcher:
    def __init__(
        self,
        api_key: str,
        max_results: int = 5,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        max_queries: int = 8,
        max_consecutive_connect_failures: int = 2,
    ):
        self.api_key = api_key
        self.max_results = min(max_results, 5)
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_queries = max_queries
        self.max_consecutive_connect_failures = max_consecutive_connect_failures
        self.failed_count = 0
        self.status = "ok"
        self.error_summary = ""
        self.results_count = 0
        self._errors: list[str] = []
        self._consecutive_connect_failures = 0
        self._bad_request_count = 0
        self._queries_used = 0

    @property
    def queries_used(self) -> int:
        return self._queries_used

    def healthcheck(self, window: TimeWindow) -> bool:
        try:
            self._search_once("OpenAI AI", window, max_results=1, read_timeout=min(self.read_timeout, 10.0))
            return True
        except TavilyConnectivityError as exc:
            self.failed_count += 1
            self._set_status("connectivity_failed", exc)
        except TavilyAuthError as exc:
            self.failed_count += 1
            self._set_status("auth_failed", exc)
        except TavilyBadRequestError as exc:
            self.failed_count += 1
            self._set_status("bad_request", exc)
        except TavilyRateLimitError as exc:
            self.failed_count += 1
            self._set_status("rate_limited", exc)
        except TavilyServerError as exc:
            self.failed_count += 1
            self._set_status("server_error", exc)
        except Exception as exc:  # noqa: BLE001
            self.failed_count += 1
            self._set_status("connectivity_failed", exc)
        return False

    def _search_once(
        self,
        query: str,
        window: TimeWindow,
        *,
        max_results: int | None = None,
        read_timeout: float | None = None,
    ) -> dict[str, Any]:
        start_date, end_date = self._date_bounds(window)
        payload = {
            "query": query,
            "topic": "general",
            "search_depth": "basic",
            "start_date": start_date,
            "end_date": end_date,
            "max_results": min(max_results or self.max_results, 5),
            "include_answer": False,
            "include_raw_content": False,
        }
        logger.info(
            "Tavily search query=%r start_date=%s end_date=%s max_results=%s",
            query,
            start_date,
            end_date,
            payload["max_results"],
        )
        resp = self._post(payload, read_timeout=read_timeout)
        body = self._response_body(resp)
        if resp.status_code == 200 and isinstance(body, dict):
            body.setdefault("results", [])
            return body
        message = f"Tavily search failed: status_code={resp.status_code}; body={body}"
        if resp.status_code == 400:
            raise TavilyBadRequestError(message)
        if resp.status_code in {401, 403}:
            raise TavilyAuthError(message)
        if resp.status_code == 429:
            raise TavilyRateLimitError(message)
        if resp.status_code >= 500:
            raise TavilyServerError(message)
        raise RuntimeError(message)

    def _post(self, payload: dict[str, Any], read_timeout: float | None = None) -> httpx.Response:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        timeout = httpx.Timeout(
            connect=self.connect_timeout,
            read=read_timeout or self.read_timeout,
            write=5.0,
            pool=5.0,
        )
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                with httpx.Client(timeout=timeout) as client:
                    resp = client.post(TAVILY_SEARCH_URL, json=payload, headers=headers)
            except (httpx.ConnectTimeout, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise TavilyConnectivityError(f"Tavily connectivity failed: {exc}") from exc
            except httpx.RequestError as exc:
                last_exc = exc
                if attempt == 0:
                    time.sleep(1)
                    continue
                raise RuntimeError(f"Tavily network error: {exc}") from exc
            if (resp.status_code == 429 or resp.status_code >= 500) and attempt == 0:
                time.sleep(1)
                continue
            return resp
        raise TavilyConnectivityError(f"Tavily connectivity failed: {last_exc}")

    def search_queries(
        self,
        queries: list[str],
        window: TimeWindow,
        region_hint: str,
        source_basket: str,
    ) -> list[EvidenceItem]:
        items: list[EvidenceItem] = []
        for query in queries:
            if self._queries_used >= self.max_queries:
                logger.warning("Tavily max query limit reached: %s", self.max_queries)
                break
            self._queries_used += 1
            logger.info("Searching [%s] %s", source_basket, query)
            try:
                response = self._search_once(query, window)
            except TavilyConnectivityError as exc:
                self.failed_count += 1
                self._consecutive_connect_failures += 1
                self._record_error(exc)
                self.status = "connectivity_failed"
                logger.warning("Search failed for query=%r: %s", query, exc)
                if self._consecutive_connect_failures >= self.max_consecutive_connect_failures:
                    self.status = "skipped_after_consecutive_failures"
                    logger.warning(
                        "Tavily connectivity degraded; disabling Tavily for this run and falling back to RSS-only evidence."
                    )
                    break
                continue
            except TavilyBadRequestError as exc:
                self.failed_count += 1
                self._bad_request_count += 1
                self.status = "bad_request"
                self._record_error(exc)
                logger.warning("Search failed for query=%r: %s", query, exc)
                logger.warning("Tavily returned bad request; stopping Tavily for this run.")
                break
            except TavilyAuthError as exc:
                self.failed_count += 1
                self.status = "auth_failed"
                self._record_error(exc)
                logger.warning("Tavily auth failed; stopping Tavily for this run: %s", exc)
                break
            except TavilyRateLimitError as exc:
                self.failed_count += 1
                self.status = "rate_limited"
                self._record_error(exc)
                logger.warning("Search failed for query=%r: %s", query, exc)
                continue
            except TavilyServerError as exc:
                self.failed_count += 1
                self.status = "server_error"
                self._record_error(exc)
                logger.warning("Search failed for query=%r: %s", query, exc)
                continue
            except Exception as exc:  # noqa: BLE001
                self.failed_count += 1
                self._record_error(exc)
                logger.warning("Search failed for query=%r: %s", query, exc)
                continue

            self._consecutive_connect_failures = 0
            if self.status not in {"bad_request", "rate_limited", "server_error"}:
                self.status = "ok"
            results = response.get("results", []) or []
            self.results_count += len(results)
            for result in results:
                items.append(
                    EvidenceItem(
                        title=result.get("title") or "",
                        url=result.get("url") or "",
                        content=result.get("content") or result.get("raw_content") or "",
                        source=result.get("source") or "Tavily",
                        published_at=result.get("published_date") or "",
                        provider="tavily",
                        retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        region_hint=region_hint,  # type: ignore[arg-type]
                        source_basket=source_basket,
                        source_type="tavily",
                    )
                )
        self.error_summary = " | ".join(self._errors)[:300]
        return items

    @staticmethod
    def _date_bounds(window: TimeWindow) -> tuple[str, str]:
        next_day = window.target_date + timedelta(days=1)
        return window.target_date.isoformat(), next_day.isoformat()

    @staticmethod
    def _response_body(resp: httpx.Response) -> Any:
        try:
            return resp.json()
        except ValueError:
            return resp.text

    def _set_status(self, status: str, exc: Exception) -> None:
        self.status = status
        self._record_error(exc)
        self.error_summary = " | ".join(self._errors)[:300]

    def _record_error(self, exc: Exception) -> None:
        text = str(exc)
        if text:
            self._errors.append(text[:300])
