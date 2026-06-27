from ai_radar_agent.feishu_result import FeishuResult


def test_safe_summary_omits_tokens():
    result = FeishuResult(
        output_mode="feishu_docx_import",
        docx_url="docx-url",
        docx_token="docx-token-secret",
        md_token="md-token-secret",
        temp_file_token="temp-token-secret",
    ).finalize()

    text = str(result.safe_summary())

    assert "docx-token-secret" not in text
    assert "md-token-secret" not in text
    assert "temp-token-secret" not in text
    assert result.safe_summary()["docx_url_exists"] is True
    assert result.safe_summary()["temp_file_token_exists"] is True
