from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JsonDatabase:
    """Small JSON-file database for prototype data storage."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def all(self, collection: str) -> list[dict[str, Any]]:
        path = self._path(collection)
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError(f"{collection}.json must contain a list")
        return payload

    def replace_all(self, collection: str, records: list[dict[str, Any]]) -> None:
        self._write(collection, records)

    def clear(self, collection: str) -> None:
        self._write(collection, [])

    def insert(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        records = self.all(collection)
        records.append(record)
        self._write(collection, records)
        return record

    def insert_many(self, collection: str, records: list[dict[str, Any]]) -> int:
        existing = self.all(collection)
        existing.extend(records)
        self._write(collection, existing)
        return len(records)

    def upsert(self, collection: str, key: str, record: dict[str, Any]) -> dict[str, Any]:
        records = self.all(collection)
        value = record.get(key)
        for index, item in enumerate(records):
            if item.get(key) == value:
                records[index] = {**item, **record}
                self._write(collection, records)
                return records[index]
        records.append(record)
        self._write(collection, records)
        return record

    def delete(self, collection: str, key: str, value: Any) -> bool:
        records = self.all(collection)
        kept = [record for record in records if record.get(key) != value]
        changed = len(kept) != len(records)
        if changed:
            self._write(collection, kept)
        return changed

    def find_one(self, collection: str, key: str, value: Any) -> dict[str, Any] | None:
        for record in self.all(collection):
            if record.get(key) == value:
                return record
        return None

    def find_many(self, collection: str, key: str, value: Any) -> list[dict[str, Any]]:
        return [record for record in self.all(collection) if record.get(key) == value]

    def _path(self, collection: str) -> Path:
        if not collection.replace("_", "").isalnum():
            raise ValueError(f"Invalid collection name: {collection}")
        return self.root / f"{collection}.json"

    def _write(self, collection: str, records: list[dict[str, Any]]) -> None:
        path = self._path(collection)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(".json.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temp_path.replace(path)


class MongoDatabase:
    """MongoDB-backed database with the same small contract as JsonDatabase."""

    def __init__(
        self,
        uri: str | None = None,
        database_name: str = "mixed_reform",
        client: Any | None = None,
    ):
        if client is None:
            try:
                from pymongo import MongoClient
            except ImportError as exc:
                raise RuntimeError(
                    "MongoDB support requires pymongo. Install it with: pip install pymongo"
                ) from exc
            if not uri:
                raise ValueError("MongoDB uri is required")
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=20000,
                connectTimeoutMS=10000,
                socketTimeoutMS=60000,
            )
        self.client = client
        self.database = client[database_name]

    def all(self, collection: str) -> list[dict[str, Any]]:
        return self.find_query(collection)

    def replace_all(self, collection: str, records: list[dict[str, Any]]) -> None:
        target = self._collection(collection)
        target.delete_many({})
        self.insert_many(collection, records)
        self._ensure_stock_code_index(collection)

    def clear(self, collection: str) -> None:
        self._collection(collection).delete_many({})

    def insert(self, collection: str, record: dict[str, Any]) -> dict[str, Any]:
        self._collection(collection).insert_one(record.copy())
        self._ensure_indexes(collection)
        return record

    def insert_many(self, collection: str, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0
        target = self._collection(collection)
        if hasattr(target, "insert_many"):
            target.insert_many([record.copy() for record in records])
        else:
            for record in records:
                target.insert_one(record.copy())
        self._ensure_indexes(collection)
        return len(records)

    def upsert(self, collection: str, key: str, record: dict[str, Any]) -> dict[str, Any]:
        self._collection(collection).replace_one({key: record.get(key)}, record.copy(), upsert=True)
        if key == "stock_code":
            self._ensure_stock_code_index(collection)
        return record

    def delete(self, collection: str, key: str, value: Any) -> bool:
        result = self._collection(collection).delete_one({key: value})
        return bool(result.deleted_count)

    def find_one(self, collection: str, key: str, value: Any) -> dict[str, Any] | None:
        record = self._collection(collection).find_one({key: value})
        return self._strip_id(record) if record else None

    def find_many(self, collection: str, key: str, value: Any) -> list[dict[str, Any]]:
        return [self._strip_id(record) for record in self._collection(collection).find({key: value})]

    def find_query(
        self,
        collection: str,
        query: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        limit: int = 0,
        projection: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        cursor = self._collection(collection).find(query or {}, projection or {"_id": 0})
        if sort:
            cursor = cursor.sort(sort)
        if limit:
            cursor = cursor.limit(limit)
        return [self._strip_id(record) for record in cursor]

    def count_documents(self, collection: str, query: dict[str, Any] | None = None) -> int:
        return int(self._collection(collection).count_documents(query or {}))

    def distinct(
        self, collection: str, key: str, query: dict[str, Any] | None = None
    ) -> list[Any]:
        return list(self._collection(collection).distinct(key, query or {}))

    def has_collection(self, collection: str) -> bool:
        return collection in self.database.list_collection_names()

    def _collection(self, collection: str) -> Any:
        if not collection.replace("_", "").isalnum():
            raise ValueError(f"Invalid collection name: {collection}")
        return self.database.get_collection(collection)

    def _ensure_stock_code_index(self, collection: str) -> None:
        if collection in {"companies", "financials", "equity", "policies", "top_shareholders"}:
            self._collection(collection).create_index("stock_code")

    def _ensure_indexes(self, collection: str) -> None:
        self._ensure_stock_code_index(collection)
        if collection == "company_scores":
            target = self._collection(collection)
            target.create_index("stock_code")
            target.create_index("province")
            target.create_index([("score", -1), ("stock_code", 1)])
        if collection == "province_company_scores":
            self._collection(collection).create_index("province")

    def _strip_id(self, record: dict[str, Any]) -> dict[str, Any]:
        record = record.copy()
        record.pop("_id", None)
        return record
