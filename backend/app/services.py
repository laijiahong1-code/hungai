from __future__ import annotations

import re
from typing import Iterable

from .data import PROVINCE_ALIASES, default_database, load_company_records


SCORE_COLLECTION = "company_scores"
PROVINCE_SCORE_COLLECTION = "province_company_scores"


MODULE_LABELS = {
    "financial": "财务压力",
    "equity": "股权信用",
    "regional": "属地适配",
    "policy": "政策案例",
}

MODULE_WEIGHTS = {
    "financial": 0.30,
    "equity": 0.25,
    "regional": 0.25,
    "policy": 0.20,
}


def _resolve_records(
    records: Iterable[dict] | None = None, companies: Iterable[dict] | None = None
) -> list[dict]:
    if records is not None:
        return list(records)
    if companies is not None:
        return list(companies)
    return load_company_records()


def _materialized_database():
    database = default_database()
    if not all(
        hasattr(database, method)
        for method in ("has_collection", "find_query", "count_documents", "distinct")
    ):
        return None
    if not database.has_collection(SCORE_COLLECTION):
        return None
    return database


def _can_use_materialized(
    records: Iterable[dict] | None = None, companies: Iterable[dict] | None = None
) -> bool:
    return records is None and companies is None


def _active_query(extra: dict | None = None) -> dict:
    query = {"is_st": {"$ne": True}, "is_financial": {"$ne": True}}
    if extra:
        query.update(extra)
    return query


def _clean_scored_doc(record: dict) -> dict:
    public = record.copy()
    public.pop("_id", None)
    public.pop("_search_text", None)
    return public


def _company_list_summary(record: dict) -> dict:
    public = _clean_scored_doc(record)
    return {
        key: public.get(key)
        for key in [
            "code",
            "stock_code",
            "name",
            "shortName",
            "short_name",
            "industry",
            "stateAttribute",
            "totalScore",
            "score",
        ]
    }


def _score_sort() -> list[tuple[str, int]]:
    return [("score", -1), ("stock_code", 1)]


def _query_text(value: str) -> str:
    return value.strip().lower()


def _number(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: object) -> float:
    return round(min(100.0, max(0.0, _number(value))), 1)


def _financial_score(record: dict) -> float:
    financials = record.get("financials", {})
    debt = _number(financials.get("asset_liability_ratio"))
    roe = _number(financials.get("roe"))
    cash_flow = _number(financials.get("cash_flow"))
    net_profit = _number(financials.get("net_profit"))

    debt_component = _clamp_score(debt)
    profit_component = 85.0 if net_profit < 0 else _clamp_score(70 - roe * 2)
    cash_component = 85.0 if cash_flow < 0 else _clamp_score(70 - min(cash_flow, 80) * 0.5)
    return round(debt_component * 0.45 + profit_component * 0.30 + cash_component * 0.25, 1)


def _equity_score(record: dict) -> float:
    equity = record.get("equity", {})
    top_shareholder = _number(equity.get("top_shareholder_ratio"))
    pledge = _number(equity.get("pledge_ratio"))
    audit_opinion = str(equity.get("audit_opinion", ""))
    overdue_debt = str(equity.get("overdue_debt", ""))

    shareholder_balance = _clamp_score(100 - abs(top_shareholder - 40) * 1.2)
    pledge_health = _clamp_score(90 - pledge * 0.7)
    penalty = 0.0
    if audit_opinion and audit_opinion != "标准无保留意见":
        penalty += 15.0
    if overdue_debt and overdue_debt != "无逾期":
        penalty += 15.0
    return _clamp_score(shareholder_balance * 0.45 + pledge_health * 0.55 - penalty)


def _policy_number(record: dict, key: str) -> float:
    return _clamp_score(record.get("policy", {}).get(key, 0))


def _module_scores(record: dict) -> dict[str, float]:
    return {
        "financial": _financial_score(record),
        "equity": _equity_score(record),
        "regional": _policy_number(record, "regional_fit"),
        "policy": _policy_number(record, "policy_signal"),
    }


def _total_score(record: dict) -> float:
    scores = _module_scores(record)
    weighted = sum(scores[module] * MODULE_WEIGHTS[module] for module in MODULE_WEIGHTS)
    return round(weighted, 1)


def _active_records(records: Iterable[dict]) -> list[dict]:
    return [
        record
        for record in records
        if not record.get("is_st") and not record.get("is_financial")
    ]


def _score_key(record: dict) -> tuple[float, str]:
    return (-_total_score(record), record.get("stock_code", ""))


def _public_company(record: dict) -> dict:
    modules = _module_scores(record)
    score = _total_score(record)
    financials = record.get("financials", {})
    equity = record.get("equity", {})
    policy = record.get("policy", {})
    positive_reasons = policy.get("positive_reasons", [])
    risk_reasons = policy.get("risk_reasons", [])

    return {
        "stock_code": record["stock_code"],
        "code": record["stock_code"],
        "name": record["name"],
        "short_name": record["short_name"],
        "shortName": record["short_name"],
        "province": record["province"],
        "city": record["city"],
        "industry": record["industry"],
        "controller": record["controller"],
        "ownership": record["ownership"],
        "stateAttribute": record["ownership"],
        "score": score,
        "totalScore": score,
        "module_scores": modules,
        "modules": {
            "finance": modules["financial"],
            "equity": modules["equity"],
            "region": modules["regional"],
            "policy": modules["policy"],
        },
        "positive_reasons": positive_reasons,
        "highlights": positive_reasons,
        "risk_reasons": risk_reasons,
        "risks": risk_reasons,
        "financials": {
            "revenue": financials.get("revenue", 0),
            "netProfit": financials.get("net_profit", 0),
            "assetLiabilityRatio": financials.get("asset_liability_ratio", 0),
            "roe": financials.get("roe", 0),
            "cashFlow": financials.get("cash_flow", 0),
            "net_profit": financials.get("net_profit", 0),
            "asset_liability_ratio": financials.get("asset_liability_ratio", 0),
            "cash_flow": financials.get("cash_flow", 0),
        },
        "equity": {
            "topShareholderRatio": equity.get("top_shareholder_ratio", 0),
            "pledgeRatio": equity.get("pledge_ratio", 0),
            "auditOpinion": equity.get("audit_opinion", ""),
            "overdueDebt": equity.get("overdue_debt", ""),
            "top_shareholder_ratio": equity.get("top_shareholder_ratio", 0),
            "pledge_ratio": equity.get("pledge_ratio", 0),
            "audit_opinion": equity.get("audit_opinion", ""),
            "overdue_debt": equity.get("overdue_debt", ""),
        },
        "is_st": record.get("is_st", False),
        "is_financial": record.get("is_financial", False),
    }


def build_company_score_documents(records: Iterable[dict]) -> list[dict]:
    documents = []
    for record in _active_records(records):
        document = _public_company(record)
        search_terms = [
            record.get("stock_code", ""),
            record.get("name", ""),
            record.get("short_name", ""),
            record.get("province", ""),
            record.get("city", ""),
            record.get("industry", ""),
            record.get("controller", ""),
            *record.get("aliases", []),
        ]
        document["_search_text"] = " ".join(str(term) for term in search_terms if term)
        documents.append(document)
    return documents


def build_province_score_documents(score_documents: Iterable[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for document in score_documents:
        province = document.get("province")
        if not province:
            continue
        grouped.setdefault(province, []).append(_company_list_summary(document))
    return [
        {
            "province": province,
            "companies": sorted(companies, key=lambda item: (-item["score"], item["stock_code"])),
        }
        for province, companies in sorted(grouped.items())
    ]


def get_top_companies(
    limit: int = 10,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> list[dict]:
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            return [
                _clean_scored_doc(record)
                for record in database.find_query(
                    SCORE_COLLECTION,
                    _active_query(),
                    sort=_score_sort(),
                    limit=limit,
                )
            ]

    ranked = sorted(_active_records(_resolve_records(records, companies)), key=_score_key)
    return [_public_company(record) for record in ranked[:limit]]


def get_province_companies(
    province: str,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> list[dict]:
    normalized = normalize_province(province)
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            if database.has_collection(PROVINCE_SCORE_COLLECTION):
                documents = database.find_query(
                    PROVINCE_SCORE_COLLECTION,
                    {"province": normalized},
                    limit=1,
                )
                return documents[0].get("companies", []) if documents else []
            return [
                _clean_scored_doc(record)
                for record in database.find_query(
                    SCORE_COLLECTION,
                    _active_query({"province": normalized}),
                    sort=_score_sort(),
                )
            ]

    ranked = [
        record
        for record in _active_records(_resolve_records(records, companies))
        if record.get("province") == normalized
    ]
    return [_public_company(record) for record in sorted(ranked, key=_score_key)]


def get_all_provinces(
    records: Iterable[dict] | None = None, companies: Iterable[dict] | None = None
) -> list[str]:
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            return sorted(
                province
                for province in database.distinct(SCORE_COLLECTION, "province", _active_query())
                if province
            )

    return sorted(
        {record["province"] for record in _active_records(_resolve_records(records, companies))}
    )


def get_company_detail(
    stock_code: str,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> dict:
    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            record = database.find_query(
                SCORE_COLLECTION,
                _active_query({"stock_code": stock_code}),
                limit=1,
            )
            if not record:
                raise KeyError(stock_code)
            detail = _clean_scored_doc(record[0])
            rank_query = _active_query(
                {
                    "$or": [
                        {"score": {"$gt": detail["score"]}},
                        {"score": detail["score"], "stock_code": {"$lt": stock_code}},
                    ]
                }
            )
            province_rank_query = _active_query(
                {
                    "province": detail["province"],
                    "$or": [
                        {"score": {"$gt": detail["score"]}},
                        {"score": detail["score"], "stock_code": {"$lt": stock_code}},
                    ],
                }
            )
            detail["national_rank"] = (
                database.count_documents(SCORE_COLLECTION, rank_query) + 1
            )
            detail["province_rank"] = (
                database.count_documents(SCORE_COLLECTION, province_rank_query) + 1
            )
            detail["module_labels"] = MODULE_LABELS
            detail["module_weights"] = MODULE_WEIGHTS
            detail["data_status"] = "mongodb"
            return detail

    active = sorted(_active_records(_resolve_records(records, companies)), key=_score_key)
    by_code = {record["stock_code"]: record for record in active}
    record = by_code.get(stock_code)
    if record is None:
        raise KeyError(stock_code)

    province_ranked = [
        item for item in active if item.get("province") == record.get("province")
    ]
    detail = _public_company(record)
    detail["national_rank"] = active.index(record) + 1
    detail["province_rank"] = province_ranked.index(record) + 1
    detail["module_labels"] = MODULE_LABELS
    detail["module_weights"] = MODULE_WEIGHTS
    detail["data_status"] = "json_database"
    return detail


def normalize_province(query: str) -> str | None:
    text = query.strip()
    if text in PROVINCE_ALIASES:
        return PROVINCE_ALIASES[text]
    for alias, province in PROVINCE_ALIASES.items():
        if alias and alias in text:
            return province
    return None


def _company_search_score(query: str, record: dict) -> int:
    fields = [
        record.get("stock_code", ""),
        record.get("name", ""),
        record.get("short_name", ""),
        *record.get("aliases", []),
    ]
    lowered = _query_text(query)
    for field in fields:
        if lowered == _query_text(field):
            return 100
    for field in fields:
        if lowered and lowered in _query_text(field):
            return 70
    return 0


def search_entities(
    query: str,
    records: Iterable[dict] | None = None,
    companies: Iterable[dict] | None = None,
) -> dict:
    text = query.strip()
    if not text:
        return {"type": "empty", "companies": []}

    province = normalize_province(text)
    if province:
        if _can_use_materialized(records, companies):
            database = _materialized_database()
            if database is not None:
                if database.has_collection(PROVINCE_SCORE_COLLECTION):
                    documents = database.find_query(
                        PROVINCE_SCORE_COLLECTION,
                        {"province": province},
                        limit=1,
                    )
                    count = len(documents[0].get("companies", [])) if documents else 0
                    return {"type": "province", "province": province, "count": count}
                return {
                    "type": "province",
                    "province": province,
                    "count": database.count_documents(
                        SCORE_COLLECTION, _active_query({"province": province})
                    ),
                }
        current_records = _resolve_records(records, companies)
        return {
            "type": "province",
            "province": province,
            "count": len(get_province_companies(province, records=current_records)),
        }

    if _can_use_materialized(records, companies):
        database = _materialized_database()
        if database is not None:
            exact_query = _active_query(
                {
                    "$or": [
                        {"stock_code": text},
                        {"name": text},
                        {"short_name": text},
                        {"aliases": text},
                    ]
                }
            )
            exact_matches = database.find_query(
                SCORE_COLLECTION, exact_query, sort=_score_sort(), limit=9
            )
            if len(exact_matches) == 1:
                return {"type": "company", "company": _clean_scored_doc(exact_matches[0])}
            if len(exact_matches) > 1:
                return {
                    "type": "candidates",
                    "companies": [_clean_scored_doc(record) for record in exact_matches[:8]],
                }

            candidates = database.find_query(
                SCORE_COLLECTION,
                _active_query({"_search_text": {"$regex": re.escape(text), "$options": "i"}}),
                sort=_score_sort(),
                limit=8,
            )
            if not candidates:
                return {"type": "none", "companies": []}
            if len(candidates) == 1:
                return {"type": "company", "company": _clean_scored_doc(candidates[0])}
            return {
                "type": "candidates",
                "companies": [_clean_scored_doc(record) for record in candidates],
            }

    current_records = _resolve_records(records, companies)
    matches = []
    for record in _active_records(current_records):
        score = _company_search_score(text, record)
        if score:
            matches.append((score, record))

    matches.sort(key=lambda item: (-item[0], item[1].get("short_name", "")))
    if not matches:
        return {"type": "none", "companies": []}

    exact_matches = [record for score, record in matches if score == 100]
    if len(exact_matches) == 1:
        return {"type": "company", "company": _public_company(exact_matches[0])}

    candidates = [record for _, record in matches]
    candidates.sort(key=_score_key)
    if len(candidates) == 1:
        return {"type": "company", "company": _public_company(candidates[0])}
    return {
        "type": "candidates",
        "companies": [_public_company(record) for record in candidates[:8]],
    }
