"""Async NotebookLM Enterprise client (transport-neutral core).

This module implements the core client for interacting with the Google Cloud Discovery Engine
v1 REST API. It handles the underlying HTTP transport via httpx, OAuth2 authentication,
loop affinity validation, automated exponential backoff retries for rate-limiting, and
specialized protocols like raw file uploads (Scotty) and interactSources (RAG queries).

It also seamlessly delegates to a mock store when mock_mode is enabled.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any, Optional

import google.auth
import google.auth.transport.requests
import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from .config import Config
from .exceptions import QuotaExceededError, translate
from .mock import MockStore


def _base_path(cfg: Config) -> str:
    """Construct the regional base URL path for the Discovery Engine API.

    Args:
        cfg: The Config object containing location and project details.

    Returns:
        The absolute base URL string.
    """
    host = f"{cfg.location}-discoveryengine.googleapis.com"
    return (
        f"https://{host}/{cfg.api_version}/projects/"
        f"{cfg.project_number}/locations/{cfg.location}"
    )


class NotebookLMClient:
    """Async client for NotebookLM Enterprise / Discovery Engine.

    This client serves as the primary entry point for managing notebooks, uploading sources,
    and running grounded Q&A. It is designed to be used as an async context manager to
    properly manage the lifecycle of the underlying httpx.AsyncClient.

    An instance of this client should ideally be reused for the same project/location/api_version
    configuration to benefit from HTTP connection pooling.

    Usage:
        async with NotebookLMClient() as client:
            notebooks = await client.notebooks.list()
    """

    def __init__(
        self,
        project_number: Optional[str | Config] = None,
        location: Optional[str] = None,
        creds: Any = None,
        api_version: Optional[str] = None,
        config: Optional[Config] = None,
    ):
        """Initialize the NotebookLM client.

        Args:
            project_number: The GCP project number (or a pre-loaded Config object).
            location: The GCP region/location (e.g., "us").
            creds: Optional pre-resolved google.auth credentials. If None, resolves via ADC.
            api_version: The Discovery Engine API version (e.g., "v1").
            config: Optional pre-loaded Config object.
        """
        if isinstance(project_number, Config):
            config = project_number
            project_number = None

        base_cfg = config or Config.load()
        # Create a localized configuration combining explicit overrides and loaded defaults.
        self.cfg = Config(
            project_number=project_number or base_cfg.project_number,
            location=location or base_cfg.location,
            api_version=api_version or base_cfg.api_version,
            mock_mode=base_cfg.mock_mode,
            poll_initial_seconds=base_cfg.poll_initial_seconds,
            poll_max_seconds=base_cfg.poll_max_seconds,
            poll_timeout_seconds=base_cfg.poll_timeout_seconds,
            retry_max_attempts=base_cfg.retry_max_attempts,
        )
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._http: Optional[httpx.AsyncClient] = None
        self._creds = creds
        self._mock = MockStore() if self.cfg.mock_mode else None

        # Namespaced sub-clients for organized API surface access.
        self.notebooks = _Notebooks(self)
        self.sources = _Sources(self)
        self.chat = _Chat(self)

    # ---- lifecycle ----
    async def __aenter__(self) -> "NotebookLMClient":
        """Enter the async context. Initializes the httpx.AsyncClient if not in mock mode.

        Validates and binds to the current running event loop.
        """
        self._loop = asyncio.get_running_loop()
        if not self.cfg.mock_mode:
            # Re-use connection pool with a reasonable timeout.
            self._http = httpx.AsyncClient(timeout=60.0)
        return self

    async def __aexit__(self, *exc) -> None:
        """Exit the async context. Clean up and close the httpx.AsyncClient."""
        if self._http:
            await self._http.aclose()

    def _guard_loop(self) -> None:
        """Verify event loop affinity to prevent cross-thread/loop connection errors.

        Since httpx.AsyncClient is bound to the event loop in which it was created,
        reusing this client instance across different event loops is unsafe and will
        raise a RuntimeError.
        """
        current = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = current
        elif self._loop is not current:
            raise RuntimeError(
                "NotebookLMClient reused across different event loops."
            )

    # ---- auth ----
    def _token(self) -> str:
        """Resolve and return a valid OAuth2 access token.

        Uses Google Application Default Credentials (ADC) with the cloud-platform scope.
        Handles automatic token refreshing if the current token has expired.

        Returns:
            The raw OAuth2 access token string.
        """
        if self._creds is None:
            self._creds, _ = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        if hasattr(self._creds, "valid") and not self._creds.valid:
            self._creds.refresh(google.auth.transport.requests.Request())
        if hasattr(self._creds, "token"):
            return self._creds.token
        return str(self._creds)

    # ---- core request with retry ----
    @retry(
        retry=retry_if_exception_type(QuotaExceededError),
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict | None = None,
    ) -> dict:
        """Issue an authorized HTTP request relative to the regional base path.

        This method is decorated with an exponential backoff retry policy targeting
        QuotaExceededError (HTTP 429), allowing graceful recovery under rate limits.

        Args:
            method: The HTTP verb (e.g., "GET", "POST", "DELETE").
            path: The API endpoint path starting with a slash (e.g., "/notebooks").
            json: Optional JSON-serializable request body.
            params: Optional query parameters.

        Returns:
            The parsed JSON response as a dictionary, or an empty dictionary if no body.

        Raises:
            RuntimeError: If called while in mock mode.
            NotebookLMError: If the server returns a non-2xx status code (mapped via translate).
        """
        self._guard_loop()
        if self.cfg.mock_mode:
            raise RuntimeError("Request called in Mock Mode")
            
        assert self._http is not None
        url = f"{_base_path(self.cfg)}{path}"
        headers = {
            "Authorization": f"Bearer {self._token()}",
            "X-Request-Id": str(uuid.uuid4()),
        }
        resp = await self._http.request(
            method, url, json=json, params=params, headers=headers
        )
        if resp.status_code >= 400:
            raise translate(resp.status_code, resp.text)
        return resp.json() if resp.content else {}

    async def request_raw(
        self,
        method: str,
        path: str,
        *,
        headers: dict | None = None,
    ) -> bytes:
        """Issue an authorized HTTP request and return the raw response bytes.

        Useful for downloading raw assets or streaming payloads where JSON decoding is inappropriate.

        Args:
            method: The HTTP verb.
            path: The API endpoint path.
            headers: Optional dictionary of additional request headers.

        Returns:
            The raw response content as bytes.

        Raises:
            RuntimeError: If called while in mock mode.
            NotebookLMError: If the server returns a non-2xx status code.
        """
        self._guard_loop()
        if self.cfg.mock_mode:
            raise RuntimeError("Request called in Mock Mode")
            
        assert self._http is not None
        url = f"{_base_path(self.cfg)}{path}"
        req_headers = {
            "Authorization": f"Bearer {self._token()}",
            "X-Request-Id": str(uuid.uuid4()),
        }
        if headers:
            req_headers.update(headers)
        resp = await self._http.request(
            method, url, headers=req_headers
        )
        if resp.status_code >= 400:
            raise translate(resp.status_code, resp.text)
        return resp.content


class _Notebooks:
    """Sub-client managing RAG Notebook (Data Store) lifecycle operations."""

    def __init__(self, c: NotebookLMClient):
        self._c = c

    async def create(self, title: str) -> dict:
        """Create a new notebook.

        Args:
            title: The display title of the notebook.

        Returns:
            The created notebook's metadata.
        """
        if self._c._mock:
            return self._c._mock.create_notebook(title)
        return await self._c.request("POST", "/notebooks", json={"title": title})

    async def get(self, notebook_id: str) -> dict:
        """Retrieve details and sources of a specific notebook.

        Args:
            notebook_id: The unique ID of the notebook.

        Returns:
            The notebook's metadata and sources list.
        """
        if self._c._mock:
            return self._c._mock.get_notebook(notebook_id)
        return await self._c.request("GET", f"/notebooks/{notebook_id}")

    async def list(self) -> dict:
        """List all notebooks recently accessed or created by the caller.

        Returns:
            A dictionary containing a list of notebook objects under the "notebooks" key.
        """
        if self._c._mock:
            return {"notebooks": self._c._mock.list_notebooks()}
        return await self._c.request("GET", "/notebooks:listRecentlyViewed")

    async def delete(self, notebook_id: str) -> dict:
        """Delete a notebook and all its ingested sources.

        Args:
            notebook_id: The unique ID of the notebook.

        Returns:
            A dictionary indicating success.
        """
        if self._c._mock:
            return self._c._mock.delete_notebook(notebook_id)
        name = (
            f"projects/{self._c.cfg.project_number}/locations/"
            f"{self._c.cfg.location}/notebooks/{notebook_id}"
        )
        return await self._c.request(
            "POST", "/notebooks:batchDelete", json={"names": [name]}
        )


class _Sources:
    """Sub-client managing document ingestion (Text, Web, GCS, and Local Files)."""

    def __init__(self, c: NotebookLMClient):
        self._c = c

    async def add_text(self, notebook_id: str, name: str, content: str) -> dict:
        """Ingest raw text content as a new source in a notebook.

        Args:
            notebook_id: The ID of the target notebook.
            name: The display name of the source (e.g., "notes.txt").
            content: The plain text content to ingest.

        Returns:
            The metadata of the ingested source.
        """
        body = {"userContents": [{"textContent": {"sourceName": name, "content": content}}]}
        return await self._batch(notebook_id, body)

    async def add_web(self, notebook_id: str, name: str, url: str) -> dict:
        """Ingest a web page URL as a source.

        Args:
            notebook_id: The ID of the target notebook.
            name: The display name for this web source.
            url: The web URL to crawl and ingest.

        Returns:
            The metadata of the ingested source.
        """
        body = {"userContents": [{"webContent": {"sourceName": name, "url": url}}]}
        return await self._batch(notebook_id, body)

    async def add_gcs(self, notebook_id: str, uris: list[str]) -> dict:
        """Ingest files directly from Google Cloud Storage URIs.

        Args:
            notebook_id: The ID of the target notebook.
            uris: A list of GCS URIs (e.g., ["gs://bucket/doc.pdf"]).

        Returns:
            The metadata of the ingested sources.
        """
        body = {"userContents": [{"gcsSource": {"uris": uris}}]}
        return await self._batch(notebook_id, body)

    async def _batch(self, notebook_id: str, body: dict) -> dict:
        """Private helper to perform a batchCreate sources request."""
        if self._c._mock:
            return self._c._mock.add_sources(notebook_id, body)
        return await self._c.request(
            "POST", f"/notebooks/{notebook_id}/sources:batchCreate", json=body
        )

    async def upload_file(self, notebook_id: str, file_path: str, mime_type: str) -> dict:
        """Upload and ingest a local file using the Google Scotty raw upload protocol.

        This method reads a local file in full, enforces a client-side 50MB safety limit,
        and executes a single-shot HTTP POST request directly to the upload endpoint.

        The Scotty protocol requires specific headers:
        - `X-Goog-Upload-Protocol: raw`: Specifies a single-shot raw body upload.
        - `X-Goog-Upload-File-Name`: Establishes the target filename on the server.
        - `Content-Type`: Sets the MIME type of the file.

        Args:
            notebook_id: The ID of the notebook workspace.
            file_path: The local filesystem path to the file.
            mime_type: The MIME type of the file (e.g., "application/pdf").

        Returns:
            The metadata of the ingested file source.

        Raises:
            ValueError: If the file size exceeds the 50MB limit.
            NotebookLMError: If the upload request fails.
        """
        filename = os.path.basename(file_path)
        with open(file_path, "rb") as f:
            content = f.read()

        # Client-side validation (PRD 50MB limit)
        if len(content) > 50 * 1024 * 1024:
            raise ValueError("File size exceeds 50MB limit")

        if self._c._mock:
            return self._c._mock.upload_file(notebook_id, filename, content)

        # Build the regional upload path
        upload_path = (
            f"/upload/{self._c.cfg.api_version}/projects/{self._c.cfg.project_number}/"
            f"locations/{self._c.cfg.location}/notebooks/{notebook_id}/sources:uploadFile"
        )
        host = f"{self._c.cfg.location}-discoveryengine.googleapis.com"
        url = f"https://{host}{upload_path}"

        headers = {
            "Authorization": f"Bearer {self._c._token()}",
            "X-Request-Id": str(uuid.uuid4()),
            "X-Goog-Upload-Protocol": "raw",
            "X-Goog-Upload-File-Name": filename,
            "Content-Type": mime_type,
        }

        self._c._guard_loop()
        assert self._c._http is not None
        resp = await self._c._http.request(
            "POST", url, content=content, headers=headers
        )
        if resp.status_code >= 400:
            raise translate(resp.status_code, resp.text)
        return resp.json()


class _Chat:
    """Sub-client managing conversational Q&A and grounding context."""

    def __init__(self, c: NotebookLMClient):
        self._c = c

    async def ask(
        self, notebook_id: str, query: str, source_ids: list[str] | None = None
    ) -> dict:
        """Run a grounded query against a notebook's sources using interactSources.

        This method executes a two-step process:
        1. It fetches the notebook's metadata to retrieve all active source references.
        2. It maps those source references into the nested `input_sources` structure
           required by the Discovery Engine `interactSources` REST endpoint, optionally
           filtering by a list of explicit `source_ids`.

        The `interactSources` API schema demands a list of sources formatted as:
        ```json
        "input_sources": [
            {
                "source_id": {
                    "id": "<source_uuid>"
                }
            }
        ]
        ```

        Args:
            notebook_id: The ID of the notebook.
            query: The user's question or prompt.
            source_ids: Optional list of source IDs to restrict grounding to. If None,
                all sources in the notebook are utilized.

        Returns:
            A dictionary containing the RAG-generated response and citations:
            {
                "answer": "...",
                "citations": [...]
            }
        """
        if self._c._mock:
            return self._c._mock.ask(notebook_id, query, source_ids)

        # 1. Fetch the notebook to retrieve source references (grounding context)
        notebook = await self._c.notebooks.get(notebook_id)
        sources = notebook.get("sources", [])

        # 2. Extract and optionally filter the sourceId nested structures
        input_sources = []
        for src in sources:
            source_id_dict = src.get("sourceId", {})
            if source_id_dict:
                sid = source_id_dict.get("id")
                if source_ids is None or (sid and sid in source_ids):
                    input_sources.append({
                        "source_id": source_id_dict
                    })

        # 3. Issue the POST request to the live API
        name = (
            f"projects/{self._c.cfg.project_number}/locations/"
            f"{self._c.cfg.location}/notebooks/{notebook_id}"
        )
        return await self._c.request(
            "POST",
            f"/notebooks/{notebook_id}:interactSources",
            json={
                "name": name,
                "input_sources": input_sources,
                "free_form_action": {
                    "user_query": query,
                },
            },
        )
