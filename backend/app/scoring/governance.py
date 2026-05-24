from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .common import normalize_year, read_xlsx_rows, stock_code, to_float
from .models import Evidence, ModuleResult


BASE_PARTS = ("企业股权评分", "企业股权评分")
TREND_YEARS = {2023, 2024, 2025}


def build_governance_scores(source_root: Path) -> dict[str, ModuleResult]:
    root = source_root.joinpath(*BASE_PARTS)
    data = root / "data"
    structures = build_structure_scores(data / "十大股东.xlsx")
    if not structures:
        return {}
    pledge = build_pledge_scores(data / "股权质押.xlsx")
    audit = build_audit_scores(data / "审计意见.xlsx")
    violations = build_violation_scores(data / "违规信息.xlsx")
    leaders = build_leader_codes(data / "龙头企业.xlsx")

    results: dict[str, ModuleResult] = {}
    for code, structure in structures.items():
        pledge_score = pledge.get(code, 0.0)
        audit_score = audit.get(code, 0.0)
        compliance_score = violations.get(code, 5.0)
        leader_score = 5.0 if code in leaders else 0.0
        raw = structure["score"] + pledge_score + audit_score + compliance_score + leader_score
        evidence = [
            Evidence("股权结构", f"{structure['score']:.1f}/5", structure["score"], 5.0),
            Evidence("股权质押", f"{pledge_score:.1f}/5", pledge_score, 5.0),
            Evidence("审计意见", f"{audit_score:.1f}/5", audit_score, 5.0),
            Evidence("合规记录", f"{compliance_score:.1f}/5", compliance_score, 5.0),
            Evidence("行业地位", f"{leader_score:.1f}/5", leader_score, 5.0),
        ]
        results[code] = ModuleResult("equity", round(raw, 2), evidence)
    return results


def build_governance_trends(source_root: Path) -> dict[str, list[dict[str, Any]]]:
    path = source_root.joinpath(*BASE_PARTS, "result", "企业股权最终评分.xlsx")
    selected: dict[tuple[str, int], dict[str, Any]] = {}
    for row in read_xlsx_rows(path):
        code = stock_code(row.get("股票代码") or row.get("证券代码") or row.get("Stkcd"))
        year = normalize_year(row.get("年份") or row.get("截止日期"))
        raw_score = to_float(row.get("最终总分") or row.get("最终评分"))
        if not code or year not in TREND_YEARS or raw_score is None:
            continue
        date_value = row.get("截止日期") or ""
        date_text = trend_date_text(date_value)
        candidate = {
            "year": year,
            "score": round(max(0.0, min(100.0, raw_score / 25.0 * 100.0)), 1),
            "rawScore": round(float(raw_score), 2),
            "date": date_text,
            "_date_key": date_text,
        }
        key = (code, year)
        current = selected.get(key)
        if current is None or (candidate["_date_key"], candidate["rawScore"]) > (
            current["_date_key"],
            current["rawScore"],
        ):
            selected[key] = candidate

    by_code: dict[str, list[dict[str, Any]]] = {}
    for code, year in sorted(selected):
        item = dict(selected[(code, year)])
        item.pop("_date_key", None)
        by_code.setdefault(code, []).append(item)
    return by_code


def trend_date_text(value: Any) -> str:
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value or "").strip()


def build_structure_scores(path: Path) -> dict[str, dict[str, Any]]:
    rows = read_xlsx_rows(path)
    grouped: dict[tuple[str, int], list[float]] = {}
    for row in rows:
        code = stock_code(row.get("Stkcd") or row.get("股票代码"))
        year = normalize_year(row.get("Reptdt") or row.get("截止日期"))
        ratio = to_float(row.get("S0301b") or row.get("持股比例"))
        if not code or year is None or ratio is None:
            continue
        if ratio >= 1:
            ratio = ratio / 100.0
        grouped.setdefault((code, year), []).append(ratio)

    by_code: dict[str, dict[str, Any]] = {}
    for (code, year), shares in grouped.items():
        metrics = calc_equity_index(shares)
        current = by_code.get(code)
        if current is None or year > current["year"] or (year == current["year"] and metrics["score"] > current["score"]):
            by_code[code] = {"year": year, **metrics}
    return by_code


def calc_equity_index(shares: list[float]) -> dict[str, Any]:
    share_list = sorted([share for share in shares if share > 0], reverse=True)
    if not share_list:
        return {"score": 0.0}
    ratio_sum = sum(share_list)
    cr1 = share_list[0]
    balance = share_list[1] / cr1 if len(share_list) >= 2 and cr1 else 0.0
    hhi = sum(share * share for share in share_list)
    entropy = -sum(share * math.log(share) for share in share_list if share > 0)

    score_cr1 = 5 if 0.3 <= cr1 <= 0.5 else 3 if 0.2 <= cr1 < 0.3 or 0.5 < cr1 <= 0.6 else 1
    score_balance = 5 if balance >= 0.5 else 3 if balance >= 0.2 else 1 if balance > 0 else 0
    score_hhi = 5 if hhi < 0.18 else 3 if hhi < 0.3 else 1
    score_entropy = 5 if entropy >= 1.5 else 3 if entropy >= 0.8 else 1
    score_ratio_sum = (
        5
        if 0.5 <= ratio_sum <= 0.700000001
        else 3
        if 0.4 <= ratio_sum < 0.5 or 0.7 < ratio_sum <= 0.8
        else 1
    )
    raw_score = score_cr1 + score_balance + score_hhi + score_entropy + score_ratio_sum
    return {
        "score": round(raw_score / 5.0, 2),
        "ratio_sum": ratio_sum,
        "cr1": cr1,
        "balance": balance,
        "hhi": hhi,
        "entropy": entropy,
    }


def build_pledge_scores(path: Path) -> dict[str, float]:
    scores = {}
    for row in read_xlsx_rows(path):
        code = stock_code(row.get("股票代码") or row.get("SCode") or row.get("证券代码"))
        ratio = to_float(row.get("质押比例") or row.get("AcPSRaT") or row.get("PSRaT") or row.get("Ple_ShRat"))
        if not code or ratio is None:
            continue
        if ratio >= 1:
            ratio = ratio / 100.0
        scores.setdefault(code, pledge_score(ratio))
    return scores


def pledge_score(ratio: float) -> float:
    if ratio < 0.1:
        return 5.0
    if ratio < 0.3:
        return 3.0
    if ratio < 0.5:
        return 1.0
    return 0.0


def build_audit_scores(path: Path) -> dict[str, float]:
    scores = {}
    for row in read_xlsx_rows(path):
        code = stock_code(row.get("股票代码") or row.get("证券代码") or row.get("Stkcd"))
        opinion = str(row.get("审计意见") or row.get("审计意见类型") or row.get("Audittyp") or row.get("Adtremark") or "")
        if code:
            scores.setdefault(code, audit_score(opinion))
    return scores


def audit_score(opinion: str) -> float:
    if "标准无保留" in opinion:
        return 5.0
    if "强调事项段" in opinion:
        return 2.0
    return 0.0


def build_violation_scores(path: Path) -> dict[str, float]:
    grouped: dict[str, list[str]] = {}
    for row in read_xlsx_rows(path):
        code = stock_code(row.get("股票代码") or row.get("证券代码") or row.get("Stkcd"))
        violation_type = str(row.get("违规类型") or row.get("违规事项") or row.get("处罚类型") or "")
        if code:
            grouped.setdefault(code, []).append(violation_type)
    return {code: violation_score(items) for code, items in grouped.items()}


def violation_score(items: list[str]) -> float:
    major_keywords = ["虚假", "欺诈", "重大", "造假", "内幕交易", "财务造假"]
    if any(any(keyword in item for keyword in major_keywords) for item in items):
        return 0.0
    if not items:
        return 5.0
    if len(items) == 1:
        return 3.0
    return 1.0


def build_leader_codes(path: Path) -> set[str]:
    return {
        code
        for code in (
            stock_code(row.get("股票代码") or row.get("证券代码") or row.get("Stkcd"))
            for row in read_xlsx_rows(path)
        )
        if code
    }
