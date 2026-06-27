from types import SimpleNamespace

import pytest

from ai_radar_agent import __main__ as main_module
from ai_radar_agent.config import Settings
from ai_radar_agent.feishu_docx import FeishuDocxImportError, FeishuDocxImporter
from ai_radar_agent.feishu_result import FeishuResult


def test_feishu_docx_import_success_returns_doc_url(tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc", FEISHU_TEMP_FOLDER_TOKEN="fldcntmp")
    upload_seen = {}
    importer = FeishuDocxImporter(settings)

    def fake_upload(path, parent_folder_token=None, file_name=None):
        upload_seen["payload"] = {"parent": parent_folder_token, "file_name": file_name}
        return {"file_token": "boxcnsource"}

    importer.drive = SimpleNamespace(
        upload_file=fake_upload,
        delete_file=lambda file_token: {"code": 0},
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    importer._poll_import_task = lambda ticket, timeout_seconds, result: {
        "data": {"result": {"job_status": 0, "token": "docx-token", "url": "https://example.feishu.cn/docx/docx-token"}}
    }

    result = importer.import_markdown(report, title="AI Radar 2026-06-01")

    assert result.docx_url == "https://example.feishu.cn/docx/docx-token"
    assert result.canonical_url == "https://example.feishu.cn/docx/docx-token"
    assert result.canonical_type == "docx"
    assert result.docx_token == "docx-token"
    assert result.fallback_used is False
    assert result.temp_file_deleted is True
    assert result.temp_file_token == "boxcnsource"
    assert result.temp_file_name.startswith(".tmp_AI_radar_2026-06-01_")
    assert upload_seen["payload"]["parent"] == "fldcntmp"
    assert upload_seen["payload"]["file_name"].startswith(".tmp_AI_radar_2026-06-01_")
    assert result.docx_attempted is True
    assert result.docx_import_started is True
    assert result.docx_import_succeeded is True
    assert result.docx_title == "AI Radar 2026-06-01"


def test_feishu_docx_import_constructs_url_from_token(tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc", FEISHU_DOC_BASE_URL="https://tenant.feishu.cn")
    importer = FeishuDocxImporter(settings)
    importer.drive = SimpleNamespace(
        upload_file=lambda path, parent_folder_token=None, file_name=None: {"file_token": "boxcnsource"},
        delete_file=lambda file_token: {"code": 0},
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    importer._poll_import_task = lambda ticket, timeout_seconds, result: {
        "data": {"result": {"job_status": 0, "obj_token": "docx-token"}}
    }

    result = importer.import_markdown(report, title="AI Radar 2026-06-01")

    assert result.docx_token == "docx-token"
    assert result.docx_url == "https://tenant.feishu.cn/docx/docx-token"
    assert result.canonical_type == "docx"


def test_poll_status_2_then_success_continues(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc")
    importer = FeishuDocxImporter(settings)
    importer.drive = SimpleNamespace(
        upload_file=lambda path, parent_folder_token=None, file_name=None: {"file_token": "boxcnsource"},
        delete_file=lambda file_token: {"code": 0},
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    responses = [
        {"code": 0, "data": {"result": {"job_status": 2, "job_error_msg": ""}}, "msg": "success"},
        {
            "code": 0,
            "data": {"result": {"job_status": 0, "token": "docx-token", "url": "https://example.feishu.cn/docx/docx-token"}},
            "msg": "success",
        },
    ]
    importer._get_import_task = lambda ticket: responses.pop(0)
    monkeypatch.setattr("ai_radar_agent.feishu_docx.time.sleep", lambda seconds: None)

    result = importer.import_markdown(report, title="AI Radar 2026-06-01", timeout_seconds=30)

    assert result.docx_poll_attempts == 2
    assert result.docx_last_job_status == "0"
    assert result.docx_import_succeeded is True
    assert result.canonical_type == "docx"
    assert result.docx_url == "https://example.feishu.cn/docx/docx-token"


def test_poll_status_1_then_success_continues(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc")
    importer = FeishuDocxImporter(settings)
    importer.drive = SimpleNamespace(
        upload_file=lambda path, parent_folder_token=None, file_name=None: {"file_token": "boxcnsource"},
        delete_file=lambda file_token: {"code": 0},
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    responses = [
        {"code": 0, "data": {"result": {"job_status": 1, "job_error_msg": ""}}, "msg": "success"},
        {
            "code": 0,
            "data": {"result": {"job_status": 0, "token": "docx-token", "url": "docx-url"}},
            "msg": "success",
        },
    ]
    importer._get_import_task = lambda ticket: responses.pop(0)
    monkeypatch.setattr("ai_radar_agent.feishu_docx.time.sleep", lambda seconds: None)

    result = importer.import_markdown(report, title="AI Radar 2026-06-01", timeout_seconds=30)

    assert result.docx_poll_attempts == 2
    assert result.docx_last_job_status == "0"
    assert result.canonical_type == "docx"


def test_poll_timeout_keeps_temp_file(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc")
    importer = FeishuDocxImporter(settings)
    delete_called = {"value": False}
    importer.drive = SimpleNamespace(
        upload_file=lambda path, parent_folder_token=None, file_name=None: {"file_token": "boxcnsource"},
        delete_file=lambda file_token: delete_called.update(value=True),
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    importer._get_import_task = lambda ticket: {
        "code": 0,
        "data": {"result": {"job_status": 2, "job_error_msg": ""}},
        "msg": "success",
    }
    clock = {"value": 0.0}
    monkeypatch.setattr("ai_radar_agent.feishu_docx.time.monotonic", lambda: clock["value"])
    monkeypatch.setattr("ai_radar_agent.feishu_docx.time.sleep", lambda seconds: clock.update(value=clock["value"] + seconds))

    with pytest.raises(FeishuDocxImportError) as exc:
        importer.import_markdown(report, title="AI Radar 2026-06-01", timeout_seconds=4)

    result = exc.value.result
    assert "timed out" in result.docx_error_summary
    assert result.docx_last_job_status == "2"
    assert result.temp_file_deleted is False
    assert result.temp_file_delete_error == "not deleted because import task timed out while still processing"
    assert delete_called["value"] is False


def test_poll_body_code_error_records_summary(tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc")
    importer = FeishuDocxImporter(settings)
    importer.drive = SimpleNamespace(
        upload_file=lambda path, parent_folder_token=None, file_name=None: {"file_token": "boxcnsource"},
        delete_file=lambda file_token: {"code": 0},
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    importer._get_import_task = lambda ticket: {"code": 999, "msg": "bad task"}

    with pytest.raises(FeishuDocxImportError) as exc:
        importer.import_markdown(report, title="AI Radar 2026-06-01", timeout_seconds=30)

    assert "poll API failed" in exc.value.result.docx_error_summary
    assert "bad task" in exc.value.result.docx_error_summary
    assert exc.value.result.temp_file_deleted is True


def test_poll_job_error_msg_records_summary(tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc")
    importer = FeishuDocxImporter(settings)
    importer.drive = SimpleNamespace(
        upload_file=lambda path, parent_folder_token=None, file_name=None: {"file_token": "boxcnsource"},
        delete_file=lambda file_token: {"code": 0},
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    importer._get_import_task = lambda ticket: {
        "code": 0,
        "data": {"result": {"job_status": 3, "job_error_msg": "convert failed"}},
        "msg": "success",
    }

    with pytest.raises(FeishuDocxImportError) as exc:
        importer.import_markdown(report, title="AI Radar 2026-06-01", timeout_seconds=30)

    assert "convert failed" in exc.value.result.docx_error_summary
    assert exc.value.result.temp_file_deleted is True


def test_docx_import_failure_falls_back_to_drive_md(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(
        FEISHU_APP_ID="app",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
        OUTPUT_MODE="feishu_docx_import",
    )

    class FakeImporter:
        def __init__(self, settings):
            pass

        def import_markdown(self, path, title):
            raise RuntimeError("import failed")

    monkeypatch.setattr(main_module, "FeishuDocxImporter", FakeImporter)
    monkeypatch.setattr(
        main_module,
        "_upload_drive_md",
        lambda settings, path, output_mode="feishu_drive_md": {
            "output_mode": output_mode,
            "docx_url": "",
            "md_url": "md-url",
            "canonical_url": "md-url",
            "canonical_type": "md",
        },
    )

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=False)

    assert result.output_mode == "feishu_docx_import"
    assert result.canonical_url == "md-url"
    assert result.canonical_type == "md"
    assert result.fallback_used is True
    assert result.docx_attempted is True
    assert result.docx_error_summary
    assert result.fallback_reason


def test_docx_import_success_without_url_falls_back_with_raw_summary(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(
        FEISHU_APP_ID="app",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
        OUTPUT_MODE="feishu_docx_import",
    )

    class FakeImporter:
        def __init__(self, settings):
            pass

        def import_markdown(self, path, title):
            return FeishuResult(
                output_mode="feishu_docx_import",
                docx_attempted=True,
                docx_import_started=True,
                docx_import_succeeded=True,
                docx_raw_result_summary='{"result": {"job_status": 0}}',
            ).finalize()

    monkeypatch.setattr(main_module, "FeishuDocxImporter", FakeImporter)
    monkeypatch.setattr(
        main_module,
        "_upload_drive_md",
        lambda settings, path, output_mode="feishu_drive_md": FeishuResult(
            output_mode=output_mode, md_url="md-url", md_token="md-token"
        ).finalize(),
    )

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=False)

    assert result.docx_import_succeeded is True
    assert result.docx_url == ""
    assert result.docx_raw_result_summary
    assert result.fallback_used is True
    assert result.fallback_reason == "docx import succeeded but docx_url could not be resolved"
    assert result.canonical_type == "md"


def test_docx_import_timeout_falls_back_to_md_without_deleting_temp(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(
        FEISHU_APP_ID="app",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
        OUTPUT_MODE="feishu_docx_import",
    )

    class FakeImporter:
        def __init__(self, settings):
            pass

        def import_markdown(self, path, title):
            result = FeishuResult(
                output_mode="feishu_docx_import",
                docx_attempted=True,
                docx_import_started=True,
                docx_import_succeeded=False,
                docx_last_job_status="2",
                docx_poll_attempts=2,
                docx_poll_duration_seconds=4.0,
                docx_error_summary="import task timed out while job_status=2",
                fallback_reason="import task timed out while job_status=2",
                temp_file_token="boxcnsource",
                temp_file_deleted=False,
                temp_file_delete_error="not deleted because import task timed out while still processing",
            )
            raise main_module.FeishuDocxImportError(result.docx_error_summary, result)

    monkeypatch.setattr(main_module, "FeishuDocxImporter", FakeImporter)
    monkeypatch.setattr(
        main_module,
        "_upload_drive_md",
        lambda settings, path, output_mode="feishu_drive_md": FeishuResult(
            output_mode=output_mode, md_url="md-url", md_token="md-token"
        ).finalize(),
    )

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=False)

    assert result.fallback_used is True
    assert result.canonical_type == "md"
    assert result.fallback_reason == "import task timed out while job_status=2"
    assert result.temp_file_token == "boxcnsource"
    assert result.temp_file_deleted is False
    assert result.temp_file_delete_error == "not deleted because import task timed out while still processing"


def test_docx_success_does_not_upload_final_md_by_default(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(
        FEISHU_APP_ID="app",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
        OUTPUT_MODE="feishu_docx_import",
    )

    class FakeImporter:
        def __init__(self, settings):
            pass

        def import_markdown(self, path, title):
            return FeishuResult(
                output_mode="feishu_docx_import",
                docx_attempted=True,
                docx_import_started=True,
                docx_import_succeeded=True,
                docx_url="docx-url",
            ).finalize()

    monkeypatch.setattr(main_module, "FeishuDocxImporter", FakeImporter)
    monkeypatch.setattr(
        main_module,
        "_upload_drive_md",
        lambda settings, path: (_ for _ in ()).throw(AssertionError("final md upload should not run")),
    )

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=False)

    assert result.canonical_url == "docx-url"
    assert result.canonical_type == "docx"
    assert result.md_url == ""


def test_keep_md_archive_does_not_override_docx_canonical(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(
        FEISHU_APP_ID="app",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
        OUTPUT_MODE="feishu_docx_import",
        FEISHU_KEEP_MD_ARCHIVE=True,
    )

    class FakeImporter:
        def __init__(self, settings):
            pass

        def import_markdown(self, path, title):
            return FeishuResult(
                output_mode="feishu_docx_import",
                docx_attempted=True,
                docx_import_started=True,
                docx_import_succeeded=True,
                docx_url="docx-url",
            ).finalize()

    monkeypatch.setattr(main_module, "FeishuDocxImporter", FakeImporter)
    monkeypatch.setattr(
        main_module,
        "_upload_drive_md",
        lambda settings, path, output_mode="feishu_drive_md": {
            "output_mode": "feishu_drive_md",
            "docx_url": "",
            "md_url": "md-url",
            "canonical_url": "md-url",
            "canonical_type": "md",
            "md_token": "md-token",
        },
    )

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=False)

    assert result.docx_url == "docx-url"
    assert result.md_url == "md-url"
    assert result.canonical_url == "docx-url"
    assert result.canonical_type == "docx"
    assert result.md_archive_used is True


def test_temp_file_delete_failure_only_warns(tmp_path, caplog):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(FEISHU_FOLDER_TOKEN="fldcnabc")
    importer = FeishuDocxImporter(settings)
    importer.drive = SimpleNamespace(
        upload_file=lambda path, parent_folder_token=None, file_name=None: {"file_token": "boxcnsource"},
        delete_file=lambda file_token: (_ for _ in ()).throw(RuntimeError("delete forbidden")),
    )
    importer._create_import_task = lambda file_token, title: "ticket-1"
    importer._poll_import_task = lambda ticket, timeout_seconds, result: {
        "data": {"result": {"job_status": 0, "token": "docx-token", "url": "docx-url"}}
    }

    result = importer.import_markdown(report, title="AI Radar 2026-06-01")

    assert result.temp_file_deleted is False
    assert result.canonical_url == "docx-url"
    assert result.temp_file_token == "boxcnsource"
    assert result.temp_file_delete_error
    assert result.canonical_url != result.temp_file_token
    assert result.warnings


def test_output_mode_none_does_not_call_feishu(tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(OUTPUT_MODE="none")

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=False)

    assert result.skipped is True
    assert result.reason == "output_mode=none"


def test_docx_import_dry_run_does_not_call_importer(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(OUTPUT_MODE="feishu_docx_import")

    monkeypatch.setattr(
        main_module,
        "FeishuDocxImporter",
        lambda settings: (_ for _ in ()).throw(AssertionError("importer should not be created")),
    )

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=True)

    assert result.skipped is True
    assert result.reason == "dry_run"


def test_output_mode_drive_md_only_uploads_md(monkeypatch, tmp_path):
    report = tmp_path / "AI_radar_2026-06-01.md"
    report.write_text("# report", encoding="utf-8")
    settings = Settings(
        FEISHU_APP_ID="app",
        FEISHU_APP_SECRET="secret",
        FEISHU_FOLDER_TOKEN="fldcnabc",
        OUTPUT_MODE="feishu_drive_md",
    )

    monkeypatch.setattr(
        main_module,
        "FeishuDocxImporter",
        lambda settings: (_ for _ in ()).throw(AssertionError("docx import should not run")),
    )
    monkeypatch.setattr(
        main_module,
        "_upload_drive_md",
        lambda settings, path, output_mode="feishu_drive_md": FeishuResult(
            output_mode=output_mode, md_url="md-url", md_token="md-token"
        ).finalize(),
    )

    result = main_module._handle_feishu_output(settings, report, window=SimpleNamespace(date_str="2026-06-01"), dry_run=False)

    assert result.canonical_type == "md"
    assert result.canonical_url == "md-url"
    assert result.docx_url == ""
