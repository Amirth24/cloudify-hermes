"""Mem0 bridge — OpenViking → Mem0 hourly push with knowledge graph categorization."""
from __future__ import annotations
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    "preference": "user_profile",
    "entity": "environment",
    "pattern": "patterns",
    "event": "shared",
    "case": "shared",
}

def categorize_entry(entry: dict) -> str:
    """Map an OpenViking memory entry to a Mem0 category (knowledge graph)."""
    entry_type = entry.get("type", "")
    return CATEGORY_MAP.get(entry_type, "shared")

class Mem0Bridge:
    def __init__(
        self,
        ov_endpoint: str = "http://localhost:8765",
        mem0_api_key: str = "",
        user_id: str = "",
        agent_id: str = "hermes",
    ):
        self.ov_endpoint = ov_endpoint
        self.mem0_api_key = mem0_api_key
        self.user_id = user_id
        self.agent_id = agent_id
        self._client = None

    def _get_mem0_client(self):
        """Lazy-init Mem0 client (managed platform via MemoryClient)."""
        if self._client is not None:
            return self._client
        try:
            from mem0 import MemoryClient
            self._client = MemoryClient(api_key=self.mem0_api_key)
        except ImportError:
            logger.error("mem0ai not installed — run pip install mem0ai")
            raise
        return self._client

    def fetch_ov_entries(self) -> List[dict]:
        """Fetch all entries from OpenViking via HTTP API."""
        import httpx
        # OpenViking API: POST /api/v1/search/find
        resp = httpx.post(
            f"{self.ov_endpoint}/api/v1/search/find",
            json={"query": "user environment preferences patterns entities", "limit": 100, "score_threshold": 0.0},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        memories = data.get("result", {}).get("memories", [])
        # Extract content from abstract field and categorize by URI path
        entries = []
        for mem in memories:
            uri = mem.get("uri", "")
            abstract = mem.get("abstract", "")
            # Determine type from URI path
            if "/preferences/" in uri:
                mem_type = "preference"
            elif "/entities/" in uri:
                mem_type = "entity"
            elif "/patterns/" in uri:
                mem_type = "pattern"
            elif "/events/" in uri:
                mem_type = "event"
            else:
                mem_type = "shared"
            entries.append({"content": abstract, "type": mem_type, "uri": uri})
        return entries

    def push_entries(self, entries: List[dict]):
        """Push entries to Mem0 with category-based knowledge graphs."""
        client = self._get_mem0_client()
        for entry in entries:
            category = categorize_entry(entry)
            content = entry.get("content", "")
            if not content:
                continue
            try:
                client.add(
                    content,
                    user_id=self.user_id,
                    agent_id=self.agent_id,
                    metadata={"category": category, "source": "openviking"},
                )
                logger.debug("Pushed to Mem0 [%s]: %s", category, content[:50])
            except Exception as e:
                logger.warning("Mem0 push failed for entry: %s", e)

    def sync(self):
        """Full sync: fetch from OV, push to Mem0."""
        entries = self.fetch_ov_entries()
        logger.info("Fetched %d entries from OpenViking", len(entries))
        self.push_entries(entries)
        logger.info("Synced %d entries to Mem0", len(entries))