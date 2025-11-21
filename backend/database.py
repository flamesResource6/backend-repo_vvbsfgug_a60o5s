from typing import Any, Dict, Optional
import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime

MONGO_URL = os.getenv("DATABASE_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DATABASE_NAME", "appdb")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None

async def get_db() -> AsyncIOMotorDatabase:
    global _client, _db
    if _db is None:
        _client = AsyncIOMotorClient(MONGO_URL)
        _db = _client[DB_NAME]
    return _db

async def create_document(collection_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    db = await get_db()
    now = datetime.utcnow().isoformat()
    payload = {**data, "created_at": now, "updated_at": now}
    res = await db[collection_name].insert_one(payload)
    payload["_id"] = str(res.inserted_id)
    return payload

async def get_documents(collection_name: str, filter_dict: Optional[Dict[str, Any]] = None, limit: int = 50):
    db = await get_db()
    cursor = db[collection_name].find(filter_dict or {}).limit(limit)
    docs = []
    async for d in cursor:
        d["_id"] = str(d["_id"])  # stringify ObjectId
        docs.append(d)
    return docs
