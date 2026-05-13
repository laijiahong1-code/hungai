from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .data import DATABASE_ROOT, load_company_records
from .db import JsonDatabase, MongoDatabase
from .services import (
    PROVINCE_SCORE_COLLECTION,
    SCORE_COLLECTION,
    build_company_score_documents,
    build_province_score_documents,
)


def migrate_json_database(
    source_root: Path | str,
    target_database: Any,
    include_raw: bool = False,
    include_scores: bool = False,
    batch_size: int = 1000,
) -> dict[str, int]:
    root = Path(source_root)
    collection_count = 0
    record_count = 0

    for path in sorted(root.glob("*.json")):
        collection = path.stem
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            continue
        target_database.replace_all(collection, records)
        collection_count += 1
        record_count += len(records)

    raw_collection_count = 0
    raw_record_count = 0
    if include_raw:
        raw_summary = migrate_raw_jsonl(root / "raw", target_database, batch_size=batch_size)
        raw_collection_count = raw_summary["raw_collections"]
        raw_record_count = raw_summary["raw_records"]

    summary = {
        "collections": collection_count,
        "records": record_count,
        "raw_collections": raw_collection_count,
        "raw_records": raw_record_count,
    }
    if include_scores:
        score_documents = build_company_score_documents(load_company_records(JsonDatabase(root)))
        province_documents = build_province_score_documents(score_documents)
        target_database.replace_all(SCORE_COLLECTION, score_documents)
        target_database.replace_all(PROVINCE_SCORE_COLLECTION, province_documents)
        summary["score_collections"] = 1
        summary["score_records"] = len(score_documents)
        summary["province_score_collections"] = 1
        summary["province_score_records"] = len(province_documents)
    return summary


def migrate_raw_jsonl(raw_root: Path | str, target_database: Any, batch_size: int = 1000) -> dict[str, int]:
    root = Path(raw_root)
    if not root.exists():
        return {"raw_collections": 0, "raw_records": 0}

    collection_count = 0
    record_count = 0
    for path in sorted(root.glob("*.jsonl")):
        collection = f"raw_{safe_collection_name(path.stem)}"
        target_database.clear(collection)
        collection_count += 1

        batch: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                batch.append(json.loads(line))
                if len(batch) >= batch_size:
                    record_count += target_database.insert_many(collection, batch)
                    batch = []
        if batch:
            record_count += target_database.insert_many(collection, batch)

    return {"raw_collections": collection_count, "raw_records": record_count}


def safe_collection_name(name: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_").lower()
    return clean[:90] or "source"


def main() -> None:
    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        raise SystemExit("Please set MONGODB_URI before running this command.")
    database_name = os.environ.get("MONGODB_DATABASE", "mixed_reform")
    include_raw = os.environ.get("MONGODB_MIGRATE_RAW", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
    }
    target = MongoDatabase(uri=uri, database_name=database_name)
    summary = migrate_json_database(
        DATABASE_ROOT,
        target,
        include_raw=include_raw,
        include_scores=True,
    )
    print(json.dumps({"database": database_name, **summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
