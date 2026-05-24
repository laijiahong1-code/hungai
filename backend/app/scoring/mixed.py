from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .common import normalize_year, read_csv_rows, stock_code
from .models import Evidence, ModuleResult


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CURRENT_A_SHARE_SCORED = PROJECT_ROOT / "data" / "HLD_current_A_share_mixed_ownership_scored.csv"

REQUIRED_COLUMNS = [
    "InstitutionID",
    "Symbol",
    "ShortName",
    "EndDate",
    "MixedEquityStructureOrNOT",
    "NSttOwnedShrhlderRatioSum",
    "NSttOwnedShrhlderPartic",
    "EquityStructureDiversity",
    "EquityStrucEntropyIndex",
    "EquityBalance",
    "OwnershipConcentration",
    "EquityStrucHerfindalIndex",
    "EquityIntegration",
]

NUMERIC_COLUMNS = [
    "MixedEquityStructureOrNOT",
    "NSttOwnedShrhlderRatioSum",
    "NSttOwnedShrhlderPartic",
    "EquityStructureDiversity",
    "EquityStrucEntropyIndex",
    "EquityBalance",
    "OwnershipConcentration",
    "EquityStrucHerfindalIndex",
    "EquityIntegration",
]

SCORE_COLUMNS = [
    "Score_NonStateCapital",
    "Score_EquityDiversity",
    "Score_EquityBalance",
    "Score_EquityIntegration",
    "Score_OpenGovernance",
]

SCORE_ITEMS = [
    ("非国有资本进入程度", "Score_NonStateCapital", 30.0),
    ("股权结构多样性", "Score_EquityDiversity", 20.0),
    ("股权制衡程度", "Score_EquityBalance", 20.0),
    ("股权融合程度", "Score_EquityIntegration", 15.0),
    ("股权开放治理程度", "Score_OpenGovernance", 15.0),
]


def build_mixed_scores(source_root: Path) -> dict[str, ModuleResult]:
    legacy_path = resolve_legacy_ga_path(source_root)
    current_scores = build_current_a_share_scores(source_root, allow_project_default=legacy_path is None)
    if current_scores:
        return current_scores

    if legacy_path is None:
        return {}
    rows = read_csv_rows(legacy_path)
    if not rows:
        return {}
    frame = pd.DataFrame(rows)
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        return {}
    scored = add_scores(frame)
    scored["_stock_code"] = scored["Symbol"].apply(stock_code)
    scored["_year"] = scored["EndDate"].apply(normalize_year)
    scored = scored.sort_values(["_stock_code", "_year"])
    results = {}
    for code, group in scored.groupby("_stock_code"):
        if not code:
            continue
        row = group.iloc[-1]
        results[code] = ModuleResult("mixed", float(row["MixedOwnershipScore"]), evidence_from_row(row))
    return results


def build_current_a_share_scores(
    source_root: Path,
    allow_project_default: bool = True,
) -> dict[str, ModuleResult]:
    path = resolve_current_a_share_scored_path(source_root, allow_project_default)
    if path is None:
        return {}
    try:
        frame = pd.read_csv(path, dtype={"Symbol": str}, low_memory=False)
    except Exception:
        return {}
    required = {"Symbol", "EndDate", "MixedOwnershipScore", *SCORE_COLUMNS}
    if any(column not in frame.columns for column in required):
        return {}
    for column in ["MixedOwnershipScore", *SCORE_COLUMNS]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["_stock_code"] = frame["Symbol"].apply(stock_code)
    frame["_year"] = frame["EndDate"].apply(normalize_year)
    frame = frame.dropna(subset=["MixedOwnershipScore"]).sort_values(["_stock_code", "_year"])
    results = {}
    for code, group in frame.groupby("_stock_code"):
        if not code:
            continue
        row = group.iloc[-1]
        results[code] = ModuleResult("mixed", float(row["MixedOwnershipScore"]), evidence_from_row(row))
    return results


def resolve_current_a_share_scored_path(
    source_root: Path,
    allow_project_default: bool = True,
) -> Path | None:
    candidates = [
        source_root / "HLD_current_A_share_mixed_ownership_scored.csv",
        source_root
        / "交付_混改评分系统"
        / "交付_混改评分系统"
        / "HLD_current_A_share_mixed_ownership_scored.csv",
    ]
    if allow_project_default:
        candidates.append(CURRENT_A_SHARE_SCORED)
    for path in candidates:
        if path.exists():
            return path
    return None


def resolve_legacy_ga_path(source_root: Path) -> Path | None:
    direct = source_root / "GA_StateOwnedMixedDegree.csv"
    if direct.exists():
        return direct
    if not source_root.exists():
        return None
    matches = list(source_root.rglob("GA_StateOwnedMixedDegree.csv"))
    return matches[0] if matches else None


def evidence_from_row(row: pd.Series) -> list[Evidence]:
    evidence = []
    for label, column, max_score in SCORE_ITEMS:
        score = safe_float(row.get(column), 0.0)
        evidence.append(Evidence(label, f"{score:.1f}/{max_score:.0f}", score, max_score))
    return evidence


def safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def add_scores(df: pd.DataFrame) -> pd.DataFrame:
    scored = df.copy()
    for column in NUMERIC_COLUMNS:
        scored[column] = pd.to_numeric(scored[column], errors="coerce")

    mixed_flag_score = np.where(scored["MixedEquityStructureOrNOT"] == 1, 10.0, 0.0)
    non_state_ratio_score = clip_score(scored["NSttOwnedShrhlderRatioSum"], 0, 35, 15)
    non_state_participation_score = clip_score(scored["NSttOwnedShrhlderPartic"], 0, 0.7, 5)
    scored["Score_NonStateCapital"] = (
        pd.Series(mixed_flag_score, index=scored.index)
        + fill_component_missing(non_state_ratio_score, 15)
        + fill_component_missing(non_state_participation_score, 5)
    )

    diversity_count_score = diversity_score(scored["EquityStructureDiversity"])
    entropy_score_for_diversity = quantile_score(scored["EquityStrucEntropyIndex"], 8)
    scored["Score_EquityDiversity"] = (
        fill_component_missing(diversity_count_score, 12)
        + fill_component_missing(entropy_score_for_diversity, 8)
    )

    balance_score = quantile_score(scored["EquityBalance"], 12)
    concentration_reverse_score = reverse_clip_score(scored["OwnershipConcentration"], 40, 90, 4)
    hhi_reverse_score = reverse_clip_score(scored["EquityStrucHerfindalIndex"], 0.35, 0.95, 4)
    scored["Score_EquityBalance"] = (
        fill_component_missing(balance_score, 12)
        + fill_component_missing(concentration_reverse_score, 4)
        + fill_component_missing(hhi_reverse_score, 4)
    )

    integration_score = quantile_score(scored["EquityIntegration"], 15)
    scored["Score_EquityIntegration"] = fill_component_missing(integration_score, 15)

    moderate_concentration_score = 5 - (scored["OwnershipConcentration"] - 55).abs() / 35 * 5
    moderate_concentration_score = moderate_concentration_score.clip(lower=0, upper=5)
    governance_hhi_reverse_score = reverse_clip_score(scored["EquityStrucHerfindalIndex"], 0.35, 0.95, 5)
    governance_entropy_score = quantile_score(scored["EquityStrucEntropyIndex"], 5)
    scored["Score_OpenGovernance"] = (
        fill_component_missing(moderate_concentration_score, 5)
        + fill_component_missing(governance_hhi_reverse_score, 5)
        + fill_component_missing(governance_entropy_score, 5)
    )

    scored["MixedOwnershipScore"] = scored[SCORE_COLUMNS].sum(axis=1).clip(lower=0, upper=100).round(2)
    for column in SCORE_COLUMNS:
        scored[column] = scored[column].round(2)
    return scored


def clip_score(series: pd.Series, low: float, high: float, max_score: float) -> pd.Series:
    return ((series - low) / (high - low) * max_score).clip(lower=0, upper=max_score)


def reverse_clip_score(series: pd.Series, low: float, high: float, max_score: float) -> pd.Series:
    return ((high - series) / (high - low) * max_score).clip(lower=0, upper=max_score)


def quantile_score(series: pd.Series, max_score: float) -> pd.Series:
    valid = series.dropna()
    if valid.empty or valid.nunique() <= 1:
        return pd.Series(np.nan, index=series.index)
    return series.rank(method="average", pct=True) * max_score


def diversity_score(series: pd.Series) -> pd.Series:
    return series.round().map({1: 0.0, 2: 3.0, 3: 7.0, 4: 10.0, 5: 12.0, 6: 12.0})


def fill_component_missing(score: pd.Series, max_score: float) -> pd.Series:
    return score.fillna(max_score * 0.5)
