from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import latest_item, normalize_year, read_csv_rows, stock_code, to_float
from .models import Evidence, ModuleResult


BASE_PARTS = ("财务引资潜力数据", "智能财务机器人数据")


NUMERIC_COLUMNS = {
    "A001000000",
    "A001100000",
    "A002000000",
    "A002100000",
    "A002101000",
    "A002201000",
    "A002203000",
    "A0f2104000",
    "A0b2102000",
    "A0b2103000",
    "A003100000",
    "A003105000",
    "B001100000",
    "B001101000",
    "B001300000",
    "B002000000",
    "B002000101",
    "C001000000",
    "F011201A",
    "F010101A",
    "F010201A",
    "Btperdiv",
    "Atperdiv",
    "Numdiv",
    "DistributionBaseShares",
    "Price1",
}


def build_finance_scores(source_root: Path) -> dict[str, ModuleResult]:
    root = source_root.joinpath(*BASE_PARTS)
    profit = prepare_rows(read_csv_rows(root / "利润表.csv"))
    if not profit:
        return {}
    balance = group_by_stock(prepare_rows(read_csv_rows(root / "资产负债表.csv")))
    profit_groups = group_by_stock(profit)
    cash = group_by_stock(prepare_rows(read_csv_rows(root / "现金流量表（直接法）.csv")))
    ratios = group_by_stock(prepare_rows(read_csv_rows(root / "资产负债率、流动比率、速动比率.csv")))
    dividends = group_by_stock(prepare_rows(read_csv_rows(root / "红利分配文件.csv")))

    results: dict[str, ModuleResult] = {}
    for code, rows in profit_groups.items():
        latest = latest_item(rows)
        if latest is None:
            continue
        year = int(latest["year"])
        summary = summarize_stock(code, year, balance, profit_groups, cash, ratios, dividends)
        results[code] = finance_result(summary)
    return results


def prepare_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        code = stock_code(row.get("Stkcd") or row.get("股票代码") or row.get("证券代码"))
        year = normalize_year(row.get("Finyear") or row.get("Accper"))
        if not code or year is None:
            continue
        clean = {**row, "Stkcd": code, "year": year}
        for column in NUMERIC_COLUMNS:
            if column in clean:
                clean[column] = to_float(clean[column])
        result.append(clean)
    return result


def group_by_stock(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(row["Stkcd"], []).append(row)
    for items in grouped.values():
        items.sort(key=lambda item: item["year"])
    return grouped


def row_for_year(grouped: dict[str, list[dict[str, Any]]], stock: str, year: int) -> dict[str, Any]:
    for row in grouped.get(stock, []):
        if row.get("year") == year:
            return row
    return {}


def dividend_row(grouped: dict[str, list[dict[str, Any]]], stock: str, year: int) -> dict[str, Any]:
    candidates = [row for row in grouped.get(stock, []) if row.get("year") <= year]
    return candidates[-1] if candidates else {}


def value(row: dict[str, Any], key: str) -> float | None:
    return to_float(row.get(key))


def score_altman_z(balance_row: dict[str, Any], profit_row: dict[str, Any], div_row: dict[str, Any]) -> dict[str, Any]:
    ta = value(balance_row, "A001000000")
    if not ta:
        return {"z": None, "score": 0.0}
    current_assets = value(balance_row, "A001100000")
    current_liabilities = value(balance_row, "A002100000")
    total_liabilities = value(balance_row, "A002000000")
    if current_assets is None or current_liabilities is None:
        working_capital = ta - total_liabilities if total_liabilities is not None else None
    else:
        working_capital = current_assets - current_liabilities
    retained = value(balance_row, "A003105000")
    if retained is None:
        retained = value(balance_row, "A003100000")
    ebit = value(profit_row, "B001300000")
    shares = value(div_row, "DistributionBaseShares")
    price = value(div_row, "Price1")
    market_val = shares * price if shares is not None and price is not None else None
    revenue = value(profit_row, "B001100000")
    if revenue is None:
        revenue = value(profit_row, "B001101000")
    if None in (working_capital, retained, ebit, total_liabilities, market_val, revenue) or total_liabilities == 0:
        return {"z": None, "score": 0.0}
    x1 = working_capital / ta
    x2 = retained / ta
    x3 = ebit / ta
    x4 = market_val / total_liabilities
    x5 = revenue / ta
    z_value = 1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5
    if z_value >= 3:
        score = 10.0
    elif z_value >= 2.5:
        score = 8.0
    elif z_value >= 1.8:
        score = 5.0
    else:
        score = 0.0
    return {"z": z_value, "score": score}


def score_debt_ratio(balance_row: dict[str, Any], ratio_row: dict[str, Any]) -> dict[str, Any]:
    ratio = value(ratio_row, "F011201A")
    if ratio is None:
        ta = value(balance_row, "A001000000")
        total_debt = value(balance_row, "A002000000")
        ratio = total_debt / ta if ta and total_debt is not None else None
    if ratio is None:
        return {"ratio": None, "score": 0.0}
    return {"ratio": ratio, "score": max(0.0, min(10.0, 10.0 - 20.0 * abs(ratio - 0.5)))}


def score_operating_cash_profitability(cash_row: dict[str, Any], profit_row: dict[str, Any]) -> dict[str, Any]:
    ocf = value(cash_row, "C001000000")
    revenue = value(profit_row, "B001100000")
    if revenue is None:
        revenue = value(profit_row, "B001101000")
    if ocf is None or not revenue:
        return {"ratio": None, "score": 0.0}
    ratio = ocf / revenue
    if ratio > 0.15:
        score = 10.0
    elif ratio > 0.10:
        score = 8.0
    elif ratio > 0.05:
        score = 5.0
    elif ratio >= 0:
        score = 2.0
    else:
        score = 0.0
    return {"ratio": ratio, "score": score}


def score_net_profit_growth(profit_rows: list[dict[str, Any]], year: int) -> dict[str, Any]:
    candidates = [row for row in profit_rows if row.get("year") <= year]
    values = []
    for row in candidates:
        net_profit = value(row, "B002000101")
        if net_profit is None:
            net_profit = value(row, "B002000000")
        if net_profit is not None:
            values.append((int(row["year"]), net_profit))
    latest_years = sorted({item[0] for item in values})[-3:]
    latest_values = [profit for row_year, profit in values if row_year in latest_years]
    if len(latest_years) != 3 or len(latest_values) < 3:
        return {"cagr": None, "score": 0.0, "years": latest_years}
    start, end = latest_values[0], latest_values[-1]
    if start > 0 and end >= 0:
        cagr = (end / start) ** 0.5 - 1
    elif start == 0:
        cagr = float("inf") if end != 0 else None
    else:
        cagr = (end - start) / abs(start) / 2
    if cagr is None:
        score = 0.0
    elif cagr == float("inf") or cagr > 0.20:
        score = 10.0
    elif cagr > 0.10:
        score = 7.0
    elif cagr > 0:
        score = 4.0
    elif cagr > -0.10:
        score = 1.0
    else:
        score = 0.0
    return {"cagr": cagr, "score": score, "years": latest_years}


def score_dividend_stability(dividend_rows: list[dict[str, Any]], year: int) -> dict[str, Any]:
    rows = [row for row in dividend_rows if row.get("year") <= year]
    years = sorted({int(row["year"]) for row in rows})[-3:]
    consecutive = 0
    for current_year in reversed(years):
        current = [row for row in rows if row["year"] == current_year]
        paid = any(
            (value(row, "Btperdiv") or 0) > 0
            or (value(row, "Atperdiv") or 0) > 0
            or (value(row, "Numdiv") or 0) > 0
            for row in current
        )
        if not paid:
            break
        consecutive += 1
    if consecutive >= 3:
        score = 5.0
    elif consecutive == 2:
        score = 3.0
    elif consecutive == 1:
        score = 1.0
    else:
        score = 0.0
    return {"years": years, "consecutive": consecutive, "score": score}


def score_interest_bearing_debt(balance_row: dict[str, Any]) -> dict[str, Any]:
    total_debt = value(balance_row, "A002000000")
    interest_debt = sum(
        value(balance_row, key) or 0.0
        for key in ["A002101000", "A002201000", "A002203000", "A0f2104000", "A0b2102000", "A0b2103000"]
    )
    ratio = interest_debt / total_debt if total_debt else None
    if ratio is None:
        return {"ratio": None, "score": 0.0, "interest_bearing_debt": interest_debt}
    return {
        "ratio": ratio,
        "score": max(0.0, min(5.0, 5.0 - 5.0 * ratio)),
        "interest_bearing_debt": interest_debt,
    }


def summarize_stock(stock: str, year: int, balance, profit, cash, ratios, dividends) -> dict[str, Any]:
    balance_row = row_for_year(balance, stock, year)
    profit_row = row_for_year(profit, stock, year)
    cash_row = row_for_year(cash, stock, year)
    ratio_row = row_for_year(ratios, stock, year)
    div_row = dividend_row(dividends, stock, year)

    altman = score_altman_z(balance_row, profit_row, div_row)
    debt = score_debt_ratio(balance_row, ratio_row)
    op_cash = score_operating_cash_profitability(cash_row, profit_row)
    growth = score_net_profit_growth(profit.get(stock, []), year)
    dividend = score_dividend_stability(dividends.get(stock, []), year)
    interest = score_interest_bearing_debt(balance_row)
    total = altman["score"] + debt["score"] + op_cash["score"] + growth["score"] + dividend["score"] + interest["score"]
    return {
        "year": year,
        "altman": altman,
        "debt": debt,
        "op_cash": op_cash,
        "growth": growth,
        "dividend": dividend,
        "interest": interest,
        "total": total,
    }


def finance_result(summary: dict[str, Any]) -> ModuleResult:
    evidence = [
        Evidence("Altman Z", format_number(summary["altman"]["z"]), summary["altman"]["score"], 10.0),
        Evidence("资产负债率", format_percent(summary["debt"]["ratio"]), summary["debt"]["score"], 10.0),
        Evidence("经营现金流/收入", format_percent(summary["op_cash"]["ratio"]), summary["op_cash"]["score"], 10.0),
        Evidence("净利润三年CAGR", format_percent(summary["growth"]["cagr"]), summary["growth"]["score"], 10.0),
        Evidence("连续分红年数", f"{summary['dividend']['consecutive']} 年", summary["dividend"]["score"], 5.0),
        Evidence("有息负债占比", format_percent(summary["interest"]["ratio"]), summary["interest"]["score"], 5.0),
    ]
    return ModuleResult("finance", round(float(summary["total"]), 2), evidence)


def format_number(value_: Any) -> str:
    return "无数据" if value_ is None else f"{float(value_):.2f}"


def format_percent(value_: Any) -> str:
    return "无数据" if value_ is None else f"{float(value_) * 100:.1f}%"
