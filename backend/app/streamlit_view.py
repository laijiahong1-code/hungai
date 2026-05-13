from __future__ import annotations

from typing import Iterable


ROUTE_KEYS = ("page", "selected_company_code", "selected_province", "selected_module")

MODULE_LABELS = [
    ("finance", "财务压力", "30%"),
    ("equity", "股权信用", "25%"),
    ("region", "属地适配", "25%"),
    ("policy", "政策案例", "20%"),
]

MODULE_META = {
    "finance": {
        "label": "财务压力",
        "title": "财务压力二级页",
        "subtitle": "从盈利能力、负债压力和现金流表现观察企业推进混改的现实压力。",
        "weight": "30%",
    },
    "equity": {
        "label": "股权信用",
        "title": "股权信用二级页",
        "subtitle": "从股权集中度、质押情况、审计意见和债务逾期观察治理稳定性。",
        "weight": "25%",
    },
    "region": {
        "label": "属地适配",
        "title": "属地适配二级页",
        "subtitle": "结合公司所在地区、国资属性和地方产业方向判断区域匹配程度。",
        "weight": "25%",
    },
    "policy": {
        "label": "政策案例",
        "title": "政策案例二级页",
        "subtitle": "结合政策文本、已混改样本特征和入库规则观察政策信号强弱。",
        "weight": "20%",
    },
}


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
                "属性": company.get("stateAttribute") or company.get("ownership", ""),
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
    return {
        "key": module_key,
        "label": meta["label"],
        "title": meta["title"],
        "subtitle": meta["subtitle"],
        "weight": meta["weight"],
        "score": round(float(modules.get(module_key, 0)), 1),
        "rows": _module_rows(company, module_key),
        "notes": _module_notes(company, module_key),
    }


def _module_rows(company: dict, module_key: str) -> list[dict]:
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
            {"指标": "第一大股东持股", "数值": f"{equity.get('topShareholderRatio', 0)}%"},
            {"指标": "股权质押率", "数值": f"{equity.get('pledgeRatio', 0)}%"},
            {"指标": "审计意见", "数值": str(equity.get("auditOpinion", ""))},
            {"指标": "债务逾期", "数值": str(equity.get("overdueDebt", ""))},
        ]
    if module_key == "region":
        return [
            {"指标": "所在省份", "数值": str(company.get("province", ""))},
            {"指标": "所在城市", "数值": str(company.get("city", ""))},
            {"指标": "实际控制人", "数值": str(company.get("controller", ""))},
            {"指标": "国资属性", "数值": str(company.get("stateAttribute", ""))},
        ]
    return [
        {"指标": "政策信号", "数值": f"{company.get('modules', {}).get('policy', 0)} 分"},
        {"指标": "积极信号数量", "数值": f"{len(company.get('highlights', []))} 条"},
        {"指标": "风险提示数量", "数值": f"{len(company.get('risks', []))} 条"},
    ]


def _module_notes(company: dict, module_key: str) -> list[str]:
    risks = reason_items(company.get("risks"), "暂无风险提示")
    highlights = reason_items(company.get("highlights"), "暂无积极信号")
    if module_key in {"finance", "equity"}:
        return risks
    return highlights


def reason_items(reasons: Iterable[str] | None, empty_text: str) -> list[str]:
    items = [str(reason) for reason in reasons or [] if str(reason).strip()]
    return items or [empty_text]
