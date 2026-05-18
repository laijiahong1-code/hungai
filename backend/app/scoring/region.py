from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import normalize_year, read_xlsx_rows, stock_code, to_float
from .models import Evidence, ModuleResult


BASE_PARTS = ("区域国资匹配度", "区域国资匹配度——代码初稿")


def build_region_scores(source_root: Path) -> dict[str, ModuleResult]:
    root = source_root.joinpath(*BASE_PARTS)
    companies = read_xlsx_rows(root / "A股主板非ST非金融公司所在地_2026-05-07.xlsx", "结果明细")
    if not companies:
        return {}
    fiscal_2023 = province_fiscal_2023(root / "china_prefecture_city_fiscal_gdp_indicators_2023_by_province(2).xlsx")
    fiscal_2024, gdp_2024 = province_fiscal_2024(root / "china_statistical_2024_province_fiscal_gdp_indicators(1).xlsx")
    debt = debt_ratio_by_province(root / "地方负债率（省级）.xls", gdp_2024)
    reform = reform_activity_by_province(root / "企业混改程度表.xlsx", companies)
    cache = load_industry_cache(root / "industry_match_cache.json")

    results: dict[str, ModuleResult] = {}
    for company in companies:
        code = stock_code(company.get("代码") or company.get("股票代码") or company.get("证券代码"))
        if not code:
            continue
        province = str(company.get("所在地省份") or "").strip()
        city = str(company.get("所在地城市") or "").strip()
        province_key = normalize_province(province)
        rate = average_available(fiscal_2023.get(province_key), fiscal_2024.get(province_key))
        debt_ratio = debt.get(province_key)
        match_level = industry_match_level(cache, str(company.get("所属行业") or ""), province, city)
        reform_count = reform.get(province, 0)
        fiscal_score = score_fiscal_self_sufficiency(rate)
        debt_score = score_debt_ratio(debt_ratio)
        industry_score = score_industry_match(match_level)
        activity_score = score_reform_activity(reform_count)
        raw = fiscal_score + debt_score + industry_score + activity_score
        evidence = [
            Evidence("财政自给率", format_percent(rate), fiscal_score, 8.0),
            Evidence("地方政府债务率", format_percent(debt_ratio), debt_score, 6.0),
            Evidence("产业匹配度", match_level or "未匹配", industry_score, 4.0),
            Evidence("区域混改活跃度", f"{int(reform_count)} 家", activity_score, 2.0),
        ]
        results[code] = ModuleResult("region", round(raw, 2), evidence)
    return results


def province_fiscal_2023(path: Path) -> dict[str, float]:
    return {
        normalize_province(row.get("province_name")): value
        for row in read_xlsx_rows(path, "Province_Summary_2023")
        if (value := to_float(row.get("revenue_expenditure_ratio_pct"))) is not None
    }


def province_fiscal_2024(path: Path) -> tuple[dict[str, float], dict[str, float]]:
    fiscal = {}
    gdp = {}
    for row in read_xlsx_rows(path, "Data_2024"):
        province = normalize_province(row.get("city_name"))
        if not province:
            continue
        rate = to_float(row.get("revenue_expenditure_ratio_pct"))
        gdp_value = to_float(row.get("gdp_current_100m_yuan"))
        if rate is not None:
            fiscal[province] = rate
        if gdp_value is not None:
            gdp[province] = gdp_value
    return fiscal, gdp


def debt_ratio_by_province(path: Path, gdp: dict[str, float]) -> dict[str, float]:
    if not path.exists():
        return {}
    fallback = debt_ratio_from_html_text(path, gdp)
    if fallback:
        return fallback
    try:
        import pandas as pd

        tables = pd.read_html(path)
    except Exception:
        return {}
    if not tables:
        return {}
    frame = tables[0]
    if "2024年" not in [str(column) for column in frame.columns]:
        frame.columns = frame.iloc[0]
        frame = frame.iloc[1:].reset_index(drop=True)
    province_col = frame.columns[0]
    result = {}
    for _, row in frame.iterrows():
        province_key = normalize_province(row.get(province_col))
        debt_value = to_float(row.get("2024年"))
        gdp_value = gdp.get(province_key)
        if province_key and debt_value is not None and gdp_value:
            result[province_key] = debt_value / gdp_value * 100.0
    return result


def debt_ratio_from_html_text(path: Path, gdp: dict[str, float]) -> dict[str, float]:
    import re

    text = path.read_text(encoding="utf-8", errors="ignore")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.I | re.S)
    if len(rows) < 2:
        return {}
    result = {}
    for row_html in rows[1:]:
        cells = [
            re.sub(r"<[^>]+>", "", cell).strip()
            for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, flags=re.I | re.S)
        ]
        if len(cells) < 2:
            continue
        province_key = normalize_province(cells[0])
        debt_value = to_float(cells[1])
        gdp_value = gdp.get(province_key)
        if province_key and debt_value is not None and gdp_value:
            result[province_key] = debt_value / gdp_value * 100.0
    return result


def reform_activity_by_province(path: Path, companies: list[dict[str, Any]]) -> dict[str, int]:
    code_to_province = {
        stock_code(row.get("代码") or row.get("股票代码") or row.get("证券代码")): str(row.get("所在地省份") or "")
        for row in companies
    }
    province_codes: dict[str, set[str]] = {}
    for row in read_xlsx_rows(path, "GA_StateOwnedMixedDegree"):
        code = stock_code(row.get("Symbol") or row.get("股票代码") or row.get("证券代码"))
        year = normalize_year(row.get("EndDate"))
        mixed = to_float(row.get("是否发生混改"), 0.0)
        province = code_to_province.get(code, "")
        if code and province and year == 2025 and mixed == 1:
            province_codes.setdefault(province, set()).add(code)
    return {province: len(codes) for province, codes in province_codes.items()}


def load_industry_cache(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return {str(key): str(value) for key, value in payload.items()}


def industry_match_level(cache: dict[str, str], industry: str, province: str, city: str) -> str | None:
    for key in [f"{industry}|{province}|{city}", f"{industry}|{province}|", f"{industry}|{normalize_province(province)}|{city}"]:
        if key in cache:
            return cache[key]
    return None


def normalize_province(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    for suffix in ["壮族自治区", "回族自治区", "维吾尔自治区", "特别行政区", "自治区", "省", "市"]:
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text


def average_available(*values: float | None) -> float | None:
    available = [value for value in values if value is not None]
    if not available:
        return None
    return sum(available) / len(available)


def score_fiscal_self_sufficiency(rate: float | None) -> float:
    if rate is None:
        return 0.0
    return round(max(0.0, min(8.0, 8.0 * (rate / 100.0))), 2)


def score_debt_ratio(ratio: float | None) -> float:
    if ratio is None:
        return 0.0
    return round(max(0.0, min(6.0, 6.0 - 6.0 * (ratio / 120.0))), 2)


def score_industry_match(level: str | None) -> float:
    if level == "省级重点产业":
        return 4.0
    if level == "市级重点产业":
        return 2.0
    return 0.0


def score_reform_activity(count: int | float | None) -> float:
    if count is None:
        return 0.0
    if count >= 10:
        return 2.0
    if count >= 5:
        return 1.0
    return 0.0


def format_percent(value: float | None) -> str:
    return "无数据" if value is None else f"{value:.1f}%"
