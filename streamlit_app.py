from __future__ import annotations

import html
import json
import math
import re
from typing import Any
from urllib import request

import streamlit as st

from backend.app.data import get_setting
from backend.app.mixed_status import load_status_dashboard
from backend.app.services import (
    ensure_top_shareholder_collection_seeded,
    get_all_provinces,
    get_company_detail,
    get_province_companies,
    get_top_companies,
    search_entities,
)
from backend.app.streamlit_view import (
    MODULE_LABELS,
    MODULE_META,
    company_report_summary,
    company_table_rows,
    module_detail,
    module_cards,
    potential_level_rows,
    reason_items,
    pop_route_history,
    push_route_history,
    route_snapshot,
    scoring_rule_sections,
    score_band,
)


DEFAULT_URLOPEN = request.urlopen


st.set_page_config(
    page_title="国企混改潜力评分系统",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(ttl=300, show_spinner=False)
def cached_top_companies(limit: int = 10) -> list[dict]:
    return get_top_companies(limit=limit)


@st.cache_data(ttl=300, show_spinner=False)
def cached_provinces() -> list[str]:
    return get_all_provinces()


@st.cache_data(ttl=300, show_spinner=False)
def cached_province_companies(province: str) -> list[dict]:
    return get_province_companies(province)


@st.cache_data(ttl=300, show_spinner=False)
def cached_company_detail(code: str) -> dict:
    return get_company_detail(code)


@st.cache_data(ttl=120, show_spinner=False)
def cached_search(query: str) -> dict:
    return search_entities(query)


@st.cache_data(ttl=300, show_spinner=False)
def cached_mixed_status_dashboard() -> dict[str, Any]:
    return load_status_dashboard()


@st.cache_data(ttl=3600, show_spinner=False)
def cached_top_shareholder_seed() -> bool:
    return ensure_top_shareholder_collection_seeded()


def main() -> None:
    ensure_state()
    apply_page_query_params()
    inject_css()
    cached_top_shareholder_seed()
    render_top_bar()
    render_navigation_controls()
    render_sidebar()

    page = st.session_state["page"]
    if page == "home":
        render_home()
    elif page == "search":
        render_search_page()
    elif page == "province":
        render_province_page()
    elif page == "company":
        render_company_page()
    elif page == "module":
        render_module_page()
    elif page == "validation":
        render_model_validation_page()
    else:
        render_method_page()


def ensure_state() -> None:
    st.session_state.setdefault("page", "home")
    st.session_state.setdefault("selected_company_code", "600004")
    st.session_state.setdefault("selected_province", "")
    st.session_state.setdefault("selected_module", "finance")
    st.session_state.setdefault("nav_history", [])


def page_from_query_params(params: Any) -> str | None:
    try:
        raw_page = params.get("page")
    except AttributeError:
        return None
    if isinstance(raw_page, list):
        raw_page = raw_page[0] if raw_page else None
    if raw_page in {"method", "validation"}:
        return str(raw_page)
    return None


def apply_page_query_params() -> None:
    query_page = page_from_query_params(st.query_params)
    if query_page:
        st.session_state["page"] = query_page


def clear_page_query_params() -> None:
    if "page" not in st.query_params:
        return
    try:
        del st.query_params["page"]
    except Exception:
        st.query_params.clear()


def navigate(page: str, remember: bool = True, **values: Any) -> None:
    clear_page_query_params()
    current_route = route_snapshot(st.session_state)
    next_route = {**current_route, "page": page, **values}
    if remember:
        st.session_state["nav_history"] = push_route_history(
            st.session_state.get("nav_history", []),
            current_route,
            next_route,
        )
    st.session_state["page"] = page
    for key, value in values.items():
        st.session_state[key] = value
    st.rerun()


def go_back() -> None:
    clear_page_query_params()
    previous, remaining = resolve_back_navigation(
        route_snapshot(st.session_state),
        st.session_state.get("nav_history", []),
    )
    st.session_state["nav_history"] = remaining
    for key, value in previous.items():
        st.session_state[key] = value
    st.rerun()


def go_home() -> None:
    st.session_state["nav_history"] = []
    navigate("home", remember=False)


def navigation_control_labels(page: str) -> list[str]:
    if page == "home":
        return []
    return ["返回"]


def resolve_back_navigation(current_route: dict, history: list[dict]) -> tuple[dict, list[dict]]:
    previous, remaining = pop_route_history(history)
    if previous is not None:
        return previous, remaining
    return {**route_snapshot(current_route), "page": "home"}, []


def sidebar_navigation_clears_history(page: str) -> bool:
    return page == "home"


def company_breadcrumb_text(company: dict) -> str:
    parts = [
        company.get("province"),
        company.get("code") or company.get("stock_code"),
    ]
    return " / ".join(str(part) for part in parts if part)


def h(value: Any) -> str:
    return html.escape(str(value if value is not None else ""))


MODEL_VALIDATION_CASES = [
    {
        "name": "登康口腔",
        "code": "001328",
        "headline": "重庆国资内部调整",
        "period_label": "混改前后对照",
        "start_year": 2023,
        "end_year": 2025,
        "start_label": "2023 混改前评分",
        "end_label": "2025 混改后评分",
        "start_score": "64.995",
        "end_score": "51.89",
        "time": "2025年1月2日签署托管协议；2025年2月28日推进轻纺集团股权无偿划转；2025年4月17日披露反垄断审查进展。",
        "content": "控股股东上层股权结构调整：轻纺集团由重庆机电控股托管，并进一步由机电集团直接持有轻纺集团100%股权。",
        "type": "同一实控体系内托管与无偿划转",
        "explanation": "评分下降说明经历一次国资内部调整后，公司未来新增混改空间下降；但分数仍处观察合理区间，表明财务状况和公司治理未出现大的不良扰动。",
        "source": "巨潮资讯网2025年公告",
        "source_links": [
            {
                "label": "托管协议公告",
                "url": "https://static.cninfo.com.cn/finalpage/2025-01-04/1222224507.PDF",
            },
            {
                "label": "无偿划转公告",
                "url": "https://file.finance.sina.com.cn/211.154.219.97%3A9494/MRGG/CNSESZ_STOCK/2025/2025-3/2025-03-01/10765652.PDF",
            },
            {
                "label": "反垄断审查进展公告",
                "url": "https://static.cninfo.com.cn/finalpage/2025-04-18/1223123703.PDF",
            },
        ],
    },
    {
        "name": "云南白药",
        "code": "000538",
        "headline": "完成混改后的持续优化",
        "period_label": "混改后持续观察",
        "start_year": 2023,
        "end_year": 2025,
        "start_label": "2023 持续优化初期",
        "end_label": "2025 持续优化后",
        "start_score": "51.415",
        "end_score": "64.997",
        "time": "主要混合所有制改革发生在2017年；2023--2025年属于混改完成后的持续优化阶段。",
        "content": "观察混改完成后公司治理、经营质量和财务稳定性的延续变化，而非单次控制权变动。",
        "type": "已完成混改后的长期稳定发展样本",
        "explanation": "评分上升说明在长期稳定运行后，公司后续混改潜力随时间逐步增加，也反映其财务状态和治理状态稳步提高。",
        "source": "团队模型测算与历史混改阶段划分",
    },
]


MODEL_VALIDATION_PEER_CASES = [
    {
        "title": "类型一：国有优质资产注入上市平台",
        "items": ["中航电测→中航成飞", "中国船舶吸收合并中国重工"],
    },
    {
        "title": "类型二：国有控股企业控制权转让给民营资本",
        "items": ["旗天科技仍待进一步观察"],
    },
    {
        "title": "长期优化样本",
        "items": ["东航物流", "中国联通"],
    },
]


def rule_tone_class(key: str) -> str:
    return f"rule-tone-{key}" if key in {"finance", "equity", "region", "mixed"} else "rule-tone-default"


def weight_percent_value(weight: str) -> int:
    try:
        return int(str(weight).strip().rstrip("%"))
    except ValueError:
        return 0


def rule_weight_bar_html(section: dict) -> str:
    width = max(0, min(100, weight_percent_value(str(section.get("weight", "")))))
    tone = rule_tone_class(str(section.get("key", "")))
    return (
        '<div class="rule-weight-bar">'
        f'<span class="rule-weight-fill {tone}" style="width:{width}%;"></span>'
        "</div>"
    )


def rule_weight_stack_html(sections: list[dict]) -> str:
    rows = []
    for section in sections:
        rows.append(
            '<div class="rule-weight-row">'
            '<div class="rule-weight-meta">'
            f'<span>{h(section.get("label", ""))}</span>'
            f'<strong>{h(section.get("weight", ""))}</strong>'
            "</div>"
            f"{rule_weight_bar_html(section)}"
            "</div>"
        )
    return f'<div class="rule-weight-stack">{"".join(rows)}</div>'


def rule_module_card_html(section: dict) -> str:
    tone = rule_tone_class(str(section.get("key", "")))
    items = "".join(f"<li>{h(item)}</li>" for item in section.get("items", []))
    return (
        f'<div class="rule-module-card {tone}" data-uniform-height="true">'
        '<div class="rule-card-head">'
        "<div>"
        f'<div class="meta">评分模块</div>'
        f'<h3>{h(section.get("label", ""))}</h3>'
        "</div>"
        f'<div class="rule-weight-number">{h(section.get("weight", ""))}</div>'
        "</div>"
        f"{rule_weight_bar_html(section)}"
        '<div class="rule-card-facts">'
        f'<span>原始满分 {h(section.get("raw_max", ""))}</span>'
        "<span>归一化 100</span>"
        "</div>"
        f'<p class="rule-summary">{h(section.get("summary", ""))}</p>'
        f'<ul class="rule-list">{items}</ul>'
        "</div>"
    )


def potential_level_display_range(score_range: str) -> str:
    if score_range == ">=80":
        return "80-100"
    if score_range == ">=70":
        return "70-79"
    if score_range == ">=60":
        return "60-69"
    return "<60"


def potential_level_grid_html(rows: list[dict]) -> str:
    items = []
    for index, row in enumerate(rows):
        display_range = potential_level_display_range(str(row.get("分数区间", "")))
        items.append(
            f'<div class="level-item" data-level="{index}">'
            f'<div class="level-score">{h(display_range)}</div>'
            f'<div class="company-title">{h(row.get("潜力等级", ""))}</div>'
            "</div>"
        )
    return f'<div class="level-grid">{"".join(items)}</div>'


def score(company: dict) -> float:
    return float(company.get("totalScore", company.get("score", 0)) or 0)


def short_name(company: dict) -> str:
    return str(company.get("shortName") or company.get("short_name") or company.get("name") or "")


def is_missing_value(value: Any) -> bool:
    text = str(value if value is not None else "").strip()
    return text == "" or text in {"待补充", "None", "nan", "NaN"}


def report_value(value: Any, fallback: str = "暂未入库") -> str:
    return fallback if is_missing_value(value) else str(value)


def report_value_class(value: Any) -> str:
    return "metric-value muted-value" if is_missing_value(value) else "metric-value"


def metric_card_rows(title: str, payload: dict) -> list[tuple[str, str, Any]]:
    def money_value(key: str) -> tuple[str, Any]:
        raw = payload.get(key)
        if is_missing_value(raw):
            return "暂未入库", raw
        return f"{float(raw):.2f} 亿元", raw

    def percent_value(key: str) -> tuple[str, Any]:
        raw = payload.get(key)
        if is_missing_value(raw):
            return "暂未入库", raw
        return f"{raw}%", raw

    if title == "财务证据":
        return [
            ("营业收入", *money_value("revenue")),
            ("归母净利润", *money_value("netProfit")),
            ("资产负债率", *percent_value("assetLiabilityRatio")),
            ("ROE", *percent_value("roe")),
        ]
    return [
        (
            "第一大股东",
            report_value(payload.get("topShareholderName", "")),
            payload.get("topShareholderName", ""),
        ),
        ("第一大股东持股", *percent_value("topShareholderRatio")),
        ("股权质押率", *percent_value("pledgeRatio")),
        ("审计意见", report_value(payload.get("auditOpinion", "")), payload.get("auditOpinion", "")),
        ("审计日期", report_value(payload.get("auditDate", "")), payload.get("auditDate", "")),
        (
            "审计事务所",
            report_value(payload.get("domesticAuditFirm", "")),
            payload.get("domesticAuditFirm", ""),
        ),
    ]


def mixed_module_detail_html(detail: dict) -> str:
    profile = detail.get("mixedDegreeProfile") or {}
    if not profile:
        return (
            '<div class="detail-card mixed-module-empty">'
            "<h3>混改程度评分明细</h3>"
            "<p>暂无混改结构明细，已回退展示基础指标证据。</p>"
            "</div>"
        )
    return (
        '<div class="mixed-module-layout">'
        f"{mixed_score_breakdown_html(profile)}"
        f"{mixed_shareholder_panel_html(profile)}"
        "</div>"
    )


def mixed_score_breakdown_html(profile: dict) -> str:
    items = profile.get("scoreItems", [])
    progress_rows = "".join(mixed_score_progress_row_html(item) for item in items)
    table_rows = "".join(
        "<tr>"
        f"<td>{h(item.get('label', ''))}</td>"
        f"<td>{format_number(item.get('score'), 1)}/{format_number(item.get('max'), 0)}</td>"
        f"<td>{format_number(item.get('percent'), 1)}%</td>"
        f"<td>{h(item.get('description', ''))}</td>"
        "</tr>"
        for item in items
    )
    metrics = profile.get("structureMetrics", {})
    metric_chips = "".join(
        f'<span>{h(label)} <strong>{h(value)}</strong></span>'
        for label, value in [
            ("非国有资本", f"{format_number(metrics.get('nonStateRatio'), 1)}%"),
            ("股东类型", format_number(metrics.get("diversity"), 0)),
            ("前十集中度", f"{format_number(metrics.get('ownershipConcentration'), 1)}%"),
        ]
    )
    return (
        '<section class="detail-card mixed-breakdown-card">'
        "<h3>指标拆解与得分依据</h3>"
        '<p class="mixed-panel-copy">五项指标共同构成混改程度评分，非国企可理解为混合股权结构成熟度与外部资本参与程度。</p>'
        f'<div class="mixed-score-lines">{progress_rows}</div>'
        f'<div class="mixed-metric-chips">{metric_chips}</div>'
        '<table class="mixed-data-table">'
        "<thead><tr><th>指标</th><th>得分</th><th>完成度</th><th>判断说明</th></tr></thead>"
        f"<tbody>{table_rows}</tbody>"
        "</table>"
        "</section>"
    )


MIXED_SCORE_ICON_BY_LABEL = {
    "非国有资本进入程度": "capital",
    "股权结构多样性": "diversity",
    "股权制衡程度": "balance",
    "股权融合程度": "integration",
    "股权开放治理程度": "governance",
}


def mixed_score_icon_svg(icon_key: str) -> str:
    icons = {
        "capital": (
            '<path d="M4 9h16" />'
            '<path d="M6 9v8" />'
            '<path d="M10 9v8" />'
            '<path d="M14 9v8" />'
            '<path d="M18 9v8" />'
            '<path d="M3 19h18" />'
            '<path d="M12 4 4 8h16l-8-4Z" />'
        ),
        "diversity": (
            '<circle cx="9" cy="8" r="3" />'
            '<circle cx="16.5" cy="9.5" r="2.5" />'
            '<path d="M3.5 18c.9-3 2.9-4.5 5.5-4.5s4.6 1.5 5.5 4.5" />'
            '<path d="M13.5 15.2c.8-.8 1.8-1.2 3-1.2 2.1 0 3.7 1.2 4.4 3.6" />'
        ),
        "balance": (
            '<path d="M12 4v16" />'
            '<path d="M5 7h14" />'
            '<path d="m6 7-3 6h6L6 7Z" />'
            '<path d="m18 7-3 6h6l-3-6Z" />'
            '<path d="M8 20h8" />'
        ),
        "integration": (
            '<path d="M9 4h6v5h5v6h-5v5H9v-5H4V9h5V4Z" />'
            '<path d="M9 9h6v6H9z" />'
        ),
        "governance": (
            '<path d="M12 3 5 6v5c0 4.3 2.8 7.4 7 9 4.2-1.6 7-4.7 7-9V6l-7-3Z" />'
            '<path d="m9.5 12 1.7 1.7 3.6-4" />'
        ),
    }
    paths = icons.get(icon_key, icons["capital"])
    return f'<svg class="mixed-score-symbol" viewBox="0 0 24 24" aria-hidden="true">{paths}</svg>'


def mixed_score_progress_row_html(item: dict) -> str:
    percent = clamp_percent(item.get("percent", 0))
    score = format_number(item.get("score"), 1)
    max_score = format_number(item.get("max"), 0)
    icon_key = MIXED_SCORE_ICON_BY_LABEL.get(str(item.get("label", "")), "capital")
    return (
        '<div class="mixed-score-line">'
        f'<div class="mixed-score-icon mixed-score-icon-{icon_key}" aria-hidden="true">'
        f"{mixed_score_icon_svg(icon_key)}"
        "</div>"
        '<div class="mixed-score-main">'
        '<div class="mixed-score-meta">'
        f'<strong>{h(item.get("label", ""))}</strong>'
        f"<span>{percent:.1f}%<em>{score}/{max_score}</em></span>"
        "</div>"
        '<div class="mixed-progress-track">'
        f'<span style="width:{percent:.1f}%;"></span>'
        "</div>"
        "</div>"
        "</div>"
    )


def mixed_shareholder_panel_html(profile: dict) -> str:
    shareholders = profile.get("shareholders", [])
    shareholder_rows = "".join(mixed_shareholder_row_html(item) for item in shareholders)
    if not shareholder_rows:
        shareholder_rows = '<tr><td colspan="5" class="mixed-empty-cell">暂无股东结构明细</td></tr>'
    return (
        '<section class="detail-card mixed-shareholder-card">'
        "<h3>主要股东结构名单</h3>"
        '<p class="mixed-panel-copy">展示前十大股东、持股比例、股东性质与结构分类，用于支撑混改程度判断。</p>'
        '<div class="mixed-table-scroll mixed-shareholder-scroll">'
        '<table class="mixed-data-table mixed-shareholder-table">'
        "<colgroup>"
        '<col class="mixed-shareholder-col-rank">'
        '<col class="mixed-shareholder-col-name">'
        '<col class="mixed-shareholder-col-ratio">'
        '<col class="mixed-shareholder-col-nature">'
        '<col class="mixed-shareholder-col-category">'
        "</colgroup>"
        "<thead><tr><th>序号</th><th>股东名称</th><th>持股比例</th><th>股东性质</th><th>类别</th></tr></thead>"
        f"<tbody>{shareholder_rows}</tbody>"
        "</table>"
        "</div>"
        '<h3 class="mixed-subtitle">股东类别占比</h3>'
        f"{mixed_holder_stack_html(profile.get('holderGroups', []))}"
        '<div class="mixed-insight-grid">'
        f"{mixed_note_box_html('自动结构解读', profile.get('structureNotes', []))}"
        f"{mixed_signal_tags_html(profile.get('signalTags', []))}"
        "</div>"
        "</section>"
    )


def mixed_shareholder_row_html(item: dict) -> str:
    holder_name = h(item.get("name", ""))
    holder_nature = h(report_value(item.get("nature", "")))
    holder_group = h(report_value(item.get("holderGroupLabel", "")))
    return (
        "<tr>"
        f"<td>{h(item.get('rank', ''))}</td>"
        f'<td><span class="mixed-holder-name" title="{holder_name}">'
        f'<span class="mixed-holder-name-text">{holder_name}</span>'
        "</span></td>"
        f"<td>{format_number(item.get('ratio'), 2)}%</td>"
        f'<td><span class="mixed-holder-compact" title="{holder_nature}">{holder_nature}</span></td>'
        f'<td><span class="mixed-holder-compact" title="{holder_group}">{holder_group}</span></td>'
        "</tr>"
    )


def mixed_holder_stack_html(groups: list[dict]) -> str:
    if not groups:
        return '<div class="mixed-holder-empty">暂无股东类别占比</div>'
    segments = []
    legend = []
    for group in groups:
        percentage = clamp_percent(group.get("percentage", 0))
        color = h(group.get("color", "#667085"))
        label = h(group.get("label", ""))
        value = f"{format_number(percentage, 2)}%"
        content = value if percentage >= 7 else ""
        segments.append(
            f'<span class="mixed-holder-segment" style="width:{percentage:.2f}%;background:{color};">{content}</span>'
        )
        legend.append(f'<span><i style="background:{color};"></i>{label} {value}</span>')
    return (
        f'<div class="mixed-holder-stack">{"".join(segments)}</div>'
        f'<div class="mixed-holder-legend">{"".join(legend)}</div>'
    )


def mixed_note_box_html(title: str, notes: list[str]) -> str:
    if not notes:
        notes = ["暂无结构解读"]
    items = "".join(f"<li>{h(item)}</li>" for item in notes)
    return (
        '<div class="mixed-note-box">'
        f"<h4>{h(title)}</h4>"
        f"<ul>{items}</ul>"
        "</div>"
    )


def mixed_signal_tags_html(tags: list[str]) -> str:
    if not tags:
        tags = ["持续观察"]
    tag_html = "".join(f"<span>{h(tag)}</span>" for tag in tags)
    return (
        '<div class="mixed-note-box">'
        "<h4>自动混改信号标签</h4>"
        f'<div class="mixed-signal-tags">{tag_html}</div>'
        "</div>"
    )


def format_number(value: Any, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return f"{number:.{digits}f}"


def clamp_percent(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return max(0.0, min(100.0, number))


def percent_score_text(value: Any) -> str:
    score_text = f"{clamp_percent(value):.1f}".rstrip("0").rstrip(".")
    return f"{score_text}/100"


FINANCE_RADAR_METRICS = (
    "Altman Z",
    "资产负债率",
    "经营现金流/收入",
    "净利润三年CAGR",
    "连续分红年数",
    "有息负债占比",
)


GOVERNANCE_RADAR_METRICS = (
    ("股权结构", "股权结构"),
    ("股权质押", "质押风险"),
    ("审计意见", "审计质量"),
    ("合规记录", "合规水平"),
    ("行业地位", "行业地位"),
)

DEEPSEEK_HIGHLIGHT_CACHE: dict[str, list[str]] = {}
DEEPSEEK_RISK_CACHE: dict[str, list[str]] = {}


def company_risk_items(company: dict) -> tuple[list[str], str]:
    deepseek_items = []
    if get_setting("DEEPSEEK_API_KEY") and get_setting("DEEPSEEK_AI_ENABLED", "1").strip().lower() not in {"0", "false"}:
        deepseek_items = _request_deepseek_company_risks(company)
    if deepseek_items:
        return deepseek_items, "AI评价"
    return reason_items(company.get("risks"), "暂无风险提示"), "规则/数据库"


def _request_deepseek_company_risks(company: dict) -> list[str]:
    summary = company_risk_prompt_summary(company)
    model = get_setting("DEEPSEEK_MODEL", "deepseek-chat")
    cache_key = json.dumps(
        {
            "code": company.get("code") or company.get("stock_code", ""),
            "model": model,
            "summary": summary,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    if cache_key in DEEPSEEK_RISK_CACHE:
        return list(DEEPSEEK_RISK_CACHE[cache_key])
    api_key = get_setting("DEEPSEEK_API_KEY")
    base_url = get_setting("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    try:
        timeout = float(get_setting("DEEPSEEK_TIMEOUT_SECONDS", "4") or 4)
    except ValueError:
        timeout = 4.0
    payload = {
        "model": model,
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 240,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是国企混改潜力风险分析助手。只依据用户提供的界面数据，"
                    "输出2到4条简洁中文风险或减分评价；每条不超过32字；不要编号；不要编造缺失信息。"
                ),
            },
            {"role": "user", "content": summary},
        ],
    }
    api_request = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("ascii"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with open_deepseek_request(api_request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    content = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    items = parse_highlight_lines(content)
    DEEPSEEK_RISK_CACHE[cache_key] = items
    return list(items)


def open_deepseek_request(api_request: request.Request, timeout: float):
    if request.urlopen is not DEFAULT_URLOPEN:
        return request.urlopen(api_request, timeout=timeout)
    return request.build_opener(request.ProxyHandler({})).open(api_request, timeout=timeout)


def company_risk_prompt_summary(company: dict) -> str:
    lines = [
        "company:",
        f"code: {company.get('code') or company.get('stock_code', '')}",
        f"name: {short_name(company)}",
        f"full_name: {company.get('name', '')}",
        f"total_score: {score(company):.1f}",
        f"province: {company.get('province', '')}",
        f"city: {company.get('city', '')}",
        f"industry: {company.get('industry', '')}",
        f"controller: {company.get('controller', '')}",
        f"state_attribute: {company.get('stateAttribute', company.get('ownership', ''))}",
        "four modules:",
    ]
    for key, label, weight in MODULE_LABELS:
        try:
            detail = module_detail(company, key)
        except Exception:
            detail = {"score": company.get("modules", {}).get(key, 0), "rows": [], "notes": []}
        try:
            module_score = float(detail.get("score", 0))
        except (TypeError, ValueError):
            module_score = 0.0
        lines.append(f"- {key} {label} weight {weight} score {module_score:.1f}")
        for row in detail.get("rows", [])[:8]:
            lines.append(
                "  evidence: "
                f"{row.get('指标', '')}: value={row.get('数值', '')}, score={row.get('得分', '')}"
            )
        notes = [str(item) for item in detail.get("notes", [])[:4] if str(item).strip()]
        if notes:
            lines.append(f"  notes: {'；'.join(notes)}")
    lines.append("highlights: " + "；".join(reason_items(company.get("highlights"), "暂无积极信号")))
    lines.append("risks: " + "；".join(reason_items(company.get("risks"), "暂无风险提示")))
    return "\n".join(lines)


def finance_score_parts(score_text: Any) -> tuple[float, float, float]:
    parts = str(score_text or "").replace(" ", "").split("/")
    try:
        score_value = float(parts[0])
        max_value = float(parts[1])
    except (IndexError, TypeError, ValueError):
        return 0.0, 0.0, 0.0
    if max_value <= 0:
        return score_value, max_value, 0.0
    return score_value, max_value, clamp_percent(score_value / max_value * 100)


def finance_radar_items(rows: list[dict]) -> list[dict]:
    row_by_label = {str(row.get("指标", "")): row for row in rows}
    items = []
    for label in FINANCE_RADAR_METRICS:
        row = row_by_label.get(label, {})
        score_value, max_value, percent = finance_score_parts(row.get("得分", ""))
        value = report_value(row.get("数值", ""))
        score_label = "无数据" if not row else f"{score_value:.1f}/{max_value:.1f}"
        items.append(
            {
                "label": label,
                "value": value,
                "score_label": score_label,
                "percent": percent,
            }
        )
    return items


def finance_radar_point(
    index: int,
    percent: float,
    center_x: float = 250.0,
    center_y: float = 182.0,
    radius: float = 108.0,
) -> tuple[float, float]:
    angle = -math.pi / 2 + (math.tau * index / len(FINANCE_RADAR_METRICS))
    scaled_radius = radius * clamp_percent(percent) / 100
    return center_x + math.cos(angle) * scaled_radius, center_y + math.sin(angle) * scaled_radius


def governance_radar_point(
    index: int,
    percent: float,
    count: int,
    center_x: float = 250.0,
    center_y: float = 182.0,
    radius: float = 108.0,
) -> tuple[float, float]:
    angle = -math.pi / 2 + (math.tau * index / count)
    scaled_radius = radius * clamp_percent(percent) / 100
    return center_x + math.cos(angle) * scaled_radius, center_y + math.sin(angle) * scaled_radius


def governance_radar_items(rows: list[dict]) -> list[dict]:
    row_by_label = {str(row.get("指标", "")): row for row in rows}
    items = []
    for source_label, display_label in GOVERNANCE_RADAR_METRICS:
        row = row_by_label.get(source_label, {})
        score_value, max_value, percent = finance_score_parts(row.get("得分", ""))
        items.append(
            {
                "label": display_label,
                "source_label": source_label,
                "value": report_value(row.get("数值", "")),
                "score_label": "无数据" if not row else f"{score_value:.1f}/{max_value:.1f}",
                "percent": percent,
            }
        )
    return items


def governance_radar_chart_html(rows: list[dict]) -> str:
    items = governance_radar_items(rows)
    center_x, center_y, radius = 250.0, 182.0, 108.0
    label_radius = 152.0
    count = len(items)
    grid_polygons = []
    for level in (20, 40, 60, 80, 100):
        points = " ".join(
            f"{x:.1f},{y:.1f}"
            for x, y in [
                governance_radar_point(index, level, count, center_x, center_y, radius)
                for index in range(count)
            ]
        )
        grid_polygons.append(f'<polygon points="{points}" />')
    axis_lines = []
    labels = []
    data_points = []
    for index, item in enumerate(items):
        axis_x, axis_y = governance_radar_point(index, 100, count, center_x, center_y, radius)
        label_x, label_y = governance_radar_point(index, 100, count, center_x, center_y, label_radius)
        point_x, point_y = governance_radar_point(index, item["percent"], count, center_x, center_y, radius)
        anchor = "middle"
        if label_x > center_x + 12:
            anchor = "start"
        elif label_x < center_x - 12:
            anchor = "end"
        axis_lines.append(f'<line x1="{center_x}" y1="{center_y}" x2="{axis_x:.1f}" y2="{axis_y:.1f}" />')
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}">{h(item["label"])}</text>'
        )
        data_points.append((point_x, point_y, item))
    data_polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in data_points)
    markers = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4">'
        f'<title>{h(item["label"])}：{h(item["value"])} · {h(item["score_label"])} · {item["percent"]:.1f}%</title>'
        "</circle>"
        for x, y, item in data_points
    )
    average = sum(item["percent"] for item in items) / len(items)
    return (
        '<section class="finance-radar-card governance-radar-card detail-card">'
        '<div class="finance-radar-head">'
        "<h3>治理能力雷达图</h3>"
        f'<div class="finance-radar-score"><span>能力模型</span><strong>{average:.1f}%</strong></div>'
        "</div>"
        '<div class="finance-radar-wrap">'
        '<svg class="finance-radar-svg" viewBox="0 0 500 370" role="img" aria-label="治理能力五维雷达图">'
        f'<g class="finance-radar-grid">{"".join(grid_polygons)}</g>'
        f'<g class="finance-radar-axis">{"".join(axis_lines)}</g>'
        f'<polygon class="finance-radar-area" points="{data_polygon}" />'
        f'<polyline class="finance-radar-line" points="{data_polygon} {data_points[0][0]:.1f},{data_points[0][1]:.1f}" />'
        f'<g class="finance-radar-points">{markers}</g>'
        f'<g class="finance-radar-labels">{"".join(labels)}</g>'
        '<text class="finance-radar-center" x="250" y="186" text-anchor="middle">能力模型</text>'
        "</svg>"
        "</div>"
        "</section>"
    )


def governance_trend_chart_html(trend: list[dict]) -> str:
    if not trend:
        return '<div class="governance-empty">暂无治理合规趋势数据</div>'
    rows = sorted(trend, key=lambda item: int(item.get("year", 0)))
    width, height = 420, 210
    left, right, top, bottom = 42, 24, 20, 42
    plot_width = width - left - right
    plot_height = height - top - bottom

    def xy(index: int, score: float) -> tuple[float, float]:
        x = left + (plot_width * index / max(1, len(rows) - 1))
        y = top + plot_height - (clamp_percent(score) / 100 * plot_height)
        return x, y

    grid = []
    for value in (0, 25, 50, 75, 100):
        y = top + plot_height - (value / 100 * plot_height)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" />')
        grid.append(f'<text x="6" y="{y + 4:.1f}">{value}</text>')
    points = [xy(index, float(row.get("score", 0))) for index, row in enumerate(rows)]
    point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    circles = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.6"><title>{int(row.get("year", 0))}年：{percent_score_text(row.get("score", 0))}</title></circle>'
        f'<text class="governance-score-label" x="{x:.1f}" y="{y - 10:.1f}">{percent_score_text(row.get("score", 0))}</text>'
        for (x, y), row in zip(points, rows)
    )
    year_labels = "".join(
        f'<text class="governance-year-label" x="{x:.1f}" y="{height - 14}">{int(row.get("year", 0))}年</text>'
        for (x, _), row in zip(points, rows)
    )
    table_rows = "".join(
        "<tr>"
        f"<td>{int(row.get('year', 0))}年</td>"
        f"<td>{percent_score_text(row.get('score', 0))}</td>"
        f"<td>{h(row.get('date', ''))}</td>"
        "</tr>"
        for row in rows
    )
    return (
        '<div class="governance-trend-chart">'
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="近三年治理合规趋势图">'
        f'<g class="governance-grid">{"".join(grid)}</g>'
        f'<polyline class="governance-trend-line" points="{point_text}" />'
        f'<g class="governance-trend-points">{circles}</g>'
        f'<g class="governance-year-axis">{year_labels}</g>'
        "</svg>"
        '<table class="governance-trend-table"><thead><tr><th>年份</th><th>得分</th><th>取数日期</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table>"
        "</div>"
    )


def governance_highlights_html(detail: dict) -> str:
    deepseek_items = []
    if get_setting("DEEPSEEK_API_KEY") and get_setting("DEEPSEEK_AI_ENABLED", "1").strip().lower() not in {"0", "false"}:
        deepseek_items = _request_deepseek_governance_highlights(detail)
    source = "DeepSeek生成" if deepseek_items else "规则生成"
    items = deepseek_items or rule_governance_highlights(detail)
    rows = "".join(
        f'<div class="governance-highlight-item"><span class="note-dot">i</span>{h(item)}</div>' for item in items
    )
    return (
        '<section class="detail-card governance-highlights-card">'
        '<div class="governance-card-head"><h3>关键治理亮点</h3>'
        f'<span class="governance-source">{h(source)}</span></div>'
        f"{rows}"
        "</section>"
    )


def _request_deepseek_governance_highlights(detail: dict) -> list[str]:
    summary = governance_prompt_summary(detail)
    model = get_setting("DEEPSEEK_MODEL", "deepseek-chat")
    cache_key = json.dumps({"model": model, "summary": summary}, ensure_ascii=False, sort_keys=True)
    if cache_key in DEEPSEEK_HIGHLIGHT_CACHE:
        return list(DEEPSEEK_HIGHLIGHT_CACHE[cache_key])
    api_key = get_setting("DEEPSEEK_API_KEY")
    base_url = get_setting("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/")
    try:
        timeout = float(get_setting("DEEPSEEK_TIMEOUT_SECONDS", "4") or 4)
    except ValueError:
        timeout = 4.0
    payload = {
        "model": model,
        "stream": False,
        "temperature": 0.2,
        "max_tokens": 180,
        "messages": [
            {
                "role": "system",
                "content": "你是企业治理合规分析助手，只输出2到4条简洁中文亮点，每条不超过28字，不要编号。",
            },
            {"role": "user", "content": summary},
        ],
    }
    api_request = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("ascii"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with open_deepseek_request(api_request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    content = str(data.get("choices", [{}])[0].get("message", {}).get("content", ""))
    items = parse_highlight_lines(content)
    DEEPSEEK_HIGHLIGHT_CACHE[cache_key] = items
    return list(items)


def governance_prompt_summary(detail: dict) -> str:
    evidence = [
        f"{row.get('指标', '')}: 数值{row.get('数值', '')}, 得分{row.get('得分', '')}"
        for row in detail.get("rows", [])
    ]
    trend = [
        f"{int(row.get('year', 0))}年{float(row.get('score', 0)):.1f}分"
        for row in detail.get("governanceTrend", [])
    ]
    return "治理合规评分证据：\n" + "\n".join(evidence) + "\n近三年趋势：" + "，".join(trend)


def parse_highlight_lines(content: str) -> list[str]:
    items = []
    for line in content.splitlines():
        text = re.sub(r"^\s*[-*•]?\s*[0-9０-９]+[.)、）．]\s*", "", line.strip()).strip()
        text = text.lstrip("-*、)） ").strip()
        if text:
            items.append(text[:60])
    return items[:4]


def rule_governance_highlights(detail: dict) -> list[str]:
    rows = detail.get("rows", [])
    scores = {str(row.get("指标", "")): finance_score_parts(row.get("得分", ""))[2] for row in rows}
    items = []
    if scores.get("股权结构", 0) >= 80:
        items.append("股权结构较清晰，治理基础稳定。")
    if scores.get("股权质押", 0) >= 80:
        items.append("质押风险可控，股权安全边际较好。")
    trend = detail.get("governanceTrend", [])
    if len(trend) >= 2 and float(trend[-1].get("score", 0)) > float(trend[0].get("score", 0)):
        items.append("治理合规得分连续改善，能力模型走强。")
    if scores.get("审计意见", 0) >= 80:
        items.append("审计质量稳定，外部监督信号良好。")
    if scores.get("合规记录", 0) >= 80:
        items.append("合规记录表现良好，负面约束较少。")
    if scores.get("行业地位", 0) >= 80:
        items.append("行业地位突出，治理资质具备支撑力。")
    return items[:4] or ["治理证据仍需补充，建议结合公告继续观察。"]


def finance_radar_chart_html(rows: list[dict]) -> str:
    items = finance_radar_items(rows)
    center_x, center_y, radius = 250.0, 182.0, 108.0
    label_radius = 152.0
    grid_polygons = []
    for level in (20, 40, 60, 80, 100):
        points = " ".join(
            f"{x:.1f},{y:.1f}"
            for x, y in [finance_radar_point(index, level, center_x, center_y, radius) for index in range(6)]
        )
        grid_polygons.append(f'<polygon points="{points}" />')
    axis_lines = []
    labels = []
    data_points = []
    for index, item in enumerate(items):
        axis_x, axis_y = finance_radar_point(index, 100, center_x, center_y, radius)
        label_x, label_y = finance_radar_point(index, 100, center_x, center_y, label_radius)
        point_x, point_y = finance_radar_point(index, item["percent"], center_x, center_y, radius)
        anchor = "middle"
        if label_x > center_x + 12:
            anchor = "start"
        elif label_x < center_x - 12:
            anchor = "end"
        axis_lines.append(f'<line x1="{center_x}" y1="{center_y}" x2="{axis_x:.1f}" y2="{axis_y:.1f}" />')
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="{anchor}">{h(item["label"])}</text>'
        )
        data_points.append((point_x, point_y, item))
    data_polygon = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in data_points)
    markers = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.4">'
        f'<title>{h(item["label"])}：{h(item["value"])} · {h(item["score_label"])} · {item["percent"]:.1f}%</title>'
        "</circle>"
        for x, y, item in data_points
    )
    average = sum(item["percent"] for item in items) / len(items)
    metric_rows = "".join(
        '<div class="finance-radar-metric">'
        f'<span>{h(item["label"])}</span>'
        f'<strong>{h(item["value"])}</strong>'
        f'<em>{h(item["score_label"])}</em>'
        "</div>"
        for item in items
    )
    return (
        '<section class="finance-radar-card detail-card">'
        '<div class="finance-radar-head">'
        "<h3>财务引资潜力雷达图</h3>"
        f'<div class="finance-radar-score"><span>综合完成度</span><strong>{average:.1f}%</strong></div>'
        "</div>"
        '<div class="finance-radar-wrap">'
        '<svg class="finance-radar-svg" viewBox="0 0 500 370" role="img" aria-label="财务引资潜力六项指标雷达图">'
        f'<g class="finance-radar-grid">{"".join(grid_polygons)}</g>'
        f'<g class="finance-radar-axis">{"".join(axis_lines)}</g>'
        f'<polygon class="finance-radar-area" points="{data_polygon}" />'
        f'<polyline class="finance-radar-line" points="{data_polygon} {data_points[0][0]:.1f},{data_points[0][1]:.1f}" />'
        f'<g class="finance-radar-points">{markers}</g>'
        f'<g class="finance-radar-labels">{"".join(labels)}</g>'
        '<text class="finance-radar-center" x="250" y="186" text-anchor="middle">得分占比</text>'
        "</svg>"
        "</div>"
        f'<div class="finance-radar-metrics">{metric_rows}</div>'
        "</section>"
    )


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --ink: #101820;
          --muted: #667085;
          --line: rgba(16, 24, 32, 0.12);
          --paper: #fffdfa;
          --warm: #fff4dd;
          --mint: #e7f6f2;
          --accent: #ef3f2d;
          --accent-dark: #b52b25;
          --violet: #4338ca;
          --shadow: 0 18px 45px rgba(16, 24, 32, 0.10);
        }
        .stApp {
          background: var(--paper);
          color: var(--ink);
        }
        header, footer, #MainMenu { visibility: hidden; }
        .block-container {
          max-width: 1180px;
          padding-top: 0.7rem;
          padding-bottom: 4rem;
        }
        h1, h2, h3 {
          font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
          letter-spacing: 0;
        }
        p, div, span, label, button, input {
          font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif;
          letter-spacing: 0;
        }
        .topbar {
          height: 58px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid var(--line);
          background: rgba(255, 253, 250, 0.86);
          backdrop-filter: blur(10px);
          margin: 0 -2rem 0 -2rem;
          padding: 0 2rem;
          position: sticky;
          top: 0;
          z-index: 20;
        }
        .brand {
          display: flex;
          align-items: center;
          gap: 10px;
          font-weight: 700;
        }
        .brand-mark {
          width: 32px;
          height: 32px;
          border-radius: 999px;
          display: grid;
          place-items: center;
          color: white;
          background: linear-gradient(145deg, #5b49c8, #ef3f2d);
          font-family: "Noto Serif SC", serif;
        }
        .brand-sub {
          color: var(--muted);
          font-size: 11px;
          text-transform: uppercase;
          margin-top: -3px;
        }
        .nav-note {
          color: var(--muted);
          font-size: 13px;
        }
        .hero {
          margin: 0 -2rem 0 -2rem;
          padding: 70px 2rem 82px 2rem;
          position: relative;
          background:
            radial-gradient(circle at 18% 20%, rgba(255, 232, 176, 0.72), transparent 34%),
            radial-gradient(circle at 78% 25%, rgba(202, 244, 239, 0.86), transparent 34%),
            linear-gradient(120deg, #fffaf0, #f5fff9 48%, #eaf8fb);
          border-bottom: 1px solid rgba(16, 24, 32, 0.08);
        }
        .hero-rule-link {
          position: absolute;
          right: 2rem;
          top: 44px;
          color: var(--accent);
          font-size: 14px;
          font-weight: 800;
          text-decoration: none;
          border-bottom: 2px solid var(--accent);
          padding-bottom: 5px;
          transition: color 160ms ease, border-color 160ms ease;
        }
        .hero-rule-link:hover {
          color: var(--accent-dark);
          border-color: var(--accent-dark);
        }
        .kicker {
          color: var(--muted);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: 0.22em;
          margin-bottom: 18px;
        }
        .headline {
          font-family: "Noto Serif SC", "Songti SC", serif;
          font-size: clamp(48px, 7vw, 86px);
          line-height: 1.06;
          max-width: 850px;
        }
        .headline .accent {
          color: transparent;
          background: linear-gradient(90deg, #5b49c8, #ef3f2d);
          -webkit-background-clip: text;
          background-clip: text;
        }
        .subline {
          max-width: 720px;
          color: #4d5a61;
          line-height: 1.8;
          margin-top: 22px;
          font-size: 15px;
        }
        .stat-card, .soft-card, .rank-card, .detail-card {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          border-radius: 18px;
          box-shadow: var(--shadow);
        }
        .stat-card {
          padding: 20px 22px;
          min-height: 92px;
        }
        .stat-label {
          color: var(--muted);
          font-size: 12px;
        }
        .stat-value {
          font-family: "Noto Serif SC", serif;
          font-size: 28px;
          margin-top: 8px;
        }
        .section-kicker {
          color: var(--accent);
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.26em;
          margin-top: 54px;
          margin-bottom: 8px;
          font-weight: 700;
        }
        .section-title {
          font-family: "Noto Serif SC", serif;
          font-size: 34px;
          margin-bottom: 22px;
        }
        .feature-card {
          min-height: 420px;
          border-radius: 20px;
          color: white;
          padding: 30px;
          background:
            radial-gradient(circle at 72% 14%, #ff7a2f, transparent 16%),
            linear-gradient(145deg, #3131a0, #973f83 48%, #e02d2b);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          box-shadow: 0 25px 60px rgba(110, 40, 80, 0.28);
        }
        .feature-rank {
          font-family: "Noto Serif SC", serif;
          font-size: 76px;
          opacity: 0.88;
        }
        .score-pill {
          width: 106px;
          height: 106px;
          border-radius: 999px;
          display: grid;
          place-items: center;
          color: white;
          background: linear-gradient(145deg, #ff6a2f, #ef3f2d);
          box-shadow: 0 18px 36px rgba(239, 63, 45, 0.28);
          font-family: "Noto Serif SC", serif;
          font-size: 32px;
        }
        .small-score {
          color: var(--accent);
          font-family: "Noto Serif SC", serif;
          font-size: 25px;
        }
        .rank-card {
          padding: 17px 18px;
          min-height: 92px;
          box-shadow: none;
        }
        .rank-number {
          font-family: "Noto Serif SC", serif;
          color: var(--muted);
          font-size: 23px;
        }
        .company-title {
          font-weight: 700;
          color: var(--ink);
        }
        .meta {
          color: var(--muted);
          font-size: 12px;
          line-height: 1.6;
        }
        .detail-hero {
          margin: 0 -2rem 42px -2rem;
          padding: 58px 2rem 70px 2rem;
          background:
            radial-gradient(circle at 22% 20%, rgba(255, 234, 184, 0.76), transparent 34%),
            radial-gradient(circle at 82% 26%, rgba(203, 244, 241, 0.82), transparent 34%),
            linear-gradient(120deg, #fffaf0, #eefcf6 54%, #e9f7fb);
          border-bottom: 1px solid rgba(16, 24, 32, 0.08);
        }
        .breadcrumb {
          color: var(--muted);
          font-size: 12px;
          letter-spacing: 0.18em;
          text-transform: uppercase;
          margin-bottom: 24px;
        }
        .detail-name {
          font-family: "Noto Serif SC", serif;
          font-size: clamp(44px, 6vw, 76px);
          line-height: 1.05;
        }
        .detail-meta {
          color: #4d5a61;
          margin-top: 14px;
          font-size: 15px;
        }
        .report-hero {
          margin: 0 -2rem 42px -2rem;
          padding: 42px 2rem 48px 2rem;
          background:
            linear-gradient(90deg, rgba(16, 24, 32, 0.04) 1px, transparent 1px),
            linear-gradient(180deg, rgba(16, 24, 32, 0.035) 1px, transparent 1px),
            linear-gradient(135deg, #fff9ed 0%, #f7fbf7 52%, #edf7f9 100%);
          background-size: 28px 28px, 28px 28px, auto;
          border-bottom: 1px solid rgba(16, 24, 32, 0.10);
        }
        .report-hero-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(382px, 432px);
          gap: 30px;
          align-items: stretch;
        }
        .report-label-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 16px 0 18px 0;
        }
        .report-chip, .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          border: 1px solid rgba(16, 24, 32, 0.12);
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.76);
          padding: 5px 10px;
          color: #344054;
          font-size: 12px;
          font-weight: 700;
        }
        .status-badge {
          border-color: transparent;
        }
        .band-strong {
          color: #0f766e;
          background: #dff8ef;
        }
        .band-support {
          color: #b54708;
          background: #fff1d6;
        }
        .band-watch {
          color: #475467;
          background: #edf1f5;
        }
        .band-risk {
          color: #b42318;
          background: #ffe4e0;
        }
        .report-summary {
          max-width: 760px;
          color: #2f3940;
          font-size: 17px;
          line-height: 1.8;
          padding: 18px 20px;
          border-left: 4px solid var(--accent);
          background: rgba(255, 255, 255, 0.72);
          border-radius: 0 16px 16px 0;
        }
        .report-stats {
          display: grid;
          grid-template-columns: repeat(3, minmax(120px, 1fr));
          gap: 12px;
          margin-top: 22px;
          max-width: 720px;
        }
        .report-stat {
          border-top: 1px solid rgba(16, 24, 32, 0.15);
          padding-top: 12px;
        }
        .hero-signal-panel {
          display: grid;
          grid-template-columns: minmax(142px, 170px) 136px;
          gap: 14px;
          align-items: center;
          align-self: center;
          padding-top: 6px;
        }
        .reform-status-stack {
          display: grid;
          grid-template-columns: 1fr;
          gap: 10px;
          align-self: center;
        }
        .reform-info-card {
          position: relative;
          min-height: 92px;
          padding: 12px 12px;
          border: 1px solid rgba(16, 24, 32, 0.12);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.66);
          box-shadow: 0 14px 34px rgba(16, 24, 32, 0.07);
          overflow: hidden;
        }
        .reform-info-card::before {
          content: "";
          position: absolute;
          inset: 0 auto 0 0;
          width: 4px;
          background: var(--accent);
        }
        .reform-info-card.state-private::before {
          background: #667085;
        }
        .reform-info-card.status-potential::before,
        .reform-info-card.status-progress::before {
          background: #f3a53c;
        }
        .reform-info-card.status-complete::before {
          background: #0f766e;
        }
        .reform-info-label {
          color: var(--muted);
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0;
          text-transform: uppercase;
        }
        .reform-info-value {
          margin-top: 8px;
          color: var(--ink);
          font-family: "Noto Serif SC", serif;
          font-size: 17px;
          line-height: 1.25;
          font-weight: 700;
          overflow-wrap: anywhere;
        }
        .reform-info-card.status-progress .reform-info-value,
        .reform-info-card.status-potential .reform-info-value {
          font-size: 16px;
          line-height: 1.34;
        }
        .reform-info-sub {
          margin-top: 8px;
          color: #667085;
          font-size: 11px;
          font-weight: 700;
        }
        .score-panel {
          display: grid;
          justify-items: center;
          gap: 10px;
          padding: 18px 14px;
          border: 1px solid rgba(16, 24, 32, 0.12);
          background: rgba(255, 255, 255, 0.72);
          border-radius: 18px;
          box-shadow: 0 18px 40px rgba(16, 24, 32, 0.08);
        }
        .module-card {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.88);
          border-radius: 18px;
          padding: 20px;
          min-height: 214px;
          box-shadow: 0 14px 34px rgba(16, 24, 32, 0.08);
          display: flex;
          flex-direction: column;
          justify-content: space-between;
        }
        .module-title {
          font-family: "Noto Serif SC", serif;
          font-size: 19px;
          margin-bottom: 8px;
        }
        .module-card-head {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 10px;
        }
        .module-summary {
          color: #475467;
          font-size: 12px;
          line-height: 1.7;
          margin-top: 12px;
          min-height: 62px;
        }
        .bar {
          height: 8px;
          background: #ece8df;
          border-radius: 999px;
          overflow: hidden;
          margin-top: 12px;
        }
        .bar span {
          display: block;
          height: 100%;
          background: linear-gradient(90deg, #ff6a2f, #ef3f2d);
          border-radius: 999px;
        }
        .detail-card {
          padding: 24px 26px;
          margin-bottom: 22px;
        }
        .detail-card h3 {
          margin: 0 0 16px 0;
          font-size: 22px;
        }
        .finance-radar-card {
          min-height: 430px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .finance-radar-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 18px;
          margin-bottom: 6px;
        }
        .finance-radar-head h3 {
          margin-bottom: 0;
        }
        .finance-radar-score {
          border: 1px solid rgba(239, 63, 45, 0.18);
          background: rgba(255, 246, 240, 0.88);
          border-radius: 14px;
          padding: 9px 12px;
          text-align: right;
          min-width: 104px;
        }
        .finance-radar-score span {
          display: block;
          color: var(--muted);
          font-size: 11px;
          line-height: 1.2;
        }
        .finance-radar-score strong {
          display: block;
          color: var(--accent);
          font-family: "Noto Serif SC", serif;
          font-size: 23px;
          line-height: 1.1;
          margin-top: 4px;
        }
        .finance-radar-wrap {
          display: grid;
          place-items: center;
          margin-top: 4px;
        }
        .finance-radar-svg {
          width: 100%;
          max-width: 440px;
          height: auto;
          display: block;
        }
        .finance-radar-grid polygon {
          fill: none;
          stroke: rgba(16, 24, 32, 0.13);
          stroke-width: 1;
        }
        .finance-radar-axis line {
          stroke: rgba(16, 24, 32, 0.11);
          stroke-dasharray: 4 6;
        }
        .finance-radar-area {
          fill: rgba(239, 63, 45, 0.18);
          stroke: none;
        }
        .finance-radar-line {
          fill: none;
          stroke: var(--accent);
          stroke-width: 2.8;
          stroke-linejoin: round;
          stroke-linecap: round;
        }
        .finance-radar-points circle {
          fill: #fffdfa;
          stroke: var(--accent);
          stroke-width: 2.4;
        }
        .finance-radar-labels text {
          fill: #344054;
          font-size: 12px;
          font-weight: 800;
        }
        .finance-radar-center {
          fill: rgba(102, 112, 133, 0.78);
          font-size: 12px;
          font-weight: 700;
        }
        .finance-radar-metrics {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 9px 12px;
          margin-top: auto;
        }
        .finance-radar-metric {
          border-top: 1px solid var(--line);
          padding-top: 9px;
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 2px 10px;
          align-items: baseline;
        }
        .finance-radar-metric span {
          color: #344054;
          font-size: 12px;
          font-weight: 800;
          overflow-wrap: anywhere;
        }
        .finance-radar-metric strong {
          color: var(--ink);
          font-size: 12px;
          text-align: right;
        }
        .finance-radar-metric em {
          grid-column: 1 / -1;
          color: var(--muted);
          font-size: 11px;
          font-style: normal;
        }
        .governance-trend-card,
        .governance-highlights-card {
          min-height: 280px;
        }
        .governance-card-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 12px;
        }
        .governance-card-head h3 {
          margin-bottom: 0;
        }
        .governance-source {
          border: 1px solid rgba(15, 170, 165, 0.24);
          background: rgba(231, 246, 242, 0.82);
          color: #087c78;
          border-radius: 999px;
          padding: 5px 10px;
          font-size: 11px;
          font-weight: 800;
          white-space: nowrap;
        }
        .governance-trend-chart svg {
          width: 100%;
          height: auto;
          display: block;
          margin-top: 4px;
        }
        .governance-grid line {
          stroke: rgba(16, 24, 32, 0.10);
        }
        .governance-grid text {
          fill: rgba(102, 112, 133, 0.82);
          font-size: 11px;
          font-weight: 700;
        }
        .governance-trend-line {
          fill: none;
          stroke: var(--accent);
          stroke-width: 3;
          stroke-linecap: round;
          stroke-linejoin: round;
        }
        .governance-trend-points circle {
          fill: #fffdfa;
          stroke: var(--accent);
          stroke-width: 2.4;
        }
        .governance-score-label,
        .governance-year-label {
          fill: #344054;
          font-size: 12px;
          font-weight: 800;
          text-anchor: middle;
        }
        .governance-trend-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 10px;
          font-size: 12px;
        }
        .governance-trend-table th,
        .governance-trend-table td {
          border-top: 1px solid var(--line);
          padding: 8px 6px;
          text-align: left;
        }
        .governance-trend-table th {
          color: var(--muted);
          font-weight: 800;
        }
        .governance-highlight-item {
          border-top: 1px solid var(--line);
          padding: 13px 0;
          color: #2f3940;
          line-height: 1.7;
        }
        .governance-empty {
          border: 1px dashed rgba(16, 24, 32, 0.18);
          border-radius: 14px;
          color: var(--muted);
          padding: 28px 18px;
          text-align: center;
          font-size: 13px;
        }
        .note-item {
          border-top: 1px solid var(--line);
          padding: 13px 0;
          color: #2f3940;
        }
        .note-dot {
          display: inline-grid;
          place-items: center;
          width: 18px;
          height: 18px;
          border-radius: 999px;
          margin-right: 9px;
          color: white;
          background: var(--accent);
          font-size: 12px;
        }
        .evidence-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
          gap: 24px;
          align-items: start;
        }
        .metric-row {
          display: flex;
          justify-content: space-between;
          gap: 18px;
          border-top: 1px solid var(--line);
          padding: 13px 0;
          color: #2f3940;
        }
        .metric-row .meta {
          min-width: 88px;
        }
        .metric-value {
          font-weight: 800;
          text-align: right;
          color: #101820;
          max-width: 68%;
          line-height: 1.45;
          overflow-wrap: anywhere;
        }
        .muted-value {
          color: #98a2b3;
          font-weight: 700;
        }
        .module-hero {
          margin: 0 -2rem 36px -2rem;
          padding: 40px 2rem 44px 2rem;
          background: linear-gradient(135deg, #fffaf0 0%, #f7fbf8 58%, #eef8fa 100%);
          border-bottom: 1px solid rgba(16, 24, 32, 0.10);
        }
        .module-hero-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 154px;
          gap: 28px;
          align-items: start;
        }
        .module-detail-grid {
          display: grid;
          grid-template-columns: minmax(0, 1.15fr) minmax(310px, 0.85fr);
          gap: 24px;
          align-items: start;
        }
        .jump-row {
          margin-top: 10px;
        }
        .method-box {
          border-left: 4px solid var(--accent);
          padding: 18px 22px;
          background: rgba(255, 255, 255, 0.72);
          border-radius: 0 16px 16px 0;
        }
        .rule-hero {
          margin: 0 -2rem 42px -2rem;
          padding: 44px 2rem 48px 2rem;
          background:
            linear-gradient(90deg, rgba(16, 24, 32, 0.04) 1px, transparent 1px),
            linear-gradient(180deg, rgba(16, 24, 32, 0.035) 1px, transparent 1px),
            linear-gradient(135deg, #fff9ed 0%, #f8fcf8 54%, #edf8fa 100%);
          background-size: 28px 28px, 28px 28px, auto;
          border-bottom: 1px solid rgba(16, 24, 32, 0.10);
        }
        .rule-hero-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(300px, 380px);
          gap: 28px;
          align-items: start;
        }
        .rule-formula-panel {
          border-left: 4px solid var(--accent);
          padding: 18px 22px;
          background: rgba(255, 255, 255, 0.74);
          border-radius: 0 18px 18px 0;
        }
        .method-formula {
          font-family: "Noto Serif SC", serif;
          font-size: clamp(24px, 3vw, 36px);
          line-height: 1.35;
          margin-top: 10px;
        }
        .normalization-flow {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
          margin-top: 20px;
        }
        .flow-step {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.78);
          border-radius: 14px;
          padding: 13px;
        }
        .flow-step strong {
          display: block;
          color: var(--ink);
          margin-top: 4px;
          font-size: 14px;
        }
        .rule-weight-stack {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.84);
          border-radius: 18px;
          padding: 18px;
          box-shadow: 0 18px 40px rgba(16, 24, 32, 0.08);
        }
        .report-score-panel {
          min-height: 164px;
          padding: 14px 12px;
          align-content: center;
          gap: 8px;
        }
        .report-score-panel .score-pill {
          width: 84px;
          height: 84px;
          font-size: 27px;
        }
        .rule-weight-row + .rule-weight-row {
          margin-top: 15px;
        }
        .rule-weight-meta {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          color: #344054;
          font-size: 13px;
          font-weight: 700;
          margin-bottom: 7px;
        }
        .rule-weight-meta strong {
          font-family: "Noto Serif SC", serif;
          color: var(--ink);
          font-size: 18px;
        }
        .rule-weight-bar {
          height: 10px;
          background: #ece8df;
          border-radius: 999px;
          overflow: hidden;
        }
        .rule-weight-fill {
          display: block;
          height: 100%;
          border-radius: 999px;
        }
        .rule-weight-fill.rule-tone-finance, .rule-module-card.rule-tone-finance {
          --rule-color: #ef3f2d;
          --rule-soft: #fff0ec;
        }
        .rule-weight-fill.rule-tone-equity, .rule-module-card.rule-tone-equity {
          --rule-color: #4338ca;
          --rule-soft: #f0efff;
        }
        .rule-weight-fill.rule-tone-region, .rule-module-card.rule-tone-region {
          --rule-color: #0f766e;
          --rule-soft: #e9f8f4;
        }
        .rule-weight-fill.rule-tone-mixed, .rule-module-card.rule-tone-mixed {
          --rule-color: #b54708;
          --rule-soft: #fff4df;
        }
        .rule-weight-fill {
          background: linear-gradient(90deg, var(--rule-color), rgba(239, 63, 45, 0.72));
        }
        .rule-module-card {
          box-sizing: border-box;
          height: 480px;
          border: 1px solid rgba(16, 24, 32, 0.12);
          border-top: 4px solid var(--rule-color);
          background: linear-gradient(180deg, var(--rule-soft), rgba(255, 255, 255, 0.90) 34%);
          border-radius: 18px;
          padding: 22px;
          box-shadow: 0 14px 34px rgba(16, 24, 32, 0.08);
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        .rule-card-head {
          display: flex;
          justify-content: space-between;
          gap: 18px;
          align-items: flex-start;
          margin-bottom: 12px;
        }
        .rule-card-head h3 {
          margin: 4px 0 0 0;
          font-size: 23px;
        }
        .rule-weight-number {
          color: var(--rule-color);
          font-family: "Noto Serif SC", serif;
          font-size: 42px;
          line-height: 1;
        }
        .rule-card-facts {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 14px 0;
        }
        .rule-card-facts span {
          border: 1px solid rgba(16, 24, 32, 0.12);
          background: rgba(255, 255, 255, 0.74);
          border-radius: 999px;
          padding: 5px 10px;
          color: #344054;
          font-size: 12px;
          font-weight: 700;
        }
        .rule-summary {
          color: #344054;
          font-size: 13px;
          line-height: 1.7;
          margin: 0 0 12px 0;
        }
        .rule-stat-row {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 10px;
          margin: 16px 0 18px 0;
        }
        .rule-stat {
          border-top: 1px solid var(--line);
          padding-top: 10px;
        }
        .rule-list {
          margin: 0;
          padding-left: 18px;
          color: #344054;
          line-height: 1.9;
          overflow-wrap: anywhere;
        }
        .level-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
        }
        .level-item {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.78);
          border-radius: 16px;
          padding: 16px;
        }
        .level-item[data-level="0"] {
          border-color: rgba(15, 118, 110, 0.28);
          background: #ecfbf7;
        }
        .level-item[data-level="1"] {
          border-color: rgba(239, 63, 45, 0.24);
          background: #fff0ec;
        }
        .level-item[data-level="2"] {
          border-color: rgba(181, 71, 8, 0.24);
          background: #fff4df;
        }
        .level-item[data-level="3"] {
          border-color: rgba(71, 84, 103, 0.18);
          background: #f3f5f7;
        }
        .level-score {
          color: var(--accent);
          font-family: "Noto Serif SC", serif;
          font-size: 24px;
          margin-bottom: 6px;
        }
        .validation-entry-card {
          margin-top: 34px;
          border: 1px solid rgba(16, 24, 32, 0.14);
          border-left: 5px solid var(--accent);
          background:
            linear-gradient(90deg, rgba(16, 24, 32, 0.035) 1px, transparent 1px),
            linear-gradient(180deg, rgba(16, 24, 32, 0.03) 1px, transparent 1px),
            rgba(255, 255, 255, 0.86);
          background-size: 24px 24px, 24px 24px, auto;
          border-radius: 0 18px 18px 0;
          padding: 22px 24px;
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 22px;
          align-items: center;
          box-shadow: 0 18px 42px rgba(16, 24, 32, 0.08);
        }
        .validation-entry-card h3 {
          margin: 2px 0 8px 0;
          font-size: 25px;
        }
        .validation-entry-card p {
          margin: 0;
          color: #475467;
          line-height: 1.7;
        }
        .validation-entry-action {
          border: 1px solid rgba(239, 63, 45, 0.28);
          background: #fff0ec;
          color: var(--accent-dark);
          border-radius: 999px;
          padding: 10px 15px;
          font-size: 13px;
          font-weight: 900;
          white-space: nowrap;
        }
        .validation-hero {
          margin: 0 -2rem 36px -2rem;
          padding: 46px 2rem 30px 2rem;
          color: #5b2b24;
          background:
            linear-gradient(90deg, rgba(181, 71, 8, 0.07) 1px, transparent 1px),
            linear-gradient(180deg, rgba(15, 118, 110, 0.055) 1px, transparent 1px),
            linear-gradient(135deg, #fff8ef 0%, #fbfdf6 52%, #e9f7f3 100%);
          background-size: 28px 28px, 28px 28px, auto;
          border-bottom: 1px solid rgba(181, 71, 8, 0.16);
          box-shadow: 0 18px 48px rgba(181, 71, 8, 0.08);
        }
        .validation-hero .section-kicker {
          color: #d92d20;
          margin-top: 0;
        }
        .validation-hero-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(230px, 310px);
          gap: 34px;
          align-items: end;
        }
        .validation-title {
          font-family: "Noto Serif SC", "Songti SC", serif;
          font-size: clamp(44px, 6vw, 76px);
          line-height: 1.08;
        }
        .validation-hero p,
        .validation-intro p,
        .validation-peer-section p {
          max-width: 840px;
          line-height: 1.85;
        }
        .validation-hero p {
          color: #5f4b45;
          font-size: 15px;
          margin: 18px 0 0 0;
        }
        .validation-proof-panel {
          border: 1px solid rgba(181, 71, 8, 0.18);
          background: rgba(255, 255, 255, 0.68);
          border-radius: 18px;
          padding: 20px;
          box-shadow:
            0 18px 40px rgba(181, 71, 8, 0.10),
            inset 0 1px rgba(255, 255, 255, 0.82);
        }
        .validation-proof-panel span,
        .validation-proof-panel em {
          display: block;
          color: #7a5d54;
          font-size: 12px;
          font-style: normal;
          font-weight: 800;
        }
        .validation-proof-panel strong {
          display: block;
          color: #b42318;
          font-family: "Noto Serif SC", serif;
          font-size: 66px;
          line-height: 1;
          margin: 8px 0;
        }
        .validation-proof-strip {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-top: 30px;
        }
        .validation-proof-strip span {
          border: 1px solid rgba(181, 71, 8, 0.18);
          background: rgba(255, 255, 255, 0.58);
          border-radius: 999px;
          padding: 7px 11px;
          color: #6f4a40;
          font-size: 12px;
          font-weight: 850;
        }
        .validation-intro,
        .validation-peer-section {
          margin: 0 0 24px 0;
        }
        .validation-intro p,
        .validation-peer-section p {
          color: #475467;
          margin-top: -10px;
        }
        .validation-case-stack {
          display: grid;
          gap: 26px;
          margin: 18px 0 42px 0;
        }
        .validation-case {
          border: 1px solid rgba(16, 24, 32, 0.14);
          background: rgba(255, 255, 255, 0.88);
          border-radius: 18px;
          padding: 24px;
          box-shadow: 0 22px 54px rgba(16, 24, 32, 0.10);
          overflow: hidden;
          position: relative;
        }
        .validation-case::before {
          content: "";
          position: absolute;
          inset: 0 0 auto 0;
          height: 6px;
          background: var(--validation-color);
        }
        .validation-trend-up {
          --validation-color: #d92d20;
          --validation-soft: #fff0ec;
          --validation-text: #b42318;
        }
        .validation-trend-down {
          --validation-color: #039855;
          --validation-soft: #ecfdf3;
          --validation-text: #027a48;
        }
        .validation-case-head {
          display: flex;
          justify-content: space-between;
          gap: 22px;
          align-items: flex-start;
          margin-bottom: 22px;
        }
        .validation-case-kicker {
          color: var(--muted);
          font-size: 12px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .validation-case h2 {
          margin: 5px 0 8px 0;
          font-size: clamp(30px, 4vw, 46px);
        }
        .validation-case-head p {
          margin: 0;
          color: #344054;
          font-size: 15px;
          font-weight: 800;
        }
        .validation-trend-badge {
          border: 1px solid color-mix(in srgb, var(--validation-color) 32%, transparent);
          background: var(--validation-soft);
          color: var(--validation-text);
          border-radius: 999px;
          padding: 8px 12px;
          font-size: 12px;
          font-weight: 900;
          white-space: nowrap;
        }
        .validation-score-pair {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(150px, 0.58fr) minmax(0, 1fr);
          gap: 14px;
          align-items: stretch;
          margin-bottom: 18px;
        }
        .validation-score-block,
        .validation-arrow-panel {
          border: 1px solid rgba(148, 163, 184, 0.22);
          background: rgba(248, 250, 252, 0.82);
          border-radius: 16px;
          padding: 18px;
          min-width: 0;
        }
        .validation-score-block span,
        .validation-score-block em,
        .validation-arrow-panel span {
          display: block;
          color: var(--muted);
          font-size: 12px;
          font-style: normal;
          font-weight: 850;
          overflow-wrap: anywhere;
        }
        .validation-score-block strong {
          display: block;
          color: var(--ink);
          font-family: "Noto Serif SC", serif;
          font-size: clamp(34px, 5vw, 58px);
          line-height: 1.05;
          margin: 10px 0 7px 0;
          font-variant-numeric: tabular-nums;
        }
        .validation-arrow-panel {
          display: grid;
          place-items: center;
          text-align: center;
          background:
            linear-gradient(180deg, var(--validation-soft), rgba(255, 255, 255, 0.92));
        }
        .validation-arrow {
          color: var(--validation-color);
          font-size: 70px;
          line-height: 0.9;
          font-family: "Noto Serif SC", serif;
        }
        .validation-delta {
          color: var(--validation-text);
          font-family: "Noto Serif SC", serif;
          font-size: 25px;
          font-weight: 900;
          font-variant-numeric: tabular-nums;
        }
        .validation-fact-table {
          width: 100%;
          border-collapse: separate;
          border-spacing: 0;
          border: 1px solid rgba(148, 163, 184, 0.24);
          border-radius: 14px;
          overflow: hidden;
          background: rgba(255, 255, 255, 0.78);
        }
        .validation-fact-table th,
        .validation-fact-table td {
          border-bottom: 1px solid rgba(148, 163, 184, 0.20);
          padding: 12px 14px;
          line-height: 1.65;
          vertical-align: top;
          text-align: left;
        }
        .validation-fact-table tr:last-child th,
        .validation-fact-table tr:last-child td {
          border-bottom: 0;
        }
        .validation-fact-table th {
          width: 112px;
          color: var(--validation-text);
          background: var(--validation-soft);
          font-size: 13px;
          white-space: nowrap;
        }
        .validation-fact-table td {
          color: #344054;
          font-size: 13px;
        }
        .validation-source-links {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .validation-source-links a {
          border: 1px solid rgba(16, 24, 32, 0.12);
          background: #ffffff;
          border-radius: 999px;
          color: var(--validation-text);
          font-size: 12px;
          font-weight: 850;
          padding: 5px 9px;
          text-decoration: none;
        }
        .validation-peer-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 12px;
          margin-top: 14px;
        }
        .validation-peer-group {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          border-radius: 16px;
          padding: 16px;
        }
        .validation-peer-group strong {
          display: block;
          color: var(--ink);
          margin-bottom: 11px;
          line-height: 1.45;
        }
        .validation-peer-group div {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .validation-peer-group span {
          border: 1px solid rgba(16, 24, 32, 0.12);
          background: #f8fafc;
          border-radius: 999px;
          padding: 6px 9px;
          color: #344054;
          font-size: 12px;
          font-weight: 800;
        }
        .mixed-status-section {
          margin-top: 64px;
          padding-top: 8px;
        }
        .mixed-status-head {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(220px, 300px);
          gap: 22px;
          align-items: end;
          margin-bottom: 18px;
        }
        .mixed-status-copy {
          max-width: 760px;
          color: #4d5a61;
          font-size: 14px;
          line-height: 1.8;
          margin-top: -12px;
        }
        .mixed-threshold-card {
          border-left: 4px solid var(--accent);
          background: rgba(255, 255, 255, 0.78);
          border-radius: 0 16px 16px 0;
          padding: 15px 18px;
          box-shadow: 0 14px 32px rgba(16, 24, 32, 0.07);
        }
        .mixed-threshold-card span {
          display: block;
          color: var(--muted);
          font-size: 12px;
          font-weight: 700;
        }
        .mixed-threshold-card strong {
          display: block;
          font-family: "Noto Serif SC", serif;
          font-size: 24px;
          margin-top: 5px;
        }
        .mixed-status-stats {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          margin-bottom: 14px;
        }
        .mixed-stat-card {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.82);
          border-radius: 16px;
          padding: 16px 18px;
          min-height: 104px;
          box-shadow: 0 14px 30px rgba(16, 24, 32, 0.06);
        }
        .mixed-stat-card span,
        .mixed-stat-card em {
          display: block;
          color: var(--muted);
          font-size: 12px;
          font-style: normal;
          line-height: 1.5;
        }
        .mixed-stat-card strong {
          display: block;
          font-family: "Noto Serif SC", serif;
          font-size: 30px;
          line-height: 1.15;
          margin: 9px 0 6px 0;
          color: var(--ink);
        }
        .mixed-status-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 16px;
          align-items: stretch;
        }
        .mixed-chart-card {
          border: 1px solid var(--line);
          background: rgba(255, 255, 255, 0.86);
          border-radius: 18px;
          padding: 20px;
          min-height: 278px;
          box-shadow: 0 16px 36px rgba(16, 24, 32, 0.07);
          overflow: hidden;
        }
        .mixed-chart-card-focus {
          background:
            linear-gradient(90deg, rgba(16, 24, 32, 0.035) 1px, transparent 1px),
            linear-gradient(180deg, rgba(16, 24, 32, 0.03) 1px, transparent 1px),
            rgba(255, 255, 255, 0.88);
          background-size: 24px 24px, 24px 24px, auto;
        }
        .mixed-card-title {
          font-family: "Noto Serif SC", serif;
          font-size: 21px;
          margin-bottom: 14px;
        }
        .mixed-donut-wrap {
          display: grid;
          grid-template-columns: 170px minmax(0, 1fr);
          gap: 22px;
          align-items: center;
        }
        .mixed-donut {
          width: 170px;
          aspect-ratio: 1;
          border-radius: 999px;
          display: grid;
          place-items: center;
          box-shadow: inset 0 0 0 1px rgba(16, 24, 32, 0.08), 0 18px 36px rgba(16, 24, 32, 0.10);
        }
        .mixed-donut > div {
          width: 94px;
          aspect-ratio: 1;
          border-radius: 999px;
          display: grid;
          place-items: center;
          align-content: center;
          background: #fffdfa;
          color: var(--ink);
          box-shadow: 0 0 0 1px rgba(16, 24, 32, 0.08);
        }
        .mixed-donut strong {
          font-family: "Noto Serif SC", serif;
          font-size: 25px;
          line-height: 1;
        }
        .mixed-donut span {
          color: var(--muted);
          font-size: 11px;
          margin-top: 4px;
        }
        .mixed-status-legend {
          display: grid;
          gap: 10px;
        }
        .mixed-legend-row {
          display: grid;
          grid-template-columns: 12px minmax(0, 1fr) auto;
          gap: 9px;
          align-items: center;
          border-bottom: 1px solid var(--line);
          padding-bottom: 9px;
          color: #344054;
          font-size: 13px;
        }
        .mixed-legend-row strong {
          color: var(--ink);
          font-size: 12px;
        }
        .mixed-dot {
          width: 10px;
          height: 10px;
          border-radius: 999px;
        }
        .mixed-trend-chart svg {
          width: 100%;
          height: auto;
          display: block;
        }
        .mixed-grid line {
          stroke: rgba(16, 24, 32, 0.10);
          stroke-dasharray: 3 5;
        }
        .mixed-grid text,
        .mixed-year-axis text {
          fill: var(--muted);
          font-size: 10px;
        }
        .mixed-year-axis text {
          text-anchor: middle;
        }
        .mixed-series polyline {
          fill: none;
          stroke: var(--series-color);
          stroke-width: 3.5;
          stroke-linecap: round;
          stroke-linejoin: round;
        }
        .mixed-series circle {
          fill: #fffdfa;
          stroke: var(--series-color);
          stroke-width: 3;
        }
        .mixed-mini-legend,
        .mixed-hist-notes {
          display: flex;
          flex-wrap: wrap;
          gap: 10px 14px;
          align-items: center;
          margin-top: 8px;
          color: var(--muted);
          font-size: 12px;
        }
        .mixed-mini-legend span {
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .mixed-mini-legend i {
          width: 20px;
          height: 3px;
          border-radius: 999px;
        }
        .mixed-histogram {
          display: grid;
          gap: 12px;
        }
        .mixed-hist-bars {
          height: 168px;
          display: flex;
          align-items: end;
          gap: 6px;
          padding: 8px 0 20px 0;
          border-bottom: 1px solid var(--line);
        }
        .mixed-hist-bar {
          position: relative;
          flex: 1;
          min-width: 0;
          background: linear-gradient(180deg, rgba(106, 174, 214, 0.92), rgba(46, 134, 171, 0.78));
          border-radius: 5px 5px 0 0;
          box-shadow: inset 0 1px rgba(255, 255, 255, 0.45);
        }
        .mixed-hist-bar span {
          position: absolute;
          left: 50%;
          bottom: calc(100% + 4px);
          transform: translateX(-50%);
          color: var(--muted);
          font-size: 10px;
          white-space: nowrap;
        }
        .mixed-hist-bar em {
          position: absolute;
          left: 50%;
          bottom: -20px;
          transform: translateX(-50%) rotate(-26deg);
          transform-origin: top center;
          color: var(--muted);
          font-size: 9px;
          font-style: normal;
          white-space: nowrap;
        }
        .mixed-metrics-chart {
          min-height: 206px;
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 12px;
          align-items: end;
        }
        .mixed-metric-group {
          display: grid;
          grid-template-rows: 150px auto;
          gap: 9px;
          min-width: 0;
        }
        .mixed-metric-bars {
          display: flex;
          align-items: end;
          justify-content: center;
          gap: 5px;
          border-bottom: 1px solid var(--line);
          padding: 0 4px;
        }
        .mixed-metric-bar {
          width: 22%;
          min-width: 9px;
          border-radius: 4px 4px 0 0;
          position: relative;
          box-shadow: inset 0 1px rgba(255, 255, 255, 0.46);
        }
        .mixed-metric-bar span {
          position: absolute;
          left: 50%;
          bottom: calc(100% + 5px);
          transform: translateX(-50%);
          background: rgba(16, 24, 32, 0.88);
          color: white;
          border-radius: 6px;
          padding: 4px 6px;
          font-size: 10px;
          white-space: nowrap;
          opacity: 0;
          pointer-events: none;
          transition: opacity 160ms ease;
        }
        .mixed-metric-bar:hover span {
          opacity: 1;
        }
        .mixed-metric-label {
          color: #344054;
          font-size: 11px;
          line-height: 1.35;
          text-align: center;
          min-height: 31px;
          overflow-wrap: anywhere;
        }
        .mixed-empty {
          min-height: 180px;
          display: grid;
          place-items: center;
          color: var(--muted);
          border: 1px dashed var(--line);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.52);
        }
        .mixed-module-layout {
          position: relative;
          display: grid;
          grid-template-columns: minmax(280px, 0.72fr) minmax(0, 1.28fr);
          gap: 26px;
          align-items: start;
          isolation: isolate;
        }
        .mixed-module-layout::before {
          content: "";
          position: absolute;
          inset: -14px -18px auto -18px;
          height: 210px;
          border-radius: 28px;
          background:
            radial-gradient(circle at 12% 14%, rgba(37, 99, 235, 0.09), transparent 32%),
            radial-gradient(circle at 88% 20%, rgba(15, 170, 165, 0.10), transparent 34%);
          pointer-events: none;
          z-index: -1;
        }
        .mixed-breakdown-card,
        .mixed-shareholder-card {
          margin-bottom: 22px;
          min-width: 0;
          box-sizing: border-box;
          max-width: 100%;
          position: relative;
          overflow: hidden;
          border-color: rgba(148, 163, 184, 0.24);
          background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(255, 255, 255, 0.82)),
            radial-gradient(circle at 0 0, rgba(37, 99, 235, 0.07), transparent 26%);
          box-shadow:
            0 26px 62px rgba(15, 23, 42, 0.10),
            0 1px 0 rgba(255, 255, 255, 0.82) inset;
        }
        .mixed-breakdown-card::before,
        .mixed-shareholder-card::before {
          content: "";
          position: absolute;
          inset: 0 0 auto 0;
          height: 4px;
          background: linear-gradient(90deg, #2563eb, #42c3e6 52%, #fb5a1e);
        }
        .mixed-shareholder-card::before {
          background: linear-gradient(90deg, #2563eb, #7c5ce7 58%, #fb5a1e);
        }
        .mixed-shareholder-card {
          padding-bottom: 22px;
        }
        .mixed-shareholder-card > h3:first-child {
          margin-bottom: 12px;
        }
        .mixed-shareholder-card .mixed-panel-copy {
          max-width: 720px;
          margin-bottom: 14px;
        }
        .mixed-panel-copy {
          color: #475569;
          font-size: 13px;
          line-height: 1.8;
          margin: -4px 0 20px 0;
        }
        .mixed-score-lines {
          display: grid;
          gap: 15px;
          margin-bottom: 20px;
        }
        .mixed-score-line {
          display: grid;
          grid-template-columns: 40px minmax(0, 1fr);
          gap: 13px;
          align-items: center;
        }
        .mixed-score-icon {
          width: 40px;
          height: 40px;
          border-radius: 999px;
          display: grid;
          place-items: center;
          color: #2563eb;
          background: linear-gradient(145deg, #eaf2ff, #f8fbff);
          box-shadow:
            0 8px 18px rgba(37, 99, 235, 0.14),
            0 0 0 1px rgba(37, 99, 235, 0.10) inset;
        }
        .mixed-score-symbol {
          width: 22px;
          height: 22px;
          fill: none;
          stroke: currentColor;
          stroke-width: 2.1;
          stroke-linecap: round;
          stroke-linejoin: round;
        }
        .mixed-score-icon-capital,
        .mixed-score-icon-diversity,
        .mixed-score-icon-balance {
          color: #2563eb;
          background: linear-gradient(145deg, #eaf2ff, #f8fbff);
        }
        .mixed-score-icon-integration {
          color: #0faaa5;
          background: #e8f8f5;
          box-shadow:
            0 8px 18px rgba(15, 170, 165, 0.16),
            0 0 0 1px rgba(15, 170, 165, 0.12) inset;
        }
        .mixed-score-icon-governance {
          color: #7c5ce7;
          background: #f0edff;
          box-shadow:
            0 8px 18px rgba(124, 92, 231, 0.15),
            0 0 0 1px rgba(124, 92, 231, 0.12) inset;
        }
        .mixed-score-main {
          min-width: 0;
        }
        .mixed-score-meta {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          color: #344054;
          font-size: 14px;
          margin-bottom: 8px;
        }
        .mixed-score-meta strong {
          overflow-wrap: anywhere;
          line-height: 1.35;
        }
        .mixed-score-meta span {
          display: grid;
          justify-items: end;
          color: #1d4ed8;
          font-weight: 900;
          white-space: nowrap;
          line-height: 1.05;
        }
        .mixed-score-meta span em {
          margin-top: 4px;
          color: #64748b;
          font-size: 11px;
          font-style: normal;
          font-weight: 800;
        }
        .mixed-progress-track {
          height: 10px;
          border-radius: 999px;
          background: #e8edf3;
          overflow: hidden;
          box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.06);
        }
        .mixed-progress-track span {
          display: block;
          height: 100%;
          border-radius: 999px;
          background: linear-gradient(90deg, #2563eb, #42c3e6);
        }
        .mixed-score-line:nth-child(4) .mixed-progress-track span {
          background: linear-gradient(90deg, #0faaa5, #4ddbd1);
        }
        .mixed-metric-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 9px;
          margin: 8px 0 20px 0;
        }
        .mixed-metric-chips span {
          border: 1px solid rgba(16, 24, 32, 0.10);
          background: rgba(248, 250, 252, 0.88);
          border-radius: 999px;
          padding: 7px 11px;
          color: #667085;
          font-size: 12px;
          font-weight: 700;
        }
        .mixed-metric-chips strong {
          color: var(--ink);
          margin-left: 4px;
        }
        .mixed-data-table {
          width: 100%;
          box-sizing: border-box;
          border-collapse: separate;
          border-spacing: 0;
          overflow: hidden;
          border: 1px solid rgba(148, 163, 184, 0.22);
          border-radius: 14px;
          background: rgba(255, 255, 255, 0.84);
          font-size: 12.5px;
        }
        .mixed-data-table th,
        .mixed-data-table td {
          border-bottom: 1px solid rgba(148, 163, 184, 0.20);
          border-right: 1px solid rgba(148, 163, 184, 0.16);
          padding: 10px 10px;
          vertical-align: middle;
          color: #344054;
          line-height: 1.45;
        }
        .mixed-data-table th {
          color: #1e293b;
          background: linear-gradient(180deg, rgba(248, 250, 252, 0.96), rgba(241, 245, 249, 0.82));
          font-weight: 800;
          white-space: nowrap;
        }
        .mixed-data-table tr:last-child td {
          border-bottom: 0;
        }
        .mixed-data-table td:last-child,
        .mixed-data-table th:last-child {
          border-right: 0;
        }
        .mixed-shareholder-table td:nth-child(2) {
          color: var(--ink);
          font-weight: 700;
        }
        .mixed-shareholder-table {
          table-layout: fixed;
          width: 100%;
          min-width: 0;
          font-size: 11.8px;
        }
        .mixed-shareholder-col-rank { width: 52px; }
        .mixed-shareholder-col-name { width: auto; }
        .mixed-shareholder-col-ratio { width: 86px; }
        .mixed-shareholder-col-nature { width: 128px; }
        .mixed-shareholder-col-category { width: 132px; }
        .mixed-shareholder-table th,
        .mixed-shareholder-table td {
          padding: 6px 8px;
          line-height: 1.22;
        }
        .mixed-shareholder-table thead th {
          position: sticky;
          top: 0;
          z-index: 2;
          box-shadow: 0 1px 0 rgba(148, 163, 184, 0.20);
        }
        .mixed-shareholder-table td:first-child,
        .mixed-shareholder-table td:nth-child(3),
        .mixed-shareholder-table td:nth-child(4),
        .mixed-shareholder-table td:nth-child(5) {
          text-align: center;
          white-space: nowrap;
          font-variant-numeric: tabular-nums;
        }
        .mixed-shareholder-table tbody tr {
          height: var(--mixed-shareholder-row-height);
        }
        .mixed-holder-name,
        .mixed-holder-compact {
          display: block;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .mixed-holder-name {
          width: 100%;
          max-width: 100%;
          overflow-x: auto;
          overflow-y: hidden;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: thin;
          scrollbar-color: rgba(37, 99, 235, 0.32) transparent;
          text-overflow: clip;
          color: var(--ink);
          cursor: ew-resize;
          font-weight: 850;
        }
        .mixed-holder-name-text {
          display: inline-block;
          min-width: max-content;
          padding-right: 14px;
        }
        .mixed-holder-name::-webkit-scrollbar {
          height: 4px;
        }
        .mixed-holder-name::-webkit-scrollbar-track {
          background: transparent;
        }
        .mixed-holder-name::-webkit-scrollbar-thumb {
          background: rgba(37, 99, 235, 0.28);
          border-radius: 999px;
        }
        .mixed-table-scroll {
          width: 100%;
          max-width: 100%;
          min-width: 0;
          border-radius: 12px;
          margin-top: 4px;
          overscroll-behavior-x: contain;
          scrollbar-width: thin;
          scrollbar-color: rgba(37, 99, 235, 0.38) rgba(226, 232, 240, 0.72);
        }
        .mixed-shareholder-scroll {
          --mixed-shareholder-row-height: 34px;
          --mixed-shareholder-head-height: 36px;
          max-height: calc(var(--mixed-shareholder-head-height) + (var(--mixed-shareholder-row-height) * 7));
          overflow-y: auto;
          overflow-x: hidden;
          border: 1px solid rgba(148, 163, 184, 0.18);
          background: rgba(255, 255, 255, 0.76);
        }
        .mixed-shareholder-scroll .mixed-shareholder-table {
          border: 0;
          border-radius: 12px;
        }
        .mixed-table-scroll::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .mixed-table-scroll::-webkit-scrollbar-track {
          background: rgba(226, 232, 240, 0.72);
          border-radius: 999px;
        }
        .mixed-table-scroll::-webkit-scrollbar-thumb {
          background: rgba(37, 99, 235, 0.38);
          border-radius: 999px;
        }
        .mixed-empty-cell {
          text-align: center;
          color: var(--muted) !important;
          padding: 24px !important;
        }
        .mixed-subtitle {
          margin-top: 16px !important;
          margin-bottom: 12px !important;
          font-size: 20px !important;
        }
        .mixed-holder-stack {
          display: flex;
          height: 42px;
          overflow: hidden;
          border-radius: 12px;
          background: #eef2f6;
          border: 1px solid rgba(148, 163, 184, 0.18);
          box-shadow: inset 0 1px 2px rgba(15, 23, 42, 0.05);
        }
        .mixed-holder-segment {
          display: grid;
          place-items: center;
          color: #ffffff;
          font-size: 13px;
          font-weight: 900;
          min-width: 0;
          white-space: nowrap;
          box-shadow: inset -1px 0 rgba(255, 255, 255, 0.54);
        }
        .mixed-holder-legend {
          display: flex;
          flex-wrap: wrap;
          gap: 10px 16px;
          margin: 13px 0 20px 0;
          color: #475467;
          font-size: 12px;
        }
        .mixed-holder-legend span {
          display: inline-flex;
          align-items: center;
          gap: 7px;
        }
        .mixed-holder-legend i {
          width: 9px;
          height: 9px;
          border-radius: 999px;
          display: inline-block;
        }
        .mixed-holder-empty,
        .mixed-module-empty p {
          color: var(--muted);
          line-height: 1.7;
        }
        .mixed-insight-grid {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(230px, 0.86fr);
          gap: 16px;
        }
        .mixed-note-box {
          border: 1px solid rgba(148, 163, 184, 0.22);
          background: rgba(255, 255, 255, 0.78);
          border-radius: 16px;
          padding: 16px 18px;
        }
        .mixed-note-box h4 {
          margin: 0 0 10px 0;
          color: var(--ink);
          font-size: 16px;
        }
        .mixed-note-box ul {
          margin: 0;
          padding-left: 18px;
          color: #344054;
          line-height: 1.85;
          font-size: 13px;
        }
        .mixed-signal-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 10px 11px;
        }
        .mixed-signal-tags span {
          border: 1px solid rgba(37, 99, 235, 0.26);
          background: linear-gradient(180deg, #f7fbff, #eef5ff);
          color: #1d4ed8;
          border-radius: 10px;
          padding: 8px 12px;
          font-size: 13px;
          font-weight: 800;
          box-shadow: 0 8px 18px rgba(37, 99, 235, 0.08);
        }
        div[data-testid="stButton"] > button {
          border-radius: 999px;
          border: 1px solid rgba(16, 24, 32, 0.16);
          background: #ffffff;
          color: var(--ink);
          min-height: 38px;
          font-weight: 600;
          transition: all 160ms ease;
        }
        div[data-testid="stButton"] > button:hover {
          border-color: var(--accent);
          color: var(--accent);
          box-shadow: 0 8px 18px rgba(239, 63, 45, 0.12);
        }
        div[data-testid="stTextInput"] input {
          border-radius: 999px;
          min-height: 48px;
        }
        @media (max-width: 760px) {
          .hero, .detail-hero, .report-hero, .module-hero, .rule-hero, .topbar {
            margin-left: -1rem;
            margin-right: -1rem;
            padding-left: 1rem;
            padding-right: 1rem;
          }
          .feature-card {
            min-height: 300px;
          }
          .hero-rule-link {
            position: static;
            display: inline-flex;
            margin-bottom: 18px;
          }
          .rule-hero-grid, .report-hero-grid, .module-hero-grid, .evidence-grid, .module-detail-grid, .level-grid,
          .validation-entry-card, .validation-hero-grid, .validation-score-pair, .validation-peer-grid,
          .mixed-status-head, .mixed-status-grid, .mixed-donut-wrap, .mixed-module-layout, .mixed-insight-grid {
            grid-template-columns: 1fr;
          }
          .validation-case-head {
            display: grid;
          }
          .validation-arrow {
            font-size: 56px;
          }
          .validation-fact-table th {
            width: 88px;
            white-space: normal;
          }
          .report-stats, .rule-stat-row, .normalization-flow, .mixed-status-stats, .mixed-metrics-chart {
            grid-template-columns: 1fr;
          }
          .mixed-chart-card {
            min-height: auto;
          }
          .mixed-donut {
            margin: 0 auto;
          }
          .mixed-hist-bars {
            gap: 4px;
          }
          .mixed-hist-bar span,
          .mixed-hist-bar em {
            display: none;
          }
          .mixed-data-table {
            font-size: 12px;
          }
          .mixed-data-table th,
          .mixed-data-table td {
            padding: 8px 7px;
          }
          .mixed-shareholder-scroll {
            overflow-x: auto;
          }
          .mixed-table-scroll .mixed-shareholder-table {
            min-width: 620px;
            white-space: nowrap;
          }
          .hero-signal-panel {
            grid-template-columns: minmax(142px, 170px) 136px;
          }
          .reform-status-stack {
            grid-template-columns: 1fr;
          }
          .finance-radar-card {
            min-height: auto;
          }
          .finance-radar-head {
            display: grid;
          }
          .finance-radar-score {
            text-align: left;
          }
          .finance-radar-metrics {
            grid-template-columns: 1fr;
          }
          .governance-card-head {
            display: grid;
          }
        }
        @media (max-width: 520px) {
          .hero-signal-panel {
            grid-template-columns: 1fr;
            padding-top: 0;
          }
          .reform-status-stack {
            grid-template-columns: 1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_bar() -> None:
    data_source = data_source_label()
    st.markdown(
        f"""
        <div class="topbar">
          <div class="brand">
            <div class="brand-mark">混</div>
            <div>
              <div>混改潜力 · 评分</div>
              <div class="brand-sub">SOE REFORM INDEX</div>
            </div>
          </div>
          <div class="nav-note">Python + Streamlit · {h(data_source)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_source_label() -> str:
    return "MongoDB 云端" if get_setting("MONGODB_URI") else "本地备份"


def render_navigation_controls() -> None:
    labels = navigation_control_labels(st.session_state.get("page", "home"))
    if not labels:
        return
    cols = st.columns([1, 7])
    with cols[0]:
        if st.button(labels[0], key="global-back", width="stretch"):
            go_back()


def route_label(route: dict) -> str:
    page = route.get("page", "home")
    if page == "home":
        return "首页"
    if page == "search":
        return "公司搜索"
    if page == "province":
        return f"省份榜单 · {route.get('selected_province', '')}"
    if page == "company":
        return f"公司详情 · {route.get('selected_company_code', '')}"
    if page == "module":
        module_key = route.get("selected_module", "finance")
        module_name = MODULE_META.get(module_key, {}).get("label", module_key)
        return f"模块二级页 · {module_name}"
    if page == "validation":
        return "模型验证案例"
    return "评分规则"


def render_sidebar() -> None:
    st.sidebar.title("导航")
    nav_items = [
        ("首页", "home"),
        ("公司搜索", "search"),
        ("省份榜单", "province"),
        ("公司详情", "company"),
        ("评分规则", "method"),
    ]
    for label, page in nav_items:
        if st.sidebar.button(label, key=f"nav-{page}", width="stretch"):
            if sidebar_navigation_clears_history(page):
                go_home()
            else:
                navigate(page)
    st.sidebar.divider()
    if st.sidebar.button("刷新缓存", width="stretch"):
        st.cache_data.clear()
        st.rerun()


def render_home() -> None:
    with st.spinner("正在读取云端榜单..."):
        top_companies = cached_top_companies(10)
        provinces = cached_provinces()

    st.markdown(
        """
        <section class="hero">
          <a class="hero-rule-link" href="?page=method" target="_self">评分规则 ↗</a>
          <div class="kicker">Issue 01 · A 股混改潜力研究</div>
          <div class="headline">谁会是下一个<br><span class="accent">混合所有制改革</span>的样本?</div>
          <div class="subline">
            综合财务引资潜力、治理合规资质、区域国资适配、混改程度评分四大模块，为全部 A 股上市公司生成 0-100 的混改潜力评分。
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    search_col, button_col = st.columns([5, 1])
    with search_col:
        query = st.text_input(
            "搜索",
            placeholder="输入公司简称、证券代码或省份，例如：600519、华信、广东",
            label_visibility="collapsed",
            key="home_search",
        )
    with button_col:
        if st.button("搜索", key="home_search_button", width="stretch"):
            route_query(query)

    render_hot_provinces(provinces[:10])

    metric_cols = st.columns(4)
    stats = [
        ("榜单展示", f"{len(top_companies)} 家"),
        ("覆盖省份", f"{len(provinces)} 省"),
        ("评分模块", "4 维度"),
        ("更新频次", "季度"),
    ]
    for col, (label, value) in zip(metric_cols, stats):
        col.markdown(
            f"""
            <div class="stat-card">
              <div class="stat-label">{h(label)}</div>
              <div class="stat-value">{h(value)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not top_companies:
        st.info("当前数据库里没有可展示公司。")
        render_mixed_status_dashboard()
        return

    st.markdown('<div class="section-kicker">Ranking · Top 10</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">本期混改潜力榜</div>', unsafe_allow_html=True)

    featured = top_companies[0]
    left, right = st.columns([1.05, 1.6], gap="large")
    with left:
        st.markdown(featured_card_html(featured), unsafe_allow_html=True)
        if st.button("查看第一名公司详情", key="featured-detail", width="stretch"):
            navigate("company", selected_company_code=featured["code"])
    with right:
        for row_start in range(1, len(top_companies), 2):
            cols = st.columns(2)
            for offset, col in enumerate(cols):
                index = row_start + offset
                if index >= len(top_companies):
                    continue
                company = top_companies[index]
                with col:
                    st.markdown(rank_card_html(company, index + 1), unsafe_allow_html=True)
                    if st.button(
                        f"进入 {short_name(company)}",
                        key=f"top-company-{company['code']}",
                        width="stretch",
                    ):
                        navigate("company", selected_company_code=company["code"])

    st.markdown('<div class="section-kicker">By Province</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">按省份浏览</div>', unsafe_allow_html=True)
    render_province_buttons(provinces)
    render_mixed_status_dashboard()


def render_mixed_status_dashboard() -> None:
    try:
        dashboard = cached_mixed_status_dashboard()
    except (FileNotFoundError, ValueError, OSError) as exc:
        st.info(f"混改状态观察数据暂未就绪：{h(exc)}")
        return
    st.markdown(mixed_status_dashboard_html(dashboard), unsafe_allow_html=True)


def mixed_status_dashboard_html(dashboard: dict[str, Any]) -> str:
    slices = list(dashboard.get("status_slices", []))
    total = int(dashboard.get("total", 0))
    median = float(dashboard.get("mixed_score_median", 0))
    threshold = float(dashboard.get("completion_threshold", 0))
    return compact_html(f"""
    <section class="mixed-status-section">
      <div class="section-kicker">Mixed Reform Status</div>
      <div class="mixed-status-head">
        <div>
          <div class="section-title">国企混改状态观察</div>
          <div class="mixed-status-copy">
            基于 {total} 家国有上市公司最新股权结构数据，观察三阶段混改分布、年度状态迁移与已混改公司的得分结构。
          </div>
        </div>
        <div class="mixed-threshold-card">
          <span>完成阈值 {threshold:.2f}</span>
          <strong>中位数 {median:.2f}</strong>
        </div>
      </div>
      <div class="mixed-status-stats">{mixed_status_stat_cards_html(slices, total)}</div>
      <div class="mixed-status-grid">
        <div class="mixed-chart-card mixed-chart-card-focus">
          <div class="mixed-card-title">三阶段状态分布</div>
          <div class="mixed-donut-wrap">
            <div class="mixed-donut" style="{h(mixed_donut_style(slices))}">
              <div><strong>{total}</strong><span>家公司</span></div>
            </div>
            <div class="mixed-status-legend">{mixed_status_legend_html(slices)}</div>
          </div>
        </div>
        <div class="mixed-chart-card">
          <div class="mixed-card-title">年度变化趋势</div>
          {mixed_annual_trend_svg(dashboard.get("annual_trends", []), slices)}
        </div>
        <div class="mixed-chart-card">
          <div class="mixed-card-title">已混改公司综合得分分布</div>
          {mixed_score_histogram_html(dashboard.get("score_histogram", []), threshold, median)}
        </div>
        <div class="mixed-chart-card">
          <div class="mixed-card-title">三阶段核心指标均值对比</div>
          {mixed_metric_averages_html(dashboard.get("metric_averages", []))}
        </div>
      </div>
    </section>
    """)


def compact_html(html_text: str) -> str:
    return "".join(line.strip() for line in html_text.splitlines())


def validation_case_delta(case: dict) -> dict[str, Any]:
    start_score = float(case["start_score"])
    end_score = float(case["end_score"])
    value = round(end_score - start_score, 3)
    return {
        "value": value,
        "direction": "up" if value >= 0 else "down",
        "label": f"{value:+.3f}",
    }


def validation_method_entry_html() -> str:
    return compact_html(
        """
        <section class="validation-entry-card">
          <div>
            <div class="section-kicker">Model Backtest</div>
            <h3>模型验证案例</h3>
            <p>用真实混改前后样本验证评分解释力，把评分规则从“怎么算”延伸到“为什么有效”。</p>
          </div>
          <div class="validation-entry-action">进入验证案例页</div>
        </section>
        """
    )


def validation_fact_rows_html(case: dict) -> str:
    rows = [
        ("混改时间", case["time"]),
        ("混改内容", case["content"]),
        ("混改类型", case["type"]),
        ("模型解释", case["explanation"]),
    ]
    if case.get("source"):
        rows.append(("事实口径", case["source"]))
    rendered_rows = [
        f"<tr><th>{h(label)}</th><td>{h(value)}</td></tr>"
        for label, value in rows
    ]
    source_links = case.get("source_links") or []
    if source_links:
        links = "".join(
            f'<a href="{h(item["url"])}" target="_blank" rel="noopener noreferrer">{h(item["label"])}</a>'
            for item in source_links
        )
        rendered_rows.append(f'<tr><th>公告链接</th><td><div class="validation-source-links">{links}</div></td></tr>')
    return "".join(rendered_rows)


def validation_case_card_html(case: dict) -> str:
    delta = validation_case_delta(case)
    direction = delta["direction"]
    arrow = "&#8599;" if direction == "up" else "&#8600;"
    trend_word = "上升" if direction == "up" else "下降"
    return compact_html(
        f"""
        <section class="validation-case validation-trend-{direction}">
          <div class="validation-case-head">
            <div>
              <div class="validation-case-kicker">{h(case["period_label"])} · {h(case["code"])}</div>
              <h2>{h(case["name"])}</h2>
              <p>{h(case["headline"])}</p>
            </div>
            <div class="validation-trend-badge">{h(trend_word)}趋势</div>
          </div>
          <div class="validation-score-pair">
            <div class="validation-score-block">
              <span>{h(case["start_label"])}</span>
              <strong>{h(case["start_score"])}</strong>
              <em>{h(case["start_year"])} Score</em>
            </div>
            <div class="validation-arrow-panel">
              <div class="validation-arrow">{arrow}</div>
              <div class="validation-delta">{h(delta["label"])}</div>
              <span>分数变化</span>
            </div>
            <div class="validation-score-block">
              <span>{h(case["end_label"])}</span>
              <strong>{h(case["end_score"])}</strong>
              <em>{h(case["end_year"])} Score</em>
            </div>
          </div>
          <div class="validation-evidence-grid">
            <table class="validation-fact-table">
              <tbody>{validation_fact_rows_html(case)}</tbody>
            </table>
          </div>
        </section>
        """
    )


def validation_peer_cases_html() -> str:
    groups = []
    for group in MODEL_VALIDATION_PEER_CASES:
        chips = "".join(f"<span>{h(item)}</span>" for item in group["items"])
        groups.append(
            f"""
            <div class="validation-peer-group">
              <strong>{h(group["title"])}</strong>
              <div>{chips}</div>
            </div>
            """
        )
    return compact_html(f'<section class="validation-peer-grid">{"".join(groups)}</section>')


def model_validation_page_html() -> str:
    cards = "".join(validation_case_card_html(case) for case in MODEL_VALIDATION_CASES)
    return compact_html(
        f"""
        <section class="validation-hero">
          <div class="validation-hero-grid">
            <div>
              <div class="section-kicker">Model Validation</div>
              <div class="validation-title">模型验证案例</div>
              <p>
                为了测试我们模型的准确性，我们小组深入研究、回测了过去十年内A股市场约200余家公司的混改前后数据，
                从而得出我们的模型效果显著。仅利用最近三年的数据来看，结果也能很好说明模型的作用和意义。
              </p>
            </div>
            <div class="validation-proof-panel">
              <span>研究样本</span>
              <strong>200+</strong>
              <em>A股公司混改前后回测</em>
            </div>
          </div>
          <div class="validation-proof-strip">
            <span>过去十年</span>
            <span>约200余家</span>
            <span>最近三年</span>
            <span>混改前后评分对照</span>
          </div>
        </section>
        <section class="validation-intro">
          <div class="section-kicker">Case Evidence</div>
          <div class="section-title">两个方向，验证同一套模型解释力</div>
          <p>
            分数变化不是简单判断好坏，而是观察企业在混改之后的新增改革空间、治理稳定性与财务基础是否发生结构性变化。
            中国股市语义中，红色表示上涨，绿色表示下跌；下方趋势色彩按这一规则呈现。
          </p>
        </section>
        <div class="validation-case-stack">{cards}</div>
        <section class="validation-peer-section">
          <div class="section-kicker">Similar Cases</div>
          <div class="section-title">类似样本提示</div>
          <p>以下案例作为同类混改路径提示，页面只做点名，不展开评分。</p>
          {validation_peer_cases_html()}
        </section>
        """
    )


def mixed_status_stat_cards_html(slices: list[dict[str, Any]], total: int) -> str:
    cards = [
        f"""
        <div class="mixed-stat-card">
          <span>样本公司</span>
          <strong>{total}</strong>
          <em>最新一期入库样本</em>
        </div>
        """
    ]
    for item in slices:
        cards.append(
            f"""
            <div class="mixed-stat-card">
              <span>{h(item.get("label", ""))}</span>
              <strong>{h(item.get("percent_label", ""))}</strong>
              <em>{h(item.get("count", 0))} 家 · {h(item.get("percent_label", ""))}</em>
            </div>
            """
        )
    return "".join(cards)


def mixed_donut_style(slices: list[dict[str, Any]]) -> str:
    segments = []
    cursor = 0.0
    for item in slices:
        percent = float(item.get("percent", 0))
        start = cursor
        end = min(100.0, cursor + percent)
        segments.append(f"{item.get('color', '#98A2B3')} {start:.1f}% {end:.1f}%")
        cursor = end
    return f"background: conic-gradient({', '.join(segments)});"


def mixed_status_legend_html(slices: list[dict[str, Any]]) -> str:
    rows = []
    for item in slices:
        rows.append(
            f"""
            <div class="mixed-legend-row">
              <span class="mixed-dot" style="background:{h(item.get("color", "#98A2B3"))};"></span>
              <span>{h(item.get("label", ""))}</span>
              <strong>{h(item.get("count", 0))} 家 · {h(item.get("percent_label", ""))}</strong>
            </div>
            """
        )
    return "".join(rows)


def mixed_annual_trend_svg(trends: list[dict[str, Any]], slices: list[dict[str, Any]]) -> str:
    if not trends:
        return '<div class="mixed-empty">暂无年度趋势数据</div>'
    status_colors = {item.get("label"): item.get("color", "#98A2B3") for item in slices}
    width, height = 360, 178
    left, right, top, bottom = 34, 18, 18, 38
    plot_width = width - left - right
    plot_height = height - top - bottom
    years = [int(item["year"]) for item in trends]

    def xy(index: int, value: float) -> tuple[float, float]:
        x = left + (plot_width * index / max(1, len(trends) - 1))
        y = top + plot_height - (max(0.0, min(100.0, value)) / 100 * plot_height)
        return x, y

    grid = []
    for value in [0, 25, 50, 75, 100]:
        y = top + plot_height - (value / 100 * plot_height)
        grid.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" />')
        grid.append(f'<text x="4" y="{y + 4:.1f}">{value}</text>')
    year_labels = []
    for index, year in enumerate(years):
        x, _ = xy(index, 0)
        year_labels.append(f'<text class="mixed-year-label" x="{x:.1f}" y="{height - 12}">{year}</text>')

    lines = []
    for status in ["尚未发生混改", "正在进行混改", "已经完成混改"]:
        points = [xy(index, float(row[status])) for index, row in enumerate(trends)]
        point_text = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        color = status_colors.get(status, "#98A2B3")
        circles = "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2"><title>{h(status)} {trends[index]["year"]}: {float(trends[index][status]):.1f}%</title></circle>'
            for index, (x, y) in enumerate(points)
        )
        lines.append(f'<g style="--series-color:{h(color)}"><polyline points="{point_text}" />{circles}</g>')
    return (
        '<div class="mixed-trend-chart">'
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="三阶段状态年度变化趋势">'
        f'<g class="mixed-grid">{"".join(grid)}</g>'
        f'<g class="mixed-year-axis">{"".join(year_labels)}</g>'
        f'<g class="mixed-series">{"".join(lines)}</g>'
        "</svg>"
        '<div class="mixed-mini-legend">'
        f'{mixed_inline_legend_item("尚未发生混改", status_colors.get("尚未发生混改", "#98A2B3"))}'
        f'{mixed_inline_legend_item("正在进行混改", status_colors.get("正在进行混改", "#98A2B3"))}'
        f'{mixed_inline_legend_item("已经完成混改", status_colors.get("已经完成混改", "#98A2B3"))}'
        "</div></div>"
    )


def mixed_inline_legend_item(label: str, color: str) -> str:
    return f'<span><i style="background:{h(color)};"></i>{h(label)}</span>'


def mixed_score_histogram_html(histogram: list[dict[str, Any]], threshold: float, median: float) -> str:
    if not histogram:
        return '<div class="mixed-empty">暂无得分分布数据</div>'
    bars = []
    max_count = max(int(item.get("count", 0)) for item in histogram) or 1
    for item in histogram:
        height = max(4, float(item.get("height", 0)))
        bars.append(
            f"""
            <div class="mixed-hist-bar" style="height:{height:.1f}%;">
              <span>{h(item.get("count", 0))}</span>
              <em>{h(item.get("label", ""))}</em>
            </div>
            """
        )
    return f"""
    <div class="mixed-histogram" style="--max-count:{max_count};">
      <div class="mixed-hist-bars">{"".join(bars)}</div>
      <div class="mixed-hist-notes">
        <span>完成阈值 {threshold:.2f}</span>
        <span>中位数 {median:.2f}</span>
      </div>
    </div>
    """


def mixed_metric_averages_html(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<div class="mixed-empty">暂无指标均值数据</div>'
    metric_labels = [metric["label"] for metric in rows[0].get("metrics", [])]
    groups = []
    for metric_index, label in enumerate(metric_labels):
        bars = []
        for row in rows:
            metric = row["metrics"][metric_index]
            bars.append(
                f"""
                <div class="mixed-metric-bar" style="height:{max(4, float(metric.get("height", 0))):.1f}%;background:{h(row.get("color", "#98A2B3"))};">
                  <span>{h(row.get("status", ""))}: {float(metric.get("value", 0)):.2f}</span>
                </div>
                """
            )
        groups.append(
            f"""
            <div class="mixed-metric-group">
              <div class="mixed-metric-bars">{"".join(bars)}</div>
              <div class="mixed-metric-label">{h(label)}</div>
            </div>
            """
        )
    return f'<div class="mixed-metrics-chart">{"".join(groups)}</div>'


def render_hot_provinces(provinces: list[str]) -> None:
    if not provinces:
        return
    st.caption("热门省份")
    render_province_buttons(provinces[:8], prefix="hot")


def render_province_buttons(provinces: list[str], prefix: str = "province") -> None:
    for row_start in range(0, len(provinces), 6):
        cols = st.columns(6)
        for index, province in enumerate(provinces[row_start : row_start + 6]):
            with cols[index]:
                if st.button(province, key=f"{prefix}-{province}", width="stretch"):
                    navigate("province", selected_province=province)


def featured_card_html(company: dict) -> str:
    return f"""
    <div class="feature-card">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div class="feature-rank">01</div>
        <div class="score-pill" style="width:72px;height:72px;font-size:20px;">{score(company):.1f}</div>
      </div>
      <div>
        <div class="meta" style="color:rgba(255,255,255,0.78);">{h(company.get('industry'))} · {h(company.get('province'))}</div>
        <div style="font-family:'Noto Serif SC',serif;font-size:42px;line-height:1.1;margin-top:10px;">{h(short_name(company))}</div>
        <div style="opacity:.82;margin-top:8px;">{h(company.get('code'))} · {h(company.get('stateAttribute'))}</div>
        <div style="margin-top:18px;font-size:13px;line-height:1.8;">{h(reason_items(company.get('highlights'), '暂无亮点说明')[0])}</div>
      </div>
    </div>
    """


def rank_card_html(company: dict, rank: int) -> str:
    return f"""
    <div class="rank-card">
      <div style="display:flex;gap:14px;align-items:center;">
        <div class="rank-number">{rank:02d}</div>
        <div style="flex:1;min-width:0;">
          <div class="company-title">{h(short_name(company))}</div>
          <div class="meta">{h(company.get('province'))} · {h(company.get('industry'))}</div>
        </div>
        <div style="text-align:right;">
          <div class="small-score">{score(company):.1f}</div>
          <div class="meta">Score</div>
        </div>
      </div>
    </div>
    """


def route_query(query: str) -> None:
    text = (query or "").strip()
    if not text:
        st.warning("请输入公司、代码或省份。")
        return
    result = cached_search(text)
    if result["type"] == "province":
        navigate("province", selected_province=result["province"])
    if result["type"] == "company":
        navigate("company", selected_company_code=result["company"]["code"])
    st.session_state["last_search_query"] = text
    st.session_state["last_search_result"] = result
    navigate("search")


def render_search_page() -> None:
    st.markdown('<div class="section-kicker">Search</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">公司与省份搜索</div>', unsafe_allow_html=True)
    query = st.text_input(
        "输入公司名称、简称、股票代码或省份",
        value=st.session_state.get("last_search_query", ""),
        placeholder="例如：600004、白云机场、广东省",
    )
    if st.button("开始搜索", key="search-page-button"):
        result = cached_search(query.strip())
        st.session_state["last_search_query"] = query.strip()
        st.session_state["last_search_result"] = result

    result = st.session_state.get("last_search_result")
    if not result:
        st.info("请输入关键词开始查询。")
        return

    if result["type"] == "province":
        st.success(f"识别为省份：{result['province']}，共 {result['count']} 家入池公司。")
        if st.button("查看该省份榜单", key="search-province-link"):
            navigate("province", selected_province=result["province"])
    elif result["type"] == "company":
        company = result["company"]
        st.markdown(rank_card_html(company, 1), unsafe_allow_html=True)
        if st.button("进入公司详情", key="search-company-link"):
            navigate("company", selected_company_code=company["code"])
    elif result["type"] == "candidates":
        st.dataframe(company_table_rows(result["companies"]), width="stretch", hide_index=True)
        for company in result["companies"]:
            if st.button(
                f"{short_name(company)} · {company.get('code')}",
                key=f"candidate-{company.get('code')}",
            ):
                navigate("company", selected_company_code=company["code"])
    else:
        st.warning("没有找到匹配的公司或省份。")


def render_province_page() -> None:
    provinces = cached_provinces()
    selected = st.session_state.get("selected_province") or (provinces[0] if provinces else "")
    st.markdown('<div class="section-kicker">Province Ranking</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">{h(selected)} 混改潜力榜</div>', unsafe_allow_html=True)
    if not provinces:
        st.info("暂无省份数据。")
        return

    province = st.selectbox(
        "切换省份",
        provinces,
        index=provinces.index(selected) if selected in provinces else 0,
    )
    st.session_state["selected_province"] = province
    with st.spinner(f"正在读取 {province} 公司榜单..."):
        companies = cached_province_companies(province)

    st.metric("入池公司数量", len(companies))
    st.dataframe(company_table_rows(companies), width="stretch", hide_index=True)
    if companies:
        selected_company = st.selectbox(
            "选择公司进入详情",
            companies,
            format_func=lambda item: f"{short_name(item)} · {item.get('code')}",
        )
        if st.button("进入公司详情", key="province-company-detail"):
            navigate("company", selected_company_code=selected_company["code"])


def render_company_page() -> None:
    code = st.session_state.get("selected_company_code", "600004")
    try:
        company = cached_company_detail(code)
    except Exception as exc:
        st.error(f"读取公司详情失败：{exc}")
        return

    render_company_hero(company)
    render_module_cards(company)
    render_company_evidence(company)


MIXED_STATUS_ENGLISH_COPY = {
    "已经完成混改": "Mixed reform completed",
    "正在进行混改": "Mixed reform in progress",
    "潜在混改企业": "Potential mixed-reform target",
    "尚未发生混改": "No mixed reform yet",
}


def reform_status_cards_html(company: dict) -> str:
    profile = company.get("reformProfile") or {}
    is_state_owned = bool(profile.get("isStateOwned"))
    state_label = "国企" if is_state_owned else "非国企"
    mixed_label = report_value(profile.get("mixedStatusLabel", ""))
    state_class = "state-owned" if is_state_owned else "state-private"
    mixed_class = reform_status_class(mixed_label)
    state_subline = "State-owned enterprise" if is_state_owned else "Non-state-owned enterprise"
    mixed_subline = MIXED_STATUS_ENGLISH_COPY.get(mixed_label, "Mixed reform status")

    return (
        f'<div class="reform-status-stack">'
        f'<div class="reform-info-card {h(state_class)}">'
        f'<div class="reform-info-label">企业状态</div>'
        f'<div class="reform-info-value">{h(state_label)}</div>'
        f'<div class="reform-info-sub">{h(state_subline)}</div>'
        f"</div>"
        f'<div class="reform-info-card {h(mixed_class)}">'
        f'<div class="reform-info-label">混改状态</div>'
        f'<div class="reform-info-value">{h(mixed_label)}</div>'
        f'<div class="reform-info-sub">{h(mixed_subline)}</div>'
        f"</div>"
        f"</div>"
    )


def reform_status_class(label: str) -> str:
    if label == "已经完成混改":
        return "status-complete"
    if label == "正在进行混改":
        return "status-progress"
    if label == "潜在混改企业":
        return "status-potential"
    return "status-none"


def hero_signal_panel_html(company: dict, total_score: float, band: dict) -> str:
    return (
        f'<div class="hero-signal-panel">'
        f"{reform_status_cards_html(company)}"
        f'<div class="score-panel report-score-panel">'
        f'<div class="meta">混改潜力总分</div>'
        f'<div class="score-pill">{total_score:.1f}</div>'
        f'<span class="status-badge {h(band["class"])}">{h(band["label"])}</span>'
        f'<div class="meta" style="margin-top:8px;">满分 100 分</div>'
        f"</div>"
        f"</div>"
    )


def render_company_hero(company: dict) -> None:
    total_score = score(company)
    band = score_band(total_score)
    summary = company_report_summary(company)
    st.markdown(
        f"""
        <section class="report-hero">
          <div class="breadcrumb">{h(company_breadcrumb_text(company))}</div>
          <div class="report-hero-grid">
            <div>
              <div class="kicker" style="color:var(--accent);">Company Reform Portrait</div>
              <div class="detail-name">{h(short_name(company))}</div>
              <div class="detail-meta">{h(company.get('name'))} · {h(company.get('code'))} · 实际控制人：{h(company.get('controller'))}</div>
              <div class="report-label-row">
                <span class="report-chip">{h(report_value(company.get('province')))}</span>
                <span class="report-chip">{h(report_value(company.get('industry')))}</span>
                <span class="report-chip">{h(report_value(company.get('stateAttribute')))}</span>
                <span class="status-badge {h(band['class'])}">{h(band['label'])}</span>
              </div>
              <div class="report-summary">{h(summary)}</div>
              <div class="report-stats">
                <div class="report-stat"><div class="meta">全国排名</div><div class="stat-value">No. {h(company.get('national_rank', '-'))}</div></div>
                <div class="report-stat"><div class="meta">省内排名</div><div class="stat-value">No. {h(company.get('province_rank', '-'))}</div></div>
                <div class="report-stat"><div class="meta">所在地</div><div class="stat-value">{h(report_value(company.get('city'), company.get('province') or '暂未入库'))}</div></div>
              </div>
            </div>
            {hero_signal_panel_html(company, total_score, band)}
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_module_cards(company: dict) -> None:
    st.markdown('<div class="section-kicker">Diagnostic Modules</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">四大模块诊断</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    for col, card in zip(cols, module_cards(company)):
        value = float(card["score"])
        with col:
            st.markdown(
                f"""
                <div class="module-card">
                  <div>
                    <div class="module-card-head">
                      <div>
                        <div class="module-title">{h(card['label'])}</div>
                        <div class="meta">权重 {h(card['weight'])}</div>
                      </div>
                      <span class="status-badge {h(card['band_class'])}">{h(card['band_label'])}</span>
                    </div>
                    <div class="module-summary">{h(card['summary'])}</div>
                  </div>
                  <div>
                    <div style="display:flex;justify-content:space-between;align-items:end;margin-top:16px;">
                      <div class="small-score">{value:.1f}</div>
                      <div class="meta">/ 100</div>
                    </div>
                    <div class="bar"><span style="width:{max(0, min(100, value))}%;"></span></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"进入{card['label']}二级页", key=f"module-{card['key']}", width="stretch"):
                navigate(
                    "module",
                    selected_company_code=company["code"],
                    selected_module=card["key"],
                )


def render_company_evidence(company: dict) -> None:
    st.markdown('<div class="section-kicker">Evidence Review</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">结论依据与风险提示</div>', unsafe_allow_html=True)
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown('<div class="detail-card"><h3>关键加分依据</h3>', unsafe_allow_html=True)
        for item in reason_items(company.get("highlights"), "暂无积极信号"):
            st.markdown(
                f'<div class="note-item"><span class="note-dot">+</span>{h(item)}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

        risks, risk_source = company_risk_items(company)
        st.markdown(
            '<div class="detail-card"><div class="governance-card-head"><h3>主要风险与减分项</h3>'
            f'<span class="governance-source">{h(risk_source)}</span></div>',
            unsafe_allow_html=True,
        )
        for item in risks:
            st.markdown(
                f'<div class="note-item"><span class="note-dot" style="background:#475467;">!</span>{h(item)}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        render_metric_card("财务证据", company.get("financials", {}))
        render_metric_card("股权与信用", company.get("equity", {}))

    if st.button(f"查看 {company.get('province')} 全部入池公司", key="back-province"):
        navigate("province", selected_province=company.get("province", ""))


def render_metric_card(title: str, payload: dict) -> None:
    rows = metric_card_rows(title, payload)
    body = "".join(
        f'<div class="metric-row"><span class="meta">{h(label)}</span><span class="{report_value_class(raw)}">{h(value)}</span></div>'
        for label, value, raw in rows
    )
    st.markdown(f'<div class="detail-card"><h3>{h(title)}</h3>{body}</div>', unsafe_allow_html=True)


def render_module_page() -> None:
    code = st.session_state.get("selected_company_code", "600004")
    module_key = st.session_state.get("selected_module", "finance")
    try:
        company = cached_company_detail(code)
        detail = module_detail(company, module_key)
    except Exception as exc:
        st.error(f"读取模块详情失败：{exc}")
        return

    st.markdown(
        f"""
        <section class="module-hero">
          <div class="breadcrumb">公司详情 / {h(short_name(company))} / {h(detail['label'])}</div>
          <div class="module-hero-grid">
            <div>
              <div class="kicker" style="color:var(--accent);">Module Evidence Page</div>
              <div class="detail-name">{h(detail['title'])}</div>
              <div class="detail-meta">{h(detail['subtitle'])}</div>
              <div class="report-label-row">
                <span class="report-chip">{h(short_name(company))}</span>
                <span class="report-chip">权重 {h(detail['weight'])}</span>
                <span class="status-badge {h(detail['band_class'])}">{h(detail['band_label'])}</span>
              </div>
              <div class="report-summary">{h(detail['report_summary'])}</div>
            </div>
            <div class="score-panel">
              <div class="meta">模块得分 · 权重 {h(detail['weight'])}</div>
              <div class="score-pill">{float(detail['score']):.1f}</div>
              <span class="status-badge {h(detail['band_class'])}">{h(detail['band_label'])}</span>
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if module_key == "finance":
        render_finance_module_detail(detail)
    elif module_key == "equity":
        render_governance_module_detail(detail)
    elif module_key == "mixed":
        st.markdown(mixed_module_detail_html(detail), unsafe_allow_html=True)
        if not detail.get("mixedDegreeProfile"):
            render_generic_module_detail(detail)
    else:
        render_generic_module_detail(detail)

    st.markdown('<div class="section-kicker">Module Switch</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    with cols[0]:
        if st.button("返回公司详情", key="module-back", width="stretch"):
            navigate("company", remember=False, selected_company_code=code)
    for index, (key, label, _) in enumerate(MODULE_LABELS, start=1):
        with cols[index]:
            if st.button(label, key=f"jump-module-{key}", width="stretch"):
                navigate("module", selected_company_code=code, selected_module=key)


def render_generic_module_detail(detail: dict) -> None:
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown('<div class="detail-card"><h3>指标证据表</h3>', unsafe_allow_html=True)
        st.dataframe(detail["rows"], width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="detail-card"><h3>关联说明与信号</h3>', unsafe_allow_html=True)
        for item in detail["notes"]:
            st.markdown(f'<div class="note-item"><span class="note-dot">i</span>{h(item)}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_finance_module_detail(detail: dict) -> None:
    left, right = st.columns([1, 1], gap="large")
    with left:
        st.markdown('<div class="detail-card"><h3>指标证据表</h3>', unsafe_allow_html=True)
        st.dataframe(detail["rows"], width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown(finance_radar_chart_html(detail["rows"]), unsafe_allow_html=True)


def render_governance_module_detail(detail: dict) -> None:
    top_left, top_right = st.columns([1, 1], gap="large")
    with top_left:
        st.markdown('<div class="detail-card"><h3>指标证据表</h3>', unsafe_allow_html=True)
        st.dataframe(detail["rows"], width="stretch", hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with top_right:
        st.markdown(governance_radar_chart_html(detail["rows"]), unsafe_allow_html=True)

    bottom_left, bottom_right = st.columns([1, 1], gap="large")
    with bottom_left:
        st.markdown(
            '<section class="detail-card governance-trend-card">'
            '<h3>治理合规趋势表（近三年）</h3>'
            f'{governance_trend_chart_html(detail.get("governanceTrend", []))}'
            "</section>",
            unsafe_allow_html=True,
        )
    with bottom_right:
        st.markdown(governance_highlights_html(detail), unsafe_allow_html=True)


def render_model_validation_page() -> None:
    st.markdown(model_validation_page_html(), unsafe_allow_html=True)


def render_method_page() -> None:
    sections = scoring_rule_sections()
    st.markdown(
        f"""
        <section class="rule-hero">
          <div class="rule-hero-grid">
            <div>
              <div class="section-kicker" style="margin-top:0;">Scoring Rules</div>
              <div class="section-title">评分规则</div>
              <div class="rule-formula-panel">
                <div class="meta">综合评分公式</div>
                <div class="method-formula">总分 = 财务×40% + 治理×25% + 区域×20% + 混改×15%</div>
                <div class="subline" style="margin-top:16px;">
                  系统使用 Python 读取 MongoDB 云端数据库，在 Python 服务层完成四模块评分计算，并用 Streamlit 展示评分结果。
                  各模块先按原始满分计算，再归一化到 0-100 分，最后按权重合成为公司混改潜力总分。
                </div>
                <div class="normalization-flow">
                  <div class="flow-step"><div class="meta">Step 01</div><strong>原始指标打分</strong></div>
                  <div class="flow-step"><div class="meta">Step 02</div><strong>归一化到 100 分</strong></div>
                  <div class="flow-step"><div class="meta">Step 03</div><strong>按权重合成总分</strong></div>
                </div>
              </div>
            </div>
            <div>
              <div class="meta" style="margin-bottom:10px;">四模块权重占比</div>
              {rule_weight_stack_html(sections)}
            </div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-kicker">Module Weights</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">模块对比</div>', unsafe_allow_html=True)
    for row_start in range(0, len(sections), 2):
        cols = st.columns(2, gap="large")
        for index, section in enumerate(sections[row_start : row_start + 2]):
            with cols[index]:
                st.markdown(rule_module_card_html(section), unsafe_allow_html=True)

    st.markdown('<div class="section-kicker">Potential Level</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">潜力等级</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="method-box" style="margin-bottom:16px;">总分越高，表示公司在财务基础、治理合规、区域适配和既有混改基础上的综合准备度越强。</div>',
        unsafe_allow_html=True,
    )
    st.markdown(potential_level_grid_html(potential_level_rows()), unsafe_allow_html=True)

    st.markdown(validation_method_entry_html(), unsafe_allow_html=True)
    if st.button("进入验证案例页", key="validation-entry-button", width="stretch"):
        navigate("validation")


if __name__ == "__main__":
    main()
