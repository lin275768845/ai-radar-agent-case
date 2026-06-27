import httpx
import pytest

from ai_radar_agent.config import Settings
from ai_radar_agent.feishu import FeishuClient


def test_feishu_upload_http_400_error_includes_body_and_request_ids(monkeypatch, tmp_path):
    uploaded = tmp_path / "AI_radar_2026-06-01.md"
    uploaded.write_text("# report", encoding="utf-8")

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, files, headers):
            assert "data" not in files
            assert files["file_name"] == (None, uploaded.name)
            assert files["parent_type"] == (None, "explorer")
            assert files["parent_node"] == (None, "fldcnabc")
            assert files["size"] == (None, str(uploaded.stat().st_size))
            assert files["file"][0] == uploaded.name
            return httpx.Response(
                400,
                json={"code": 99991663, "msg": "bad parent_node"},
                headers={"X-Request-Id": "req-123", "X-Tt-Logid": "log-456"},
            )

    settings = Settings(
        FEISHU_APP_ID="cli_test",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
    )
    client = FeishuClient(settings)
    client._tenant_access_token = "tenant-token"
    monkeypatch.setattr("ai_radar_agent.feishu.httpx.Client", FakeClient)

    with pytest.raises(RuntimeError) as exc:
        client.upload_file(uploaded)

    message = str(exc.value)
    assert "status_code=400" in message
    assert "bad parent_node" in message
    assert "x_request_id=req-123" in message
    assert "x_tt_logid=log-456" in message
    assert "tenant-token" not in message
    assert "secret" not in message


def test_feishu_delete_file_passes_file_type(monkeypatch):
    seen = {}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def delete(self, url, params, headers):
            seen["url"] = url
            seen["params"] = params
            return httpx.Response(200, json={"code": 0})

    settings = Settings(
        FEISHU_APP_ID="cli_test",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
    )
    client = FeishuClient(settings)
    client._tenant_access_token = "tenant-token"
    monkeypatch.setattr("ai_radar_agent.feishu.httpx.Client", FakeClient)

    client.delete_file("boxcnsource")

    assert seen["url"].endswith("/drive/v1/files/boxcnsource")
    assert seen["params"] == {"type": "file"}
