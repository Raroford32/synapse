"""Memory service leveraging Mem0 with an in-memory fallback."""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional


class MemoryService:
    """CRUD operations for user memories with simple categorization.

    Real Mem0 integration can replace the in-memory store later while keeping
    the same interface.
    """

    def __init__(self) -> None:
        # In-memory fallback store: {user_id: [{id, content, type, metadata, created_at}]}
        self._store: Dict[str, List[Dict[str, Any]]] = {}

    async def list_memories(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self._store.get(user_id, []))

    async def create_memory(
        self,
        user_id: str,
        content: str,
        type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        memory = {
            "id": str(uuid.uuid4()),
            "content": content,
            "type": type,
            "metadata": metadata or {},
            "created_at": int(time.time()),
        }
        self._store.setdefault(user_id, []).append(memory)
        return memory

    async def delete_memory(self, user_id: str, memory_id: str) -> bool:
        items = self._store.get(user_id, [])
        new_items = [m for m in items if m["id"] != memory_id]
        deleted = len(new_items) != len(items)
        if deleted:
            self._store[user_id] = new_items
        return deleted

