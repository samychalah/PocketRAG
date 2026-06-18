"""In-memory mock store for local POC runs.

This module provides a pure-Python, in-memory implementation of the NotebookLM Enterprise
data structures and operations. It allows developers to run, test, and demonstrate the MCP
server locally without requiring access to a live, allowlisted Google Cloud Project.
"""
from __future__ import annotations

import uuid
from typing import Any

from .exceptions import NotebookNotFoundError


class MockStore:
    """An in-memory store simulating the Discovery Engine / NotebookLM backend.

    This class maintains a thread-safe-ish (for single-process asyncio) global-like state
    of mock notebooks, sources, and shares using a class-level dictionary. The structures
    returned by these methods mimic the JSON schemas returned by the real Google Cloud APIs.
    
    Attributes:
        _nb: A class-level dictionary mapping notebook IDs to their mock notebook
             representation (metadata, sources, shares, etc.).
    """
    _nb: dict[str, dict] = {}

    def __init__(self) -> None:
        pass

    def create_notebook(self, title: str) -> dict:
        """Simulate creating a new notebook (Data Store).

        Args:
            title: The user-defined title of the notebook.

        Returns:
            A dictionary representing the created notebook, matching the structure:
            {
                "name": "projects/.../locations/.../notebooks/<id>",
                "notebookId": "<id>",
                "title": "<title>",
                "sources": [],
                "shares": []
            }
        """
        nid = uuid.uuid4().hex[:12]
        nb = {
            "name": f"notebooks/{nid}",
            "notebookId": nid,
            "title": title,
            "sources": [],
            "shares": [],
        }
        self._nb[nid] = nb
        return nb

    def _require(self, nid: str) -> dict:
        """Helper to retrieve a notebook or raise NotebookNotFoundError if it doesn't exist.

        Args:
            nid: The notebook ID.

        Returns:
            The mock notebook dictionary.

        Raises:
            NotebookNotFoundError: If the notebook ID is not in the store.
        """
        if nid not in self._nb:
            raise NotebookNotFoundError(nid)
        return self._nb[nid]

    def get_notebook(self, nid: str) -> dict:
        """Retrieve a specific notebook's metadata and sources.

        Args:
            nid: The notebook ID.

        Returns:
            The mock notebook dictionary.
        """
        return self._require(nid)

    def list_notebooks(self) -> list[dict]:
        """List all notebooks currently stored in memory.

        Returns:
            A list of mock notebook dictionaries.
        """
        return list(self._nb.values())

    def delete_notebook(self, nid: str) -> dict:
        """Remove a notebook and all its associated sources from the in-memory store.

        Args:
            nid: The notebook ID to delete.

        Returns:
            A confirmation dictionary: {"deleted": "<notebook_id>"}
        """
        self._require(nid)
        del self._nb[nid]
        return {"deleted": nid}

    def share(self, nid: str, email: str, role: str) -> dict:
        """Simulate sharing a notebook with a user.

        Args:
            nid: The notebook ID.
            email: The email of the user to share with.
            role: The role/permission level (e.g., "READER", "WRITER").

        Returns:
            A dictionary containing the updated list of shares.
        """
        nb = self._require(nid)
        nb["shares"].append({"email": email, "role": role})
        return {"shares": nb["shares"]}

    def add_sources(self, nid: str, body: dict[str, Any]) -> dict:
        """Simulate adding structured sources (text, web, GCS) in batch.

        Args:
            nid: The notebook ID.
            body: The batchCreate request body containing "userContents".

        Returns:
            A dictionary containing the list of newly added sources with generated IDs:
            {"sources": [{"sourceId": {"id": "<id>"}, "content": {...}}]}
        """
        nb = self._require(nid)
        added = []
        for uc in body.get("userContents", []):
            sid = uuid.uuid4().hex[:8]
            src = {
                "sourceId": {"id": sid},
                "content": uc
            }
            nb["sources"].append(src)
            added.append(src)
        return {"sources": added}

    def upload_file(self, nid: str, filename: str, content: bytes) -> dict:
        """Simulate uploading a local file to the notebook.

        Args:
            nid: The notebook ID.
            filename: The original name of the uploaded file.
            content: The raw bytes of the file.

        Returns:
            A dictionary containing the newly created file source:
            {"sources": [{"sourceId": {"id": "<id>"}, "content": {"fileContent": ...}}]}
        """
        nb = self._require(nid)
        sid = uuid.uuid4().hex[:8]
        src = {
            "sourceId": {"id": sid},
            "content": {
                "fileContent": {
                    "sourceName": filename,
                    "sizeBytes": len(content)
                }
            }
        }
        nb["sources"].append(src)
        return {"sources": [src]}

    def ask(self, nid: str, query: str, source_ids: list[str] | None = None) -> dict:
        """Simulate running a grounded Q&A query against the notebook's sources.

        This method mimics the `interactSources` API endpoint by returning a synthesized
        answer and a set of grounding citations pointing to the mock sources.

        Args:
            nid: The notebook ID.
            query: The user's natural language question.
            source_ids: Optional list of source IDs to restrict the grounding context to.

        Returns:
            A dictionary representing the grounded answer and citation metadata:
            {
                "answer": "[MOCK] Grounded response...",
                "citations": [{"sourceId": {"id": "<source_id>"}}, ...]
            }
        """
        nb = self._require(nid)
        sources = nb["sources"]
        if source_ids is not None:
            sources = [s for s in sources if s["sourceId"]["id"] in source_ids]
        n = len(sources)
        return {
            "answer": f"[MOCK] Grounded response to your query '{query}' based on {n} source(s).",
            "citations": [{"sourceId": s["sourceId"]} for s in sources[:3]],
        }
