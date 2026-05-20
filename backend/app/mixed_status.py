from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATUS_PATH = PROJECT_ROOT / "data" / "GA_StateOwnedMixedDegree_latest_status.csv"

STATUS_ORDER = ["尚未发生混改", "正在进行混改", "已经完成混改"]
STATUS_COLORS = {
    "尚未发生混改": "#F05A4A",
    "正在进行混改": "#F3B562",
    "已经完成混改": "#2E86AB",
}

METRICS = [
    ("NSttOwnedShrhlderRatioSum", "非国有股东持股比例"),
    ("EquityStructureDiversity", "股东类型多样性"),
    ("OwnershipConcentration", "股权集中度"),
    ("MixedOwnershipScore", "混改综合得分"),
]

ANNUAL_TRENDS = [
    {"year": 2022, "尚未发生混改": 42.7, "正在进行混改": 46.2, "已经完成混改": 11.1},
    {"year": 2023, "尚未发生混改": 45.7, "正在进行混改": 43.8, "已经完成混改": 10.6},
    {"year": 2024, "尚未发生混改": 46.8, "正在进行混改": 43.9, "已经完成混改": 9.2},
    {"year": 2025, "尚未发生混改": 49.4, "正在进行混改": 43.9, "已经完成混改": 6.8},
]


def load_status_dashboard(path: Path | None = None) -> dict[str, Any]:
    data_path = Path(path) if path is not None else DEFAULT_STATUS_PATH
    df = pd.read_csv(data_path, dtype={"Symbol": str})
    require_dashboard_columns(df)

    total = len(df)
    if total == 0:
        raise ValueError("mixed ownership status data is empty")

    return {
        "total": total,
        "status_slices": status_slices(df, total),
        "score_histogram": score_histogram(df),
        "metric_averages": metric_averages(df),
        "mixed_score_median": round(
            float(df.loc[df["MixedEquityStructureOrNOT"] == 1, "MixedOwnershipScore"].median()),
            2,
        ),
        "completion_threshold": round(
            float(df.loc[df["ReformStatus"] == "已经完成混改", "MixedOwnershipScore"].min()),
            2,
        ),
        "annual_trends": ANNUAL_TRENDS,
    }


def require_dashboard_columns(df: pd.DataFrame) -> None:
    required = {
        "ReformStatus",
        "MixedEquityStructureOrNOT",
        "MixedOwnershipScore",
        *(key for key, _ in METRICS),
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"mixed ownership status data missing columns: {', '.join(missing)}")


def status_slices(df: pd.DataFrame, total: int) -> list[dict[str, Any]]:
    counts = df["ReformStatus"].value_counts().reindex(STATUS_ORDER, fill_value=0)
    slices = []
    for status in STATUS_ORDER:
        count = int(counts.loc[status])
        percent = count / total * 100
        slices.append(
            {
                "label": status,
                "count": count,
                "percent": round(percent, 1),
                "percent_label": f"{percent:.1f}%",
                "color": STATUS_COLORS[status],
            }
        )
    return slices


def score_histogram(df: pd.DataFrame, bins: int = 12) -> list[dict[str, Any]]:
    scores = (
        df.loc[df["MixedEquityStructureOrNOT"] == 1, "MixedOwnershipScore"]
        .dropna()
        .astype(float)
        .to_numpy()
    )
    if len(scores) == 0:
        return []

    counts, edges = np.histogram(scores, bins=bins)
    max_count = int(counts.max()) if counts.size else 0
    histogram = []
    for index, count in enumerate(counts):
        left = float(edges[index])
        right = float(edges[index + 1])
        histogram.append(
            {
                "label": f"{left:.0f}-{right:.0f}",
                "left": round(left, 2),
                "right": round(right, 2),
                "count": int(count),
                "height": round((int(count) / max_count * 100) if max_count else 0, 1),
            }
        )
    return histogram


def metric_averages(df: pd.DataFrame) -> list[dict[str, Any]]:
    grouped = df.groupby("ReformStatus")[[key for key, _ in METRICS]].mean().reindex(STATUS_ORDER)
    max_by_metric = grouped.max(axis=0).replace(0, np.nan)

    rows = []
    for status in STATUS_ORDER:
        metrics = []
        for key, label in METRICS:
            value = float(grouped.loc[status, key])
            max_value = float(max_by_metric.loc[key]) if not pd.isna(max_by_metric.loc[key]) else 0
            metrics.append(
                {
                    "key": key,
                    "label": label,
                    "value": round(value, 2),
                    "height": round((value / max_value * 100) if max_value else 0, 1),
                }
            )
        rows.append({"status": status, "color": STATUS_COLORS[status], "metrics": metrics})
    return rows
