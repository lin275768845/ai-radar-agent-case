from ai_radar_agent.llm import build_evidence_context
from ai_radar_agent.models import EvidenceItem


def test_build_evidence_context_keeps_not_core_candidates_in_forbidden_section_and_preserves_ids():
    weak = EvidenceItem(title="阿里千问高考志愿填报Agent", url="https://www.php.cn/faq/1", content="S4转载", source="php中文网")
    weak.not_core_eligible = True
    strong = EvidenceItem(title="NVIDIA官方发布", url="https://blogs.nvidia.com/blog/a", content="S1官方", source="NVIDIA Blog")

    context = build_evidence_context([weak, strong])

    assert "## 仅候选/观察证据（禁止入选正式雷达）" in context
    assert "阿里千问高考志愿填报Agent" in context
    assert "[E2] 标题：NVIDIA官方发布" in context
    assert "[E1] 标题：阿里千问高考志愿填报Agent" in context
    assert "已从主报告 LLM 输入排除 not_core_eligible 证据：1 条" in context


def test_build_evidence_context_adds_ranked_core_candidate_section():
    weak = EvidenceItem(
        title="聚合站转述AI工具更新",
        url="https://example.com/weak",
        content="普通聚合转载",
        source="聚合站",
        region_hint="domestic",
    )
    weak.source_tier = "S4"
    weak.source_fit = "medium"
    weak.date_status = "in_window"

    medium = EvidenceItem(
        title="腾讯元宝上线企业效率Agent",
        url="https://example.com/tencent-agent",
        content="腾讯 AI Agent 企业工作流场景上线",
        source="第一财经",
        region_hint="domestic",
    )
    medium.source_tier = "S2"
    medium.source_fit = "medium"
    medium.date_status = "in_window"

    strong = EvidenceItem(
        title="阿里发布新模型并披露调用量",
        url="https://example.com/ali-model",
        content="官方发布模型升级，披露 token 调用量和企业客户 adoption signal",
        source="阿里云官方",
        region_hint="domestic",
    )
    strong.source_tier = "S1"
    strong.source_fit = "high"
    strong.date_status = "in_window"
    strong.is_primary_source = True

    context = build_evidence_context([weak, medium, strong])
    recommended = context.split("[E1] 标题", 1)[0]

    assert "## 推荐核心候选（确定性预筛）" in recommended
    assert "正式雷达 Top 应优先从这里选择" in recommended
    assert "聚合站转述AI工具更新" not in recommended
    assert "E3" in recommended
    assert "E2" in recommended
    assert recommended.index("E3") < recommended.index("E2")
