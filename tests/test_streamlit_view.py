import pytest

import streamlit_app
from backend.app.streamlit_view import (
    company_report_summary,
    company_table_rows,
    module_detail,
    module_cards,
    module_score_rows,
    pop_route_history,
    push_route_history,
    reason_items,
    route_snapshot,
    score_band,
)


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
    assert {"指标": "Altman Z", "数值": "3.20", "得分": "10.0 / 10.0"} in detail["rows"]
    assert {"指标": "资产负债率", "数值": "50.0%", "得分": "10.0 / 10.0"} in detail["rows"]
    assert all(row["指标"] != "ROI" for row in detail["rows"])
    assert detail["notes"] == ["资产负债率偏高"]


def test_financial_metric_card_rows_use_roe_not_roi():
    rows = streamlit_app.metric_card_rows("财务证据", sample_company()["financials"])

    assert ("ROE", "-1.2%", -1.2) in rows
    assert all(row[0] != "ROI" for row in rows)


def test_module_detail_builds_equity_audit_rows():
    detail = module_detail(sample_company(), "equity")

    assert detail["title"] == "治理合规资质二级页"
    assert {"指标": "股权结构", "数值": "4.5/5", "得分": "4.5 / 5.0"} in detail["rows"]
    assert {"指标": "审计意见", "数值": "5/5", "得分": "5.0 / 5.0"} in detail["rows"]
    assert len(detail["rows"]) == 5


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
