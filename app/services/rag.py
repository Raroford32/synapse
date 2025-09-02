"""RAG service placeholder with in-memory index.

In production, this will wrap R2R. For now, we provide a simple
in-memory index supporting upload, keyword search, and delete.
"""
from __future__ import annotations

import re
import time
import uuid
from typing import Any, Dict, List


class RagService:
    def __init__(self) -> None:
        # In-memory document store: {doc_id: {filename, content, created_at}}
        self._docs: Dict[str, Dict[str, Any]] = {}

    async def ingest_bytes(self, filename: str, content_bytes: bytes) -> Dict[str, Any]:
        doc_id = str(uuid.uuid4())
        text = content_bytes.decode(errors="ignore")
        self._docs[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "content": text,
            "created_at": int(time.time()),
        }
        return {"id": doc_id, "filename": filename}

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        results: List[Dict[str, Any]] = []
        for doc in self._docs.values():
            matches = list(pattern.finditer(doc["content"]))
            if not matches:
                continue
            # Take first match for snippet
            m = matches[0]
            start = max(0, m.start() - 60)
            end = min(len(doc["content"]), m.end() + 60)
            snippet = doc["content"][start:end]
            results.append({
                "document_id": doc["id"],
                "filename": doc["filename"],
                "score": 1.0 / (1 + start),
                "snippet": snippet,
            })
        # Sort by pseudo score and limit
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:limit]

    async def delete(self, document_id: str) -> bool:
        return self._docs.pop(document_id, None) is not None

