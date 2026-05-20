from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .db import MongoDatabase
from .services import SCORE_COLLECTION
from .top_shareholders import (
    DEFAULT_TOP_SHAREHOLDER_CSV,
    TOP_SHAREHOLDER_COLLECTION,
    apply_top_shareholder_to_equity,
    load_top_shareholders_from_csv,
    load_top_shareholders_from_excel,
)


def load_source_records(path: Path | str) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() in {".xlsx", ".xls"}:
        return load_top_shareholders_from_excel(source)
    return load_top_shareholders_from_csv(source)


def import_top_shareholders(
    source: Path | str,
    target_database: Any,
    update_materialized: bool = True,
) -> dict[str, int]:
    records = load_source_records(source)
    target_database.replace_all(TOP_SHAREHOLDER_COLLECTION, records)
    summary = {
        "top_shareholder_records": len(records),
        "equity_documents_updated": 0,
        "score_documents_updated": 0,
    }
    if update_materialized and hasattr(target_database, "_collection"):
        summary.update(_update_mongo_materialized_fields(target_database, records))
    return summary


def _update_mongo_materialized_fields(
    target_database: Any,
    records: list[dict[str, Any]],
) -> dict[str, int]:
    equity_collection = target_database._collection("equity")
    scores_collection = target_database._collection(SCORE_COLLECTION)
    equity_updates = 0
    score_updates = 0

    for record in records:
        stock_code = record.get("stock_code")
        if not stock_code:
            continue
        overlay = apply_top_shareholder_to_equity({}, record)
        equity_fields = {
            key: overlay[key]
            for key in [
                "top_shareholder_name",
                "top_shareholder_ratio",
                "top_shareholder_date",
                "top_shareholder_shares",
                "top_shareholder_share_class",
            ]
        }
        score_fields = {f"equity.{key}": value for key, value in overlay.items()}

        equity_result = equity_collection.update_one(
            {"stock_code": stock_code},
            {"$set": equity_fields},
            upsert=False,
        )
        score_result = scores_collection.update_one(
            {"stock_code": stock_code},
            {"$set": score_fields},
            upsert=False,
        )
        equity_updates += int(getattr(equity_result, "modified_count", 0))
        score_updates += int(getattr(score_result, "modified_count", 0))

    return {
        "equity_documents_updated": equity_updates,
        "score_documents_updated": score_updates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import 2025 top shareholder data to MongoDB.")
    parser.add_argument("--source", type=Path, default=DEFAULT_TOP_SHAREHOLDER_CSV)
    parser.add_argument("--database", default=os.environ.get("MONGODB_DATABASE", "mixed_reform"))
    parser.add_argument(
        "--skip-materialized-update",
        action="store_true",
        help="Only replace the top_shareholders collection.",
    )
    args = parser.parse_args()

    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        raise SystemExit("Please set MONGODB_URI before running this command.")

    target = MongoDatabase(uri=uri, database_name=args.database)
    summary = import_top_shareholders(
        args.source,
        target,
        update_materialized=not args.skip_materialized_update,
    )
    print(json.dumps({"database": args.database, **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
