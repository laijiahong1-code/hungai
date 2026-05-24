import json

import pytest

import streamlit_app
from backend.app.streamlit_view import (
    company_report_summary,
    company_table_rows,
    module_detail,
    module_cards,
    module_score_rows,
    potential_level_rows,
    pop_route_history,
    push_route_history,
    reason_items,
    route_snapshot,
    scoring_rule_sections,
    score_band,
)


FINANCE_RADAR_LABELS = [
    "Altman Z",
    "资产负债率",
    "经营现金流/收入",
    "净利润三年CAGR",
    "连续分红年数",
    "有息负债占比",
]


def sample_company():
    return {
        "code": "600001",
        "stock_code": "600001",
        "shortName": "甲能源",
        "name": "甲能源集团股份有限公司",
        "province": "江西省",
        "industry": "能源",
        "stateAttribute": "国有控股",
        "score": 82.4,
        "totalScore": 82.4,
        "modules": {"finance": 72.0, "equity": 81.0, "region": 90.0, "mixed": 86.0},
        "module_details": {
            "finance": {
                "evidence": [
                    {"label": "Altman Z", "value": "3.20", "score": 10.0, "max": 10.0},
                    {"label": "资产负债率", "value": "50.0%", "score": 10.0, "max": 10.0},
                    {"label": "经营现金流/收入", "value": "18.5%", "score": 10.0, "max": 10.0},
                    {"label": "净利润三年CAGR", "value": "69.2%", "score": 10.0, "max": 10.0},
                    {"label": "连续分红年数", "value": "3 年", "score": 5.0, "max": 5.0},
                    {"label": "有息负债占比", "value": "23.1%", "score": 3.8, "max": 5.0},
                ]
            },
            "equity": {
                "evidence": [
                    {"label": "股权结构", "value": "4.5/5", "score": 4.5, "max": 5.0},
                    {"label": "股权质押", "value": "5/5", "score": 5.0, "max": 5.0},
                    {"label": "审计意见", "value": "5/5", "score": 5.0, "max": 5.0},
                    {"label": "合规记录", "value": "5/5", "score": 5.0, "max": 5.0},
                    {"label": "行业地位", "value": "5/5", "score": 5.0, "max": 5.0},
                ]
            },
            "region": {
                "evidence": [
                    {"label": "财政自给率", "value": "100.0%", "score": 8.0, "max": 8.0},
                ]
            },
            "mixed": {
                "evidence": [
                    {"label": "非国有资本进入程度", "value": "30.0/30", "score": 30.0, "max": 30.0},
                ]
            },
        },
        "financials": {
            "revenue": 120.5,
            "netProfit": -3.2,
            "assetLiabilityRatio": 74.5,
            "roe": -1.2,
            "roi": 2.7,
            "cashFlow": 5.6,
        },
        "equity": {
            "topShareholderRatio": 40,
            "pledgeRatio": 12,
            "auditOpinion": "标准无保留意见",
            "auditAccountingDate": "2024-12-31",
            "auditDate": "2025-03-20",
            "auditor": "张三,李四",
            "domesticAuditFirm": "样本会计师事务所",
            "overdueDebt": "无逾期",
        },
        "highlights": ["区域政策匹配"],
        "risks": ["资产负债率偏高"],
        "governanceTrend": [
            {"year": 2023, "score": 72.0, "rawScore": 18.0, "date": "2023-12-31"},
            {"year": 2024, "score": 80.0, "rawScore": 20.0, "date": "2024-12-31"},
            {"year": 2025, "score": 85.0, "rawScore": 21.25, "date": "2025-09-30"},
        ],
        "mixedDegreeProfile": {
            "score": 86.1,
            "level": "高度融合混改",
            "scoreItems": [
                {
                    "label": "非国有资本进入程度",
                    "score": 29.8,
                    "max": 30,
                    "percent": 99.3,
                    "description": "非国有资本参与充分",
                }
            ],
            "structureMetrics": {
                "nonStateRatio": 55.0,
                "diversity": 4,
                "ownershipConcentration": 66.0,
            },
            "shareholders": [
                {
                    "rank": 1,
                    "name": "广东德赛集团有限公司",
                    "ratio": 28.31,
                    "nature": "国有法人",
                    "holderGroupLabel": "国资相关",
                }
            ],
            "holderGroups": [
                {"label": "国资相关", "ratio": 28.31, "percentage": 55.77, "color": "#2563eb"},
                {"label": "市场化股东", "ratio": 5.58, "percentage": 10.99, "color": "#0faaa5"},
                {"label": "机构/互联互通", "ratio": 1.56, "percentage": 3.08, "color": "#7c5ce7"},
                {"label": "其他市场主体", "ratio": 15.31, "percentage": 30.16, "color": "#fb5a1e"},
            ],
            "structureNotes": ["前十大股东持股集中度较高，股权结构整体较稳定。"],
            "signalTags": ["国资参与", "股东多元", "市场化参与", "结构稳定"],
        },
    }


def test_company_table_rows_keep_streamlit_table_fields_small():
    rows = company_table_rows([sample_company()])

    assert rows == [
        {
            "排名": 1,
            "代码": "600001",
            "公司简称": "甲能源",
            "省份": "江西省",
            "行业": "能源",
            "总分": 82.4,
        }
    ]


def test_module_score_rows_include_labels_weights_and_scores():
    rows = module_score_rows(sample_company())

    assert rows[0] == {"模块": "财务引资潜力", "权重": "40%", "得分": 72.0}
    assert rows[-1] == {"模块": "混改程度评分", "权重": "15%", "得分": 86.0}


def test_score_band_maps_scores_to_report_statuses():
    assert score_band(85)["label"] == "优势项"
    assert score_band(75)["label"] == "支撑项"
    assert score_band(65)["label"] == "观察项"
    assert score_band(55)["label"] == "风险项"


def test_company_report_summary_names_best_and_weakest_modules():
    summary = company_report_summary(sample_company())

    assert "甲能源综合得分82.4" in summary
    assert "优势项" in summary
    assert "区域国资适配贡献最强" in summary
    assert "财务引资潜力仍需重点观察" in summary


def test_module_cards_include_status_and_explanatory_copy():
    cards = module_cards(sample_company())

    assert len(cards) == 4
    assert cards[0]["key"] == "finance"
    assert cards[0]["band_label"] == "支撑项"
    assert "Altman Z、债务结构、现金盈利与分红" in cards[0]["summary"]
    assert cards[2]["key"] == "region"
    assert cards[2]["band_label"] == "优势项"


def test_reason_items_returns_empty_fallback():
    assert reason_items([], "暂无风险提示") == ["暂无风险提示"]


def test_module_detail_builds_finance_secondary_page_model():
    detail = module_detail(sample_company(), "finance")

    assert detail["title"] == "财务引资潜力二级页"
    assert detail["score"] == 72.0
    assert detail["weight"] == "40%"
    assert detail["band_label"] == "支撑项"
    assert "财务引资潜力得分72.0" in detail["report_summary"]
    assert "Altman Z、债务结构、现金盈利与分红" in detail["report_summary"]
    assert [row["指标"] for row in detail["rows"]] == FINANCE_RADAR_LABELS
    assert {"指标": "Altman Z", "数值": "3.20", "得分": "10.0 / 10.0"} in detail["rows"]
    assert {"指标": "资产负债率", "数值": "50.0%", "得分": "10.0 / 10.0"} in detail["rows"]
    assert {"指标": "经营现金流/收入", "数值": "18.5%", "得分": "10.0 / 10.0"} in detail["rows"]
    assert {"指标": "净利润三年CAGR", "数值": "69.2%", "得分": "10.0 / 10.0"} in detail["rows"]
    assert {"指标": "连续分红年数", "数值": "3 年", "得分": "5.0 / 5.0"} in detail["rows"]
    assert {"指标": "有息负债占比", "数值": "23.1%", "得分": "3.8 / 5.0"} in detail["rows"]
    assert all(row["指标"] != "ROI" for row in detail["rows"])
    assert detail["notes"] == ["资产负债率偏高"]


def test_finance_radar_chart_html_uses_six_metric_contract():
    helper = getattr(streamlit_app, "finance_radar_chart_html", None)
    detail = module_detail(sample_company(), "finance")

    assert helper is not None
    html = helper(detail["rows"])

    assert "finance-radar-card" in html
    assert 'role="img"' in html
    assert "财务引资潜力雷达图" in html
    assert "综合完成度" in html
    assert "96.0%" in html
    assert "关联说明与信号" not in html
    for label in FINANCE_RADAR_LABELS:
        assert label in html


def test_finance_radar_chart_html_keeps_missing_metrics_visible():
    helper = getattr(streamlit_app, "finance_radar_chart_html", None)

    assert helper is not None
    html = helper([{"指标": "Altman Z", "数值": "3.20", "得分": "10.0 / 10.0"}])

    assert "Altman Z" in html
    assert "有息负债占比" in html
    assert "无数据" in html


def test_mixed_module_detail_exposes_profile_and_page_html():
    detail = module_detail(sample_company(), "mixed")
    html = streamlit_app.mixed_module_detail_html(detail)

    assert detail["mixedDegreeProfile"]["score"] == 86.1
    assert "指标拆解与得分依据" in html
    assert "主要股东结构名单" in html
    assert "股东类别占比" in html
    assert "自动结构解读" in html
    assert "自动混改信号标签" in html
    assert "广东德赛集团有限公司" in html


def test_mixed_shareholder_table_uses_compact_scroll_contract():
    detail = module_detail(sample_company(), "mixed")
    html = streamlit_app.mixed_module_detail_html(detail)

    assert 'class="mixed-table-scroll mixed-shareholder-scroll"' in html
    assert 'class="mixed-shareholder-col-rank"' in html
    assert 'class="mixed-shareholder-col-name"' in html
    assert 'class="mixed-shareholder-col-ratio"' in html
    assert 'class="mixed-shareholder-col-nature"' in html
    assert 'class="mixed-shareholder-col-category"' in html


def test_mixed_shareholder_row_keeps_full_name_in_cell_and_title():
    long_name = "中信建投证券-信邦通远(上海)投资管理有限公司-中信建投长期价值集合资产管理计划"
    html = streamlit_app.mixed_shareholder_row_html(
        {
            "rank": 8,
            "name": long_name,
            "ratio": 2.2,
            "nature": "机构账户 / 互联互通",
            "holderGroupLabel": "机构 / 市场化",
        }
    )

    assert f'title="{long_name}"' in html
    assert f'<span class="mixed-holder-name" title="{long_name}">' in html
    assert f'<span class="mixed-holder-name-text">{long_name}</span>' in html


def test_mixed_score_rows_use_distinct_reference_style_icons():
    labels_and_icons = [
        ("非国有资本进入程度", "capital"),
        ("股权结构多样性", "diversity"),
        ("股权制衡程度", "balance"),
        ("股权融合程度", "integration"),
        ("股权开放治理程度", "governance"),
    ]

    for label, icon in labels_and_icons:
        html = streamlit_app.mixed_score_progress_row_html({"label": label, "percent": 80, "score": 8, "max": 10})

        assert f"mixed-score-icon-{icon}" in html
        assert '<svg class="mixed-score-symbol"' in html


def test_mixed_module_detail_html_handles_missing_profile():
    detail = module_detail({**sample_company(), "mixedDegreeProfile": {}}, "mixed")
    html = streamlit_app.mixed_module_detail_html(detail)

    assert "暂无混改结构明细" in html
    assert "基础指标证据" in html


def test_financial_metric_card_rows_use_roe_not_roi():
    rows = streamlit_app.metric_card_rows("财务证据", sample_company()["financials"])

    assert ("ROE", "-1.2%", -1.2) in rows
    assert all(row[0] != "ROI" for row in rows)


def test_equity_metric_card_rows_include_top_shareholder_name_and_ratio():
    company = sample_company()
    company["equity"]["topShareholderName"] = "深圳市地铁集团有限公司"
    company["equity"]["topShareholderRatio"] = 27.18

    rows = streamlit_app.metric_card_rows("股权与信用", company["equity"])

    assert ("第一大股东", "深圳市地铁集团有限公司", "深圳市地铁集团有限公司") in rows
    assert ("第一大股东持股", "27.18%", 27.18) in rows


def test_data_source_label_uses_streamlit_secret_mongodb_uri(monkeypatch):
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.setattr(
        streamlit_app,
        "get_setting",
        lambda name, default="": "mongodb+srv://secret" if name == "MONGODB_URI" else default,
        raising=False,
    )

    assert streamlit_app.data_source_label() == "MongoDB 云端"


def test_reform_status_cards_html_contains_company_profile_labels():
    company = sample_company()
    company["reformProfile"] = {
        "isStateOwned": True,
        "stateOwnedLabel": "是",
        "mixedStatusLabel": "正在进行混改",
        "source": "status_csv",
    }

    html = streamlit_app.reform_status_cards_html(company)

    assert 'class="reform-status-stack"' in html
    assert 'class="reform-info-card status-progress"' in html
    assert "企业状态" in html
    assert "混改状态" in html
    assert ">国企<" in html
    assert "正在进行混改" in html
    assert "是否国企" not in html
    assert "是否混改" not in html


def test_reform_status_cards_html_maps_private_company_copy():
    company = sample_company()
    company["reformProfile"] = {
        "isStateOwned": False,
        "stateOwnedLabel": "否",
        "mixedStatusLabel": "潜在混改企业",
        "source": "private_score_threshold",
    }

    html = streamlit_app.reform_status_cards_html(company)

    assert 'class="reform-info-card status-potential"' in html
    assert "企业状态" in html
    assert ">非国企<" in html
    assert "混改状态" in html
    assert "潜在混改企业" in html


def test_hero_signal_panel_groups_status_cards_with_score_card():
    company = sample_company()
    company["reformProfile"] = {
        "isStateOwned": True,
        "stateOwnedLabel": "是",
        "mixedStatusLabel": "正在进行混改",
        "source": "status_csv",
    }

    html = streamlit_app.hero_signal_panel_html(company, 87.7, score_band(87.7))

    assert 'class="hero-signal-panel"' in html
    assert 'class="reform-status-stack"' in html
    assert 'class="score-panel report-score-panel"' in html
    assert "企业状态" in html
    assert "混改状态" in html
    assert "87.7" in html


def test_module_detail_builds_equity_audit_rows():
    detail = module_detail(sample_company(), "equity")

    assert detail["title"] == "治理合规资质二级页"
    assert {"指标": "股权结构", "数值": "4.5/5", "得分": "4.5 / 5.0"} in detail["rows"]
    assert {"指标": "审计意见", "数值": "5/5", "得分": "5.0 / 5.0"} in detail["rows"]
    assert len(detail["rows"]) == 5
    assert detail["governanceTrend"][-1] == {"year": 2025, "score": 85.0, "rawScore": 21.25, "date": "2025-09-30"}


def test_governance_radar_chart_html_uses_five_metric_contract():
    detail = module_detail(sample_company(), "equity")
    html = streamlit_app.governance_radar_chart_html(detail["rows"])

    assert "governance-radar-card" in html
    assert 'role="img"' in html
    assert "治理能力雷达图" in html
    assert "能力模型" in html
    assert "质押风险" in html
    assert "审计质量" in html
    assert "合规水平" in html
    assert "关联说明与信号" not in html


def test_governance_trend_chart_html_uses_three_year_scores():
    detail = module_detail(sample_company(), "equity")
    html = streamlit_app.governance_trend_chart_html(detail["governanceTrend"])

    assert "governance-trend-chart" in html
    assert 'role="img"' in html
    assert "2023年" in html
    assert "2024年" in html
    assert "2025年" in html
    assert "85/100" in html
    assert "72/100" in html


def test_governance_trend_chart_html_handles_missing_data():
    html = streamlit_app.governance_trend_chart_html([])

    assert "暂无治理合规趋势数据" in html


def test_governance_highlights_use_qwen_when_configured(monkeypatch):
    detail = module_detail(sample_company(), "equity")
    monkeypatch.setattr(
        streamlit_app,
        "get_setting",
        lambda name, default="": {
            "QWEN_API_KEY": "secret",
            "QWEN_HIGHLIGHTS_ENABLED": "1",
        }.get(name, default),
        raising=False,
    )
    monkeypatch.setattr(
        streamlit_app,
        "_request_qwen_governance_highlights",
        lambda detail: ["模型判断：审计意见稳定，合规记录清晰。"],
        raising=False,
    )

    html = streamlit_app.governance_highlights_html(detail)

    assert "模型判断：审计意见稳定，合规记录清晰。" in html
    assert "Qwen生成" in html
    assert "规则生成" not in html


def test_qwen_governance_highlights_request_uses_nvidia_chat_completions(monkeypatch):
    detail = module_detail(sample_company(), "equity")
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return json.dumps(
                {
                    "choices": [
                        {
                            "message": {
                                "content": "治理基础稳定\n审计质量良好",
                            }
                        }
                    ]
                }
            ).encode("utf-8")

    def fake_urlopen(api_request, timeout):
        captured["request"] = api_request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(
        streamlit_app,
        "get_setting",
        lambda name, default="": {
            "QWEN_API_KEY": "qwen-secret",
            "QWEN_BASE_URL": "https://integrate.api.nvidia.com/v1",
            "QWEN_MODEL": "qwen/qwen3-next-80b-a3b-instruct",
            "QWEN_TIMEOUT_SECONDS": "7",
        }.get(name, default),
        raising=False,
    )
    monkeypatch.setattr(streamlit_app.request, "urlopen", fake_urlopen)
    if hasattr(streamlit_app, "QWEN_HIGHLIGHT_CACHE"):
        streamlit_app.QWEN_HIGHLIGHT_CACHE.clear()

    items = streamlit_app._request_qwen_governance_highlights(detail)

    payload = json.loads(captured["request"].data.decode("utf-8"))
    assert captured["request"].full_url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert captured["request"].get_header("Authorization") == "Bearer qwen-secret"
    assert captured["timeout"] == 7.0
    assert payload["model"] == "qwen/qwen3-next-80b-a3b-instruct"
    assert payload["stream"] is False
    assert items == ["治理基础稳定", "审计质量良好"]


def test_governance_highlights_fall_back_without_qwen_key(monkeypatch):
    detail = module_detail(sample_company(), "equity")
    monkeypatch.setattr(streamlit_app, "get_setting", lambda name, default="": default, raising=False)

    html = streamlit_app.governance_highlights_html(detail)

    assert "规则生成" in html
    assert "质押风险可控" in html
    assert "治理合规得分连续改善" in html


def test_module_detail_equity_fallback_includes_top_shareholder_name():
    company = sample_company()
    company["module_details"]["equity"]["evidence"] = []
    company["equity"]["topShareholderName"] = "深圳市地铁集团有限公司"
    company["equity"]["topShareholderRatio"] = 27.18

    detail = module_detail(company, "equity")

    assert {"指标": "第一大股东", "数值": "深圳市地铁集团有限公司"} in detail["rows"]
    assert {"指标": "第一大股东持股", "数值": "27.18%"} in detail["rows"]


def test_module_detail_rejects_unknown_module():
    with pytest.raises(KeyError):
        module_detail(sample_company(), "unknown")


def test_route_history_pushes_current_route_before_navigation():
    current = {
        "page": "company",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "finance",
    }
    next_route = {**current, "page": "module", "selected_module": "equity"}

    history = push_route_history([], current, next_route)

    assert history == [current]


def test_route_history_does_not_duplicate_same_route():
    current = {
        "page": "company",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "finance",
    }

    history = push_route_history([], current, current.copy())

    assert history == []


def test_route_history_pops_previous_route():
    first = {"page": "home", "selected_company_code": "", "selected_province": "", "selected_module": "finance"}
    second = {"page": "company", "selected_company_code": "600001", "selected_province": "江西省", "selected_module": "finance"}

    previous, remaining = pop_route_history([first, second])

    assert previous == second
    assert remaining == [first]


def test_route_snapshot_keeps_only_navigation_keys():
    state = {
        "page": "module",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "mixed",
        "other": "ignore",
    }

    assert route_snapshot(state) == {
        "page": "module",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "mixed",
    }


def test_navigation_control_labels_only_show_single_back_button_off_home():
    helper = getattr(streamlit_app, "navigation_control_labels", None)

    assert helper is not None
    assert helper("home") == []
    assert helper("company") == ["返回"]
    assert "返回上一页" not in helper("company")
    assert "回到首页" not in helper("company")


def test_back_navigation_resolves_stack_and_empty_history_fallback():
    helper = getattr(streamlit_app, "resolve_back_navigation", None)
    home = {"page": "home", "selected_company_code": "", "selected_province": "", "selected_module": "finance"}
    province = {"page": "province", "selected_company_code": "", "selected_province": "江西省", "selected_module": "finance"}
    company = {
        "page": "company",
        "selected_company_code": "600001",
        "selected_province": "江西省",
        "selected_module": "finance",
    }
    module = {**company, "page": "module", "selected_module": "equity"}

    assert helper is not None
    previous, remaining = helper(module, [home, province, company])
    assert previous == company
    assert remaining == [home, province]

    previous, remaining = helper(company, [home])
    assert previous == home
    assert remaining == []

    previous, remaining = helper(company, [])
    assert previous["page"] == "home"
    assert remaining == []


def test_company_breadcrumb_text_omits_home_segment():
    helper = getattr(streamlit_app, "company_breadcrumb_text", None)

    assert helper is not None
    breadcrumb = helper(sample_company())
    assert breadcrumb == "江西省 / 600001"
    assert "首页" not in breadcrumb


def test_sidebar_home_navigation_clears_history():
    helper = getattr(streamlit_app, "sidebar_navigation_clears_history", None)

    assert helper is not None
    assert helper("home") is True
    assert helper("company") is False


def test_method_route_is_labeled_as_scoring_rules():
    assert streamlit_app.route_label({"page": "method"}) == "评分规则"


def test_scoring_rule_sections_match_four_module_contract():
    sections = scoring_rule_sections()

    assert [section["key"] for section in sections] == ["finance", "equity", "region", "mixed"]
    assert [section["weight"] for section in sections] == ["40%", "25%", "20%", "15%"]
    assert [section["raw_max"] for section in sections] == ["50", "25", "20", "100"]
    assert sections[0]["items"][0] == "Altman Z"
    assert "股权开放治理程度" in sections[-1]["items"]


def test_potential_level_rows_describe_all_score_bands():
    rows = potential_level_rows()

    assert rows == [
        {"分数区间": ">=80", "潜力等级": "高潜力"},
        {"分数区间": ">=70", "潜力等级": "中高潜力"},
        {"分数区间": ">=60", "潜力等级": "观察潜力"},
        {"分数区间": "<60", "潜力等级": "低潜力"},
    ]


def test_page_from_query_params_only_accepts_method_page():
    helper = getattr(streamlit_app, "page_from_query_params", None)

    assert helper is not None
    assert helper({"page": "method"}) == "method"
    assert helper({"page": ["method"]}) == "method"
    assert helper({"page": "home"}) is None
    assert helper({"page": "company"}) is None
    assert helper({}) is None


def test_rule_weight_stack_html_makes_module_weights_scannable():
    helper = getattr(streamlit_app, "rule_weight_stack_html", None)

    assert helper is not None
    html = helper(scoring_rule_sections())
    assert 'class="rule-weight-stack"' in html
    assert 'class="rule-weight-fill rule-tone-finance" style="width:40%;"' in html
    assert 'class="rule-weight-fill rule-tone-equity" style="width:25%;"' in html
    assert "财务引资潜力" in html
    assert "40%" in html


def test_rule_module_card_html_emphasizes_weight_and_visual_tone():
    helper = getattr(streamlit_app, "rule_module_card_html", None)

    assert helper is not None
    card = helper(scoring_rule_sections()[0])
    assert 'class="rule-module-card rule-tone-finance"' in card
    assert 'data-uniform-height="true"' in card
    assert 'class="rule-weight-number">40%</div>' in card
    assert 'class="rule-weight-fill rule-tone-finance" style="width:40%;"' in card
    assert "原始满分 50" in card
    assert "Altman Z" in card


def test_potential_level_grid_html_is_compact_and_not_markdown_code():
    helper = getattr(streamlit_app, "potential_level_grid_html", None)

    assert helper is not None
    html = helper(potential_level_rows())
    assert html.startswith('<div class="level-grid">')
    assert html.endswith("</div>")
    assert "\n" not in html
    assert html.count('class="level-item"') == 4
    assert "高潜力" in html
    assert "80-100" in html
