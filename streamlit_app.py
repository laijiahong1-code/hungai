from __future__ import annotations

import html
import os
from typing import Any

import streamlit as st

from backend.app.services import (
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
    reason_items,
    pop_route_history,
    push_route_history,
    route_snapshot,
    score_band,
)


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


def main() -> None:
    ensure_state()
    inject_css()
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
    else:
        render_method_page()


def ensure_state() -> None:
    st.session_state.setdefault("page", "home")
    st.session_state.setdefault("selected_company_code", "600004")
    st.session_state.setdefault("selected_province", "")
    st.session_state.setdefault("selected_module", "finance")
    st.session_state.setdefault("nav_history", [])


def navigate(page: str, remember: bool = True, **values: Any) -> None:
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
        ("第一大股东持股", *percent_value("topShareholderRatio")),
        ("股权质押率", *percent_value("pledgeRatio")),
        ("审计意见", report_value(payload.get("auditOpinion", "")), payload.get("auditOpinion", "")),
        ("审计日期", report_value(payload.get("auditDate", "")), payload.get("auditDate", "")),
        (
            "审计事务所",
            report_value(payload.get("domesticAuditFirm", "")),
            payload.get("domesticAuditFirm", ""),
        ),
        ("债务逾期", report_value(payload.get("overdueDebt", "")), payload.get("overdueDebt", "")),
    ]


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
          background:
            radial-gradient(circle at 18% 20%, rgba(255, 232, 176, 0.72), transparent 34%),
            radial-gradient(circle at 78% 25%, rgba(202, 244, 239, 0.86), transparent 34%),
            linear-gradient(120deg, #fffaf0, #f5fff9 48%, #eaf8fb);
          border-bottom: 1px solid rgba(16, 24, 32, 0.08);
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
          grid-template-columns: minmax(0, 1fr) 168px;
          gap: 30px;
          align-items: start;
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
          .hero, .detail-hero, .report-hero, .module-hero, .topbar {
            margin-left: -1rem;
            margin-right: -1rem;
            padding-left: 1rem;
            padding-right: 1rem;
          }
          .feature-card {
            min-height: 300px;
          }
          .report-hero-grid, .module-hero-grid, .evidence-grid, .module-detail-grid {
            grid-template-columns: 1fr;
          }
          .report-stats {
            grid-template-columns: 1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_top_bar() -> None:
    data_source = "MongoDB 云端" if os.environ.get("MONGODB_URI") else "本地备份"
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


def render_navigation_controls() -> None:
    labels = navigation_control_labels(st.session_state.get("page", "home"))
    if not labels:
        return
    cols = st.columns([1, 7])
    with cols[0]:
        if st.button(labels[0], key="global-back", use_container_width=True):
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
    return "方法论"


def render_sidebar() -> None:
    st.sidebar.title("导航")
    nav_items = [
        ("首页", "home"),
        ("公司搜索", "search"),
        ("省份榜单", "province"),
        ("公司详情", "company"),
        ("方法论", "method"),
    ]
    for label, page in nav_items:
        if st.sidebar.button(label, key=f"nav-{page}", use_container_width=True):
            if sidebar_navigation_clears_history(page):
                go_home()
            else:
                navigate(page)
    st.sidebar.divider()
    if st.sidebar.button("刷新缓存", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def render_home() -> None:
    with st.spinner("正在读取云端榜单..."):
        top_companies = cached_top_companies(10)
        provinces = cached_provinces()

    st.markdown(
        """
        <section class="hero">
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
        if st.button("搜索", key="home_search_button", use_container_width=True):
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
        return

    st.markdown('<div class="section-kicker">Ranking · Top 10</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">本期混改潜力榜</div>', unsafe_allow_html=True)

    featured = top_companies[0]
    left, right = st.columns([1.05, 1.6], gap="large")
    with left:
        st.markdown(featured_card_html(featured), unsafe_allow_html=True)
        if st.button("查看第一名公司详情", key="featured-detail", use_container_width=True):
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
                        use_container_width=True,
                    ):
                        navigate("company", selected_company_code=company["code"])

    st.markdown('<div class="section-kicker">By Province</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">按省份浏览</div>', unsafe_allow_html=True)
    render_province_buttons(provinces)


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
                if st.button(province, key=f"{prefix}-{province}", use_container_width=True):
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
        st.dataframe(company_table_rows(result["companies"]), use_container_width=True, hide_index=True)
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
    st.dataframe(company_table_rows(companies), use_container_width=True, hide_index=True)
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
            <div class="score-panel">
              <div class="meta">混改潜力总分</div>
              <div class="score-pill">{total_score:.1f}</div>
              <span class="status-badge {h(band['class'])}">{h(band['label'])}</span>
              <div class="meta" style="margin-top:8px;">满分 100 分</div>
            </div>
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
            if st.button(f"进入{card['label']}二级页", key=f"module-{card['key']}", use_container_width=True):
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

        st.markdown('<div class="detail-card"><h3>主要风险与减分项</h3>', unsafe_allow_html=True)
        for item in reason_items(company.get("risks"), "暂无风险提示"):
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

    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown('<div class="detail-card"><h3>指标证据表</h3>', unsafe_allow_html=True)
        st.dataframe(detail["rows"], use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="detail-card"><h3>关联说明与信号</h3>', unsafe_allow_html=True)
        for item in detail["notes"]:
            st.markdown(f'<div class="note-item"><span class="note-dot">i</span>{h(item)}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-kicker">Module Switch</div>', unsafe_allow_html=True)
    cols = st.columns(5)
    with cols[0]:
        if st.button("返回公司详情", key="module-back", use_container_width=True):
            navigate("company", remember=False, selected_company_code=code)
    for index, (key, label, _) in enumerate(MODULE_LABELS, start=1):
        with cols[index]:
            if st.button(label, key=f"jump-module-{key}", use_container_width=True):
                navigate("module", selected_company_code=code, selected_module=key)


def render_method_page() -> None:
    st.markdown('<div class="section-kicker">Methodology</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-title">评分方法论</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="method-box">
          本系统使用 Python 读取 MongoDB 云端数据库，并在 Python 服务层完成评分计算。
          前端展示使用 Streamlit 编写，符合 Python 课程技术栈。
        </div>
        """,
        unsafe_allow_html=True,
    )
    for key, meta in MODULE_META.items():
        st.markdown(
            f"""
            <div class="detail-card">
              <h3>{h(meta['label'])} · {h(meta['weight'])}</h3>
              <div class="meta">{h(meta['subtitle'])}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
