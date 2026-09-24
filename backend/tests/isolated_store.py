"""Test-only Motor subset. No network, dotenv, or persistent database access."""
from copy import deepcopy
import re
from types import SimpleNamespace


def matches(doc, query):
    for key, expected in (query or {}).items():
        if key == "$or":
            if not any(matches(doc, q) for q in expected):
                return False
            continue
        if key == "$and":
            if not all(matches(doc, q) for q in expected):
                return False
            continue
        actual = doc.get(key)
        if isinstance(expected, dict):
            for op, value in expected.items():
                if op == "$regex":
                    ok = isinstance(actual, str) and re.search(value, actual) is not None
                elif op == "$gte":
                    ok = actual is not None and actual >= value
                elif op == "$lte":
                    ok = actual is not None and actual <= value
                elif op == "$gt":
                    ok = actual is not None and actual > value
                elif op == "$lt":
                    ok = actual is not None and actual < value
                elif op == "$ne":
                    ok = actual != value
                elif op == "$in":
                    ok = actual in value
                elif op == "$exists":
                    ok = (key in doc) == value
                else:
                    raise NotImplementedError(f"Unsupported test filter: {op}")
                if not ok:
                    return False
        elif actual != expected:
            return False
    return True


def project(doc, projection):
    result = deepcopy(doc)
    if not projection:
        return result
    includes = [k for k, v in projection.items() if v and k != "_id"]
    if includes:
        return {k: result[k] for k in includes if k in result}
    return {k: v for k, v in result.items() if projection.get(k, 1)}


class Cursor:
    def __init__(self, docs):
        self.docs = docs

    def sort(self, key, direction=1):
        fields = key if isinstance(key, list) else [(key, direction)]
        for field, order in reversed(fields):
            self.docs.sort(key=lambda d: (d.get(field) is not None, d.get(field)), reverse=order < 0)
        return self

    def limit(self, count):
        self.docs = self.docs[:count]
        return self

    async def to_list(self, length=None):
        return deepcopy(self.docs[:length] if length is not None else self.docs)

    def __aiter__(self):
        self._iterator = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return deepcopy(next(self._iterator))
        except StopIteration:
            raise StopAsyncIteration


class Collection:
    def __init__(self):
        self.docs = []

    def find(self, query=None, projection=None):
        return Cursor([project(d, projection) for d in self.docs if matches(d, query)])

    async def find_one(self, query, projection=None):
        return next((project(d, projection) for d in self.docs if matches(d, query)), None)

    async def count_documents(self, query):
        return sum(matches(d, query) for d in self.docs)

    async def insert_one(self, doc):
        self.docs.append(deepcopy(doc))
        return SimpleNamespace(inserted_id=doc.get("id"))

    async def insert_many(self, docs):
        for doc in docs:
            await self.insert_one(doc)

    async def update_one(self, query, update, upsert=False):
        doc = next((d for d in self.docs if matches(d, query)), None)
        existing = doc is not None
        if not existing:
            if not upsert:
                return SimpleNamespace(matched_count=0, modified_count=0)
            doc = {k: deepcopy(v) for k, v in query.items() if not k.startswith("$") and not isinstance(v, dict)}
            self.docs.append(doc)
        for op, values in update.items():
            if op == "$set" or (op == "$setOnInsert" and not existing):
                doc.update(deepcopy(values))
            elif op == "$unset":
                for key in values:
                    doc.pop(key, None)
            elif op == "$inc":
                for key, value in values.items():
                    doc[key] = doc.get(key, 0) + value
            elif op != "$setOnInsert":
                raise NotImplementedError(f"Unsupported test update: {op}")
        return SimpleNamespace(matched_count=int(existing), modified_count=1)

    async def delete_one(self, query):
        for i, doc in enumerate(self.docs):
            if matches(doc, query):
                self.docs.pop(i)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    async def delete_many(self, query):
        count = len(self.docs)
        self.docs[:] = [d for d in self.docs if not matches(d, query)]
        return SimpleNamespace(deleted_count=count - len(self.docs))


class Database:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        return self.collections.setdefault(name, Collection())

    def __getattr__(self, name):
        return self[name]


def install():
    """Install before router import: generic CRUD captures collection handles."""
    import sys
    from types import ModuleType
    if "lib.db" in sys.modules:
        raise RuntimeError("Install isolated store before importing the application")
    module = ModuleType("lib.db")
    module.db = Database()
    sys.modules["lib.db"] = module
    return module.db


def create_app():
    from fastapi import FastAPI
    from routers import account, auth, finance, gaming, insights, subscriptions
    app = FastAPI()
    for module in (account, auth, finance, gaming, insights, subscriptions):
        app.include_router(module.router, prefix="/api")
    return app
