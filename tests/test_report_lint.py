from ai_radar_agent.models import EvidenceItem
from ai_radar_agent.report_lint import lint_report


def _good_report(extra: str = ""):
    return "\n".join(
        [
            "## 国内候选事件筛选表",
            "国内核心事件：不强行凑数。",
            "## 海外候选事件筛选表",
            "海外核心事件：不强行凑数。",
            "## 国内版正式雷达",
            "内容。",
            "## 海外版正式雷达",
            "内容。",
            "## 输出前自我检查清单",
            "已检查。",
            "来源：https://example.com/a",
            extra,
        ]
    )


def test_report_lint_detects_missing_sections():
    result = lint_report("# AI Radar", [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.passed is False
    assert any("missing required section" in error for error in result.errors)
    assert any("basic structure" in error for error in result.critical_errors)


def test_report_lint_detects_llm_preamble_before_first_heading():
    result = lint_report(
        "以下严格按指令，仅基于给定证据列表生成日报。先输出候选事件筛选表。\n\n" + _good_report(),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert "LLM preamble leaked before first heading at line 1" in result.critical_errors
    assert result.passed is False


def test_report_lint_detects_empty_so_what_line():
    result = lint_report(
        _good_report("- **影响 / So what**:"),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert any("empty So what section" in error for error in result.critical_errors)
    assert result.passed is False


def test_report_lint_detects_non_daily_core_judgment_heading():
    result = lint_report(
        _good_report("#### **四、本周核心判断**\n- 不应出现在日报正式正文。"),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert any("non-daily core judgment heading" in error for error in result.critical_errors)
    assert result.passed is False


def test_report_lint_accepts_so_what_heading_with_numbered_body():
    result = lint_report(
        _good_report("- **影响 / So what**:\n  1. 这条解释承接上一行，不应按空段落处理。"),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert not any("empty So what section" in error for error in result.critical_errors)
    assert result.passed is True


def test_report_lint_detects_future_candidate_row_date():
    report = "\n".join(
        [
            "## 国内候选事件筛选表",
            "| 事件 | event_date | report_date | 是否入选 |",
            "|---|---|---|---|",
            "| Kimi高速版 | 2026-06-15 | 2026-06-15 | 是 |",
            "## 海外候选事件筛选表",
            "| 事件 | event_date | report_date | 是否入选 |",
            "|---|---|---|---|",
            "| Barret Zoph离开OpenAI | 2026-06-19 | 2026-06-19 | 否 |",
            "# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "## 输出前自我检查清单",
            "已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(
        report,
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
        target_date="2026-06-15",
    )

    assert any("candidate row has future date after target 2026-06-15" in error for error in result.critical_errors)
    assert result.passed is False


def test_report_lint_detects_candidate_table_after_formal_radar():
    report = "\n".join(
        [
            "## 国内候选事件筛选表",
            "候选表。",
            "# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "## 海外候选事件筛选表",
            "候选表。",
            "# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "## 输出前自我检查清单",
            "已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert any("candidate table appears after formal radar" in error for error in result.critical_errors)
    assert result.passed is False


def test_report_lint_detects_candidate_table_prose_after_rows():
    report = "\n".join(
        [
            "## 国内候选事件筛选表",
            "| 事件 | 是否入选 |",
            "|---|---|",
            "| 微信小微灰度上线 | 否 |",
            "",
            "用户提供的证据中，国内缺乏强一手数据事件，但该事件战略意义重大，破格入选。",
            "## 海外候选事件筛选表",
            "海外核心事件：不强行凑数。",
            "## 国内版正式雷达",
            "内容。",
            "## 海外版正式雷达",
            "内容。",
            "## 输出前自我检查清单",
            "已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert "candidate table has prose after rows at line 6" in result.critical_errors
    assert result.passed is False


def test_report_lint_detects_p3_candidate_rows():
    report = "\n".join(
        [
            "## 国内候选事件筛选表",
            "| 事件 | 初步优先级 | 是否入选 |",
            "|---|---|---|",
            "| 观察事件 | P3 | 否 |",
            "## 海外候选事件筛选表",
            "候选表。",
            "# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "## 输出前自我检查清单",
            "已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert "P3 row found in candidate table at line 4" in result.critical_errors
    assert result.passed is False


def test_report_lint_detects_report_url_not_in_evidence():
    result = lint_report(
        _good_report("参考：https://not-evidence.example.com/a"),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert result.passed is True
    assert "https://not-evidence.example.com/a" in " ".join(result.errors)


def test_report_lint_url_normalization_allows_equivalent_urls():
    result = lint_report(
        _good_report("参考：http://example.com/a/?utm_source=x#section"),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert result.errors == []


def test_report_lint_ignores_feishu_urls():
    result = lint_report(
        _good_report("飞书：https://example.feishu.cn/docx/abc"),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert result.errors == []


def test_report_lint_accepts_section_aliases():
    report = "\n".join(
        [
            "## 国内候选事件表",
            "今日无强核心事件",
            "## 海外候选事件表",
            "无足够证据进入核心",
            "## 国内版",
            "内容。",
            "## 海外版",
            "内容。",
            "## 自我检查清单",
            "已检查。",
        ]
    )

    result = lint_report(report + "\n来源：https://example.com/a", [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.errors == []
    assert result.critical_errors == []


def test_report_lint_does_not_warn_when_formal_radar_sections_exist():
    report = "\n".join(
        [
            "## 国内候选事件筛选表",
            "候选表。",
            "## 海外候选事件筛选表",
            "候选表。",
            "# AI 前沿能力与应用雷达 - 国内版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "# AI 前沿能力与应用雷达 - 海外版【2026年06月15日】",
            "## 一、今日总览",
            "内容。",
            "## 输出前自我检查清单",
            "- [x] 已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert "domestic core event section absent without no-forced-count explanation" not in result.warnings
    assert "overseas core event section absent without no-forced-count explanation" not in result.warnings


def test_report_lint_accepts_domestic_overseas_versioned_candidate_headings():
    report = "\n".join(
        [
            "#### 国内版候选事件筛选表",
            "今日无强核心事件",
            "#### 海外版候选事件筛选表",
            "无足够证据进入核心",
            "## 国内版",
            "内容。",
            "## 海外版",
            "内容。",
            "## 自我检查清单",
            "已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.errors == []
    assert result.critical_errors == []


def test_report_lint_accepts_domestic_overseas_radar_aliases():
    report = "\n".join(
        [
            "## 国内候选事件表",
            "今日无强核心事件",
            "## 海外候选事件表",
            "无足够证据进入核心",
            "## 国内核心判断",
            "内容。",
            "## 海外雷达",
            "内容。",
            "## 输出前自检",
            "已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.errors == []
    assert result.critical_errors == []


def test_report_lint_accepts_self_check_aliases():
    for title in ("输出前自检", "自检清单", "检查清单", "自我校验", "self check", "checklist"):
        report = _good_report().replace("输出前自我检查清单", title)
        result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

        assert not any("self_check" in error for error in result.errors)
        assert not any("self_check" in warning for warning in result.warnings)


def test_report_lint_accepts_checkbox_self_check():
    report = _good_report().replace(
        "## 输出前自我检查清单\n已检查。",
        "## 质量复核\n- [x] 日期窗口正确\n- [ ] URL 已检查\n✅ 来源已核验",
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert not any("self_check" in error for error in result.errors)
    assert not any("self_check" in warning for warning in result.warnings)


def test_report_lint_missing_only_self_check_is_warning():
    report = _good_report().replace("## 输出前自我检查清单\n已检查。\n", "")

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.passed is True
    assert result.errors == []
    assert "missing required section: self_check" in result.warnings


def test_report_lint_no_forced_count_aliases_avoid_warning():
    report = _good_report().replace("国内核心事件：不强行凑数。", "未发现足够强事件。").replace(
        "海外核心事件：不强行凑数。", "本期无入选核心。"
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.warnings == []


def test_report_lint_warns_when_formal_radar_has_more_than_six_events():
    rows = "\n".join(f"| 海外事件{i} | P2 | L3 | 来源：https://example.com/a |" for i in range(1, 8))
    report = "\n".join(
        [
            "## 国内候选事件筛选表",
            "国内核心事件：不强行凑数。",
            "## 海外候选事件筛选表",
            "海外核心事件：不强行凑数。",
            "## 国内版正式雷达",
            "今日无强核心事件，不强行凑数。",
            "## 海外版正式雷达",
            "### 今日总览",
            "| 事件 | 优先级 | 层级 | 来源 |",
            "| --- | --- | --- | --- |",
            rows,
            "## 输出前自我检查清单",
            "已检查。",
            "来源：https://example.com/a",
        ]
    )

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.passed is True
    assert "formal radar has more than 6 core events; capped for brief/card" in result.warnings


def test_report_lint_placeholder_is_critical():
    result = lint_report(_good_report("TBD"), [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.passed is False
    assert result.critical_errors


def test_report_lint_detects_no_source_url_as_critical():
    result = lint_report(
        _good_report().replace("来源：https://example.com/a", ""),
        [EvidenceItem(title="A", url="https://example.com/a", content="A")],
    )

    assert result.passed is True
    assert "report body had no source URL; evidence source appendix appended" in result.warnings
    assert result.source_url_count == 0


def test_report_lint_source_appendix_counts_as_source_urls():
    report = _good_report().replace("来源：https://example.com/a", "")
    report += "\n\n## 附录：本次证据来源索引\n\n- [E1] [A](https://example.com/a) — Example\n"

    result = lint_report(report, [EvidenceItem(title="A", url="https://example.com/a", content="A")])

    assert result.passed is True
    assert result.source_appendix_present is True
    assert result.source_url_count == 1
    assert "report has no source URL" not in result.critical_errors


def test_report_lint_detects_zero_evidence_as_critical():
    result = lint_report(_good_report(), [])

    assert result.passed is False
    assert "evidence_count is 0" in result.critical_errors
