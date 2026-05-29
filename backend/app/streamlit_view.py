from __future__ import annotations

from typing import Iterable


ROUTE_KEYS = ("page", "selected_company_code", "selected_province", "selected_module")

MODULE_LABELS = [
    ("finance", "财务引资潜力", "40%"),
    ("equity", "治理合规资质", "25%"),
    ("region", "区域国资适配", "20%"),
    ("mixed", "混改程度评分", "15%"),
]

MODULE_META = {
    "finance": {
        "label": "财务引资潜力",
        "title": "财务引资潜力二级页",
        "subtitle": "从 Altman Z、债务结构、现金盈利、增长和分红稳定性观察引资基础。",
        "weight": "40%",
        "focus": "Altman Z、债务结构、现金盈利与分红",
    },
    "equity": {
        "label": "治理合规资质",
        "title": "治理合规资质二级页",
        "subtitle": "从股权结构、质押、审计、合规记录和行业地位观察治理资质。",
        "weight": "25%",
        "focus": "股权结构、质押、审计、合规与行业地位",
    },
    "region": {
        "label": "区域国资适配",
        "title": "区域国资适配二级页",
        "subtitle": "结合财政自给率、地方债务率、产业匹配和区域混改活跃度判断适配度。",
        "weight": "20%",
        "focus": "地方财政、债务率、产业匹配与混改活跃度",
    },
    "mixed": {
        "label": "混改程度评分",
        "title": "混改程度评分二级页",
        "subtitle": "从非国有资本进入、股权多样性、制衡、融合和开放治理观察混改程度。",
        "weight": "15%",
        "focus": "非国有资本、股权多样性、制衡、融合与开放治理",
    },
}


SCORING_RULE_SECTIONS = [
    {
        "key": "finance",
        "label": "财务引资潜力",
        "weight": "40%",
        "raw_max": "50",
        "summary": "观察企业资产质量、偿债结构、现金盈利能力、成长性和分红稳定性，判断其对社会资本的吸引基础。",
        "items": ["Altman Z", "资产负债率", "经营现金流/收入", "净利润三年CAGR", "连续分红年数", "有息负债占比"],
    },
    {
        "key": "equity",
        "label": "治理合规资质",
        "weight": "25%",
        "raw_max": "25",
        "summary": "从股权结构、质押风险、审计意见、合规记录和行业地位判断企业治理透明度与合规稳定性。",
        "items": ["股权结构", "股权质押", "审计意见", "合规记录", "行业地位"],
    },
    {
        "key": "region",
        "label": "区域国资适配",
        "weight": "20%",
        "raw_max": "20",
        "summary": "结合地方财政、债务压力、产业政策匹配和区域混改活跃度，判断属地国资推进混改的适配条件。",
        "items": ["财政自给率", "地方政府债务率", "产业匹配度", "区域混改活跃度"],
    },
    {
        "key": "mixed",
        "label": "混改程度评分",
        "weight": "15%",
        "raw_max": "100",
        "summary": "衡量企业已有混改基础，包括非国有资本进入、股权多样性、制衡、融合和开放治理程度。",
        "items": ["非国有资本进入程度", "股权结构多样性", "股权制衡程度", "股权融合程度", "股权开放治理程度"],
    },
]

POTENTIAL_LEVEL_ROWS = [
    {"分数区间": ">=80", "潜力等级": "高潜力"},
    {"分数区间": ">=70", "潜力等级": "中高潜力"},
    {"分数区间": ">=60", "潜力等级": "观察潜力"},
    {"分数区间": "<60", "潜力等级": "低潜力"},
]


def scoring_rule_sections() -> list[dict]:
    return [{**section, "items": list(section["items"])} for section in SCORING_RULE_SECTIONS]


def potential_level_rows() -> list[dict]:
    return [row.copy() for row in POTENTIAL_LEVEL_ROWS]


def _short_name(company: dict) -> str:
    return str(company.get("shortName") or company.get("short_name") or company.get("name") or "")


def _score_value(value: object) -> float:
    try:
        return round(float(value or 0), 1)
    except (TypeError, ValueError):
        return 0.0


def score_band(value: object) -> dict:
    score = _score_value(value)
    if score >= 80:
        return {
            "label": "优势项",
            "tone": "strong",
            "class": "band-strong",
            "summary": "得分处于优势区间，可作为混改潜力判断的主要支撑。",
        }
    if score >= 70:
        return {
            "label": "支撑项",
            "tone": "support",
            "class": "band-support",
            "summary": "得分处于支撑区间，对综合判断形成正向贡献。",
        }
    if score >= 60:
        return {
            "label": "观察项",
            "tone": "watch",
            "class": "band-watch",
            "summary": "得分处于观察区间，需要结合其他证据继续判断。",
        }
    return {
        "label": "风险项",
        "tone": "risk",
        "class": "band-risk",
        "summary": "得分处于风险区间，是当前混改潜力判断中的短板。",
    }


def _module_scores(company: dict) -> list[dict]:
    modules = company.get("modules", {})
    return [
        {
            "key": key,
            "label": label,
            "weight": weight,
            "score": _score_value(modules.get(key, 0)),
        }
        for key, label, weight in MODULE_LABELS
    ]


def _module_summary(label: str, score: float, band: dict, focus: str) -> str:
    return f"{label}得分{score:.1f}，当前属于{band['label']}；重点依据包括{focus}。"


def company_report_summary(company: dict) -> str:
    name = _short_name(company) or "该公司"
    total_score = _score_value(company.get("totalScore", company.get("score", 0)))
    total_band = score_band(total_score)
    modules = _module_scores(company)
    if not modules:
        return f"{name}综合得分{total_score:.1f}，处于{total_band['label']}区间；暂无可用于拆解的模块数据。"

    best = max(modules, key=lambda item: item["score"])
    weakest = min(modules, key=lambda item: item["score"])
    return (
        f"{name}综合得分{total_score:.1f}，处于{total_band['label']}区间；"
        f"{best['label']}贡献最强，{weakest['label']}仍需重点观察。"
    )


def module_cards(company: dict) -> list[dict]:
    cards = []
    for item in _module_scores(company):
        meta = MODULE_META[item["key"]]
        band = score_band(item["score"])
        cards.append(
            {
                **item,
                "band": band,
                "band_label": band["label"],
                "band_class": band["class"],
                "summary": _module_summary(item["label"], item["score"], band, meta["focus"]),
            }
        )
    return cards


def company_table_rows(companies: Iterable[dict]) -> list[dict]:
    rows = []
    for index, company in enumerate(companies, start=1):
        rows.append(
            {
                "排名": index,
                "代码": company.get("code") or company.get("stock_code", ""),
                "公司简称": company.get("shortName") or company.get("short_name", ""),
                "省份": company.get("province", ""),
                "行业": company.get("industry", ""),
                "总分": round(float(company.get("totalScore", company.get("score", 0))), 1),
            }
        )
    return rows


def route_snapshot(state: dict) -> dict:
    return {key: state.get(key, "") for key in ROUTE_KEYS}


def push_route_history(
    history: list[dict], current_route: dict, next_route: dict, max_length: int = 30
) -> list[dict]:
    if route_snapshot(current_route) == route_snapshot(next_route):
        return list(history)
    updated = [*history, route_snapshot(current_route)]
    return updated[-max_length:]


def pop_route_history(history: list[dict]) -> tuple[dict | None, list[dict]]:
    if not history:
        return None, []
    return history[-1], history[:-1]


def module_score_rows(company: dict) -> list[dict]:
    modules = company.get("modules", {})
    return [
        {
            "模块": label,
            "权重": weight,
            "得分": round(float(modules.get(key, 0)), 1),
        }
        for key, label, weight in MODULE_LABELS
    ]


def module_detail(company: dict, module_key: str) -> dict:
    if module_key not in MODULE_META:
        raise KeyError(module_key)

    meta = MODULE_META[module_key]
    modules = company.get("modules", {})
    current_score = _score_value(modules.get(module_key, 0))
    band = score_band(current_score)
    return {
        "key": module_key,
        "label": meta["label"],
        "title": meta["title"],
        "subtitle": meta["subtitle"],
        "weight": meta["weight"],
        "score": current_score,
        "band": band,
        "band_label": band["label"],
        "band_class": band["class"],
        "report_summary": _module_summary(meta["label"], current_score, band, meta["focus"]),
        "rows": _module_rows(company, module_key),
        "notes": _module_notes(company, module_key),
        "governanceTrend": _governance_trend(company) if module_key == "equity" else [],
        "mixedDegreeProfile": company.get("mixedDegreeProfile", {}) if module_key == "mixed" else {},
    }


def _governance_trend(company: dict) -> list[dict]:
    trend = company.get("governanceTrend") or company.get("governance_trend") or []
    rows = []
    for item in trend:
        try:
            year = int(item.get("year"))
            score = round(float(item.get("score", 0)), 1)
        except (TypeError, ValueError, AttributeError):
            continue
        try:
            raw_score = round(float(item.get("rawScore", item.get("raw_score", score / 4))), 2)
        except (TypeError, ValueError):
            raw_score = round(score / 4, 2)
        rows.append(
            {
                "year": year,
                "score": score,
                "rawScore": raw_score,
                "date": str(item.get("date", "")),
            }
        )
    return sorted(rows, key=lambda row: row["year"])


def _module_rows(company: dict, module_key: str) -> list[dict]:
    evidence = company.get("module_details", {}).get(module_key, {}).get("evidence", [])
    if evidence:
        return [
            {
                "指标": str(item.get("label", "")),
                "数值": str(item.get("value", "")),
                "得分": f"{float(item.get('score', 0)):.1f} / {float(item.get('max', 0)):.1f}",
            }
            for item in evidence
        ]
    if module_key == "finance":
        financials = company.get("financials", {})
        return [
            {"指标": "营业收入", "数值": f"{float(financials.get('revenue', 0)):.2f} 亿元"},
            {"指标": "归母净利润", "数值": f"{float(financials.get('netProfit', 0)):.2f} 亿元"},
            {"指标": "资产负债率", "数值": f"{financials.get('assetLiabilityRatio', 0)}%"},
            {"指标": "ROE", "数值": f"{financials.get('roe', 0)}%"},
            {"指标": "经营性现金流", "数值": f"{float(financials.get('cashFlow', 0)):.2f} 亿元"},
        ]
    if module_key == "equity":
        equity = company.get("equity", {})
        return [
            {"指标": "第一大股东", "数值": display_value(equity.get("topShareholderName", ""))},
            {"指标": "第一大股东持股", "数值": f"{equity.get('topShareholderRatio', 0)}%"},
            {"指标": "股权质押率", "数值": f"{equity.get('pledgeRatio', 0)}%"},
            {"指标": "审计意见", "数值": display_value(equity.get("auditOpinion", ""))},
            {"指标": "审计截止日", "数值": display_value(equity.get("auditAccountingDate", ""))},
            {"指标": "审计日期", "数值": display_value(equity.get("auditDate", ""))},
            {"指标": "境内审计事务所", "数值": display_value(equity.get("domesticAuditFirm", ""))},
            {"指标": "签字审计师", "数值": display_value(equity.get("auditor", ""))},
        ]
    if module_key == "region":
        return [
            {"指标": "所在省份", "数值": str(company.get("province", ""))},
            {"指标": "所在城市", "数值": str(company.get("city", ""))},
            {"指标": "实际控制人", "数值": str(company.get("controller", ""))},
            {"指标": "国资属性", "数值": str(company.get("stateAttribute", ""))},
        ]
    return [
        {"指标": "混改程度评分", "数值": f"{company.get('modules', {}).get('mixed', 0)} 分"},
        {"指标": "积极信号数量", "数值": f"{len(company.get('highlights', []))} 条"},
        {"指标": "风险提示数量", "数值": f"{len(company.get('risks', []))} 条"},
    ]


def _module_notes(company: dict, module_key: str) -> list[str]:
    risks = reason_items(company.get("risks"), "暂无风险提示")
    highlights = reason_items(company.get("highlights"), "暂无积极信号")
    if module_key in {"finance", "equity"}:
        return risks
    return highlights


def display_value(value: object, empty_text: str = "暂未入库") -> str:
    text = str(value if value is not None else "").strip()
    if text == "" or text in {"待补充", "None", "nan", "NaN"}:
        return empty_text
    return text


def reason_items(reasons: Iterable[str] | None, empty_text: str) -> list[str]:
    items = [str(reason) for reason in reasons or [] if str(reason).strip()]
    return items or [empty_text]
