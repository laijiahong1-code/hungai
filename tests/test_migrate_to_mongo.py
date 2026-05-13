import json

from backend.app.migrate_to_mongo import migrate_json_database


class FakeDatabase:
    def __init__(self):
        self.collections = {}

    def replace_all(self, collection, records):
        self.collections[collection] = records

    def clear(self, collection):
        self.collections[collection] = []

    def insert_many(self, collection, records):
        self.collections.setdefault(collection, []).extend(records)
        return len(records)


def test_migrate_json_database_copies_json_collections(tmp_path):
    source = tmp_path / "database"
    source.mkdir()
    (source / "companies.json").write_text(
        json.dumps([{"stock_code": "600001", "name": "甲能源"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (source / "source_catalog.json").write_text(
        json.dumps([{"source_id": "one", "row_count": 1}], ensure_ascii=False),
        encoding="utf-8",
    )

    target = FakeDatabase()
    summary = migrate_json_database(source, target)

    assert summary == {"collections": 2, "records": 2, "raw_collections": 0, "raw_records": 0}
    assert target.collections["companies"] == [{"stock_code": "600001", "name": "甲能源"}]
    assert target.collections["source_catalog"] == [{"source_id": "one", "row_count": 1}]


def test_migrate_json_database_can_stream_raw_jsonl_collections(tmp_path):
    source = tmp_path / "database"
    raw = source / "raw"
    raw.mkdir(parents=True)
    (source / "companies.json").write_text("[]", encoding="utf-8")
    (raw / "source_one.jsonl").write_text(
        '{"stock_code":"600001"}\n{"stock_code":"600002"}\n',
        encoding="utf-8",
    )

    target = FakeDatabase()
    summary = migrate_json_database(source, target, include_raw=True, batch_size=1)

    assert summary == {"collections": 1, "records": 0, "raw_collections": 1, "raw_records": 2}
    assert target.collections["raw_source_one"] == [
        {"stock_code": "600001"},
        {"stock_code": "600002"},
    ]
