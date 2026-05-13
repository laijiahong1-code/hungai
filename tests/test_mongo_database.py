import pytest
import sys
from types import SimpleNamespace

from backend.app import data as data_module
from backend.app.db import MongoDatabase


class FakeCollection:
    def __init__(self):
        self.records = []
        self.replacements = []
        self.indexes = []

    def find(self, query=None, projection=None):
        query = query or {}
        return [record.copy() for record in self.records if matches(record, query)]

    def find_one(self, query):
        for record in self.records:
            if matches(record, query):
                return record.copy()
        return None

    def insert_one(self, record):
        self.records.append(record.copy())

    def replace_one(self, query, record, upsert=False):
        self.replacements.append((query.copy(), record.copy(), upsert))
        for index, item in enumerate(self.records):
            if matches(item, query):
                self.records[index] = record.copy()
                return
        if upsert:
            self.records.append(record.copy())

    def delete_one(self, query):
        before = len(self.records)
        self.records = [record for record in self.records if not matches(record, query)]

        class Result:
            deleted_count = before - len(self.records)

        return Result()

    def delete_many(self, query):
        self.records = []

    def create_index(self, key):
        self.indexes.append(key)


class FakeMongoClient:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, database_name):
        return self

    def get_collection(self, collection):
        self.collections.setdefault(collection, FakeCollection())
        return self.collections[collection]


def matches(record, query):
    return all(record.get(key) == value for key, value in query.items())


def test_mongo_database_crud_methods_match_json_database_contract():
    client = FakeMongoClient()
    db = MongoDatabase(client=client, database_name="mixed_reform")

    db.insert("companies", {"stock_code": "600001", "name": "甲能源"})
    db.upsert("companies", "stock_code", {"stock_code": "600001", "name": "甲能源集团"})

    assert db.find_one("companies", "stock_code", "600001")["name"] == "甲能源集团"
    assert db.find_many("companies", "stock_code", "600001") == [
        {"stock_code": "600001", "name": "甲能源集团"}
    ]
    assert db.delete("companies", "stock_code", "600001") is True
    assert db.all("companies") == []


def test_default_database_uses_mongo_when_uri_is_configured(monkeypatch):
    created = {}

    class FakeMongoDatabase:
        def __init__(self, uri, database_name):
            created["uri"] = uri
            created["database_name"] = database_name

    monkeypatch.setenv("MONGODB_URI", "mongodb+srv://example")
    monkeypatch.setenv("MONGODB_DATABASE", "cloud_mix")
    monkeypatch.setattr(data_module, "MongoDatabase", FakeMongoDatabase)

    database = data_module.default_database()

    assert isinstance(database, FakeMongoDatabase)
    assert created == {"uri": "mongodb+srv://example", "database_name": "cloud_mix"}


def test_default_database_can_read_streamlit_secrets(monkeypatch):
    created = {}

    class FakeMongoDatabase:
        def __init__(self, uri, database_name):
            created["uri"] = uri
            created["database_name"] = database_name

    fake_streamlit = SimpleNamespace(
        secrets={"MONGODB_URI": "mongodb+srv://secret", "MONGODB_DATABASE": "streamlit_mix"}
    )
    monkeypatch.delenv("MONGODB_URI", raising=False)
    monkeypatch.delenv("MONGODB_DATABASE", raising=False)
    monkeypatch.setitem(sys.modules, "streamlit", fake_streamlit)
    monkeypatch.setattr(data_module, "MongoDatabase", FakeMongoDatabase)
    monkeypatch.setattr(data_module, "_DEFAULT_DATABASE", None)
    monkeypatch.setattr(data_module, "_DEFAULT_DATABASE_CONFIG", None)

    database = data_module.default_database()

    assert isinstance(database, FakeMongoDatabase)
    assert created == {"uri": "mongodb+srv://secret", "database_name": "streamlit_mix"}


def test_mongo_database_requires_pymongo_when_client_is_not_injected(monkeypatch):
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name == "pymongo":
            raise ImportError("missing")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)

    with pytest.raises(RuntimeError, match="pip install pymongo"):
        MongoDatabase(uri="mongodb://example", database_name="mixed_reform")
