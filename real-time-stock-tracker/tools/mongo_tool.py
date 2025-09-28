from pymongo import MongoClient
from pydantic import BaseModel

class ToolResult(BaseModel):
    status: str
    payload: dict
    summary: str = None

class MongoQueryTool:
    def __init__(self, conn_str, allowed_collections=None):
        self.client = MongoClient(conn_str)
        self.db = self.client["inventory"]
        self.allowed = set(allowed_collections or ["products"])

    def run(self, params: dict) -> ToolResult:
        coll = params.get("collection")
        if coll not in self.allowed:
            return ToolResult(status="error", payload={}, summary="Collection not allowed")
        filt = params.get("filter", {})
        proj = params.get("projection")
        limit = min(int(params.get("limit",1)), 100)
        cur = self.db[coll].find(filt, proj).limit(limit)
        docs = list(cur)
        return ToolResult(status="ok", payload={"docs":docs}, summary=f"Found {len(docs)} rows")
