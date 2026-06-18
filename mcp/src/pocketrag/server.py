"""FastMCP server exposing PocketRAG (NotebookLM Enterprise) tools to AI assistants.

This server acts as a bridge, exposing the NotebookLM API features as Model Context Protocol (MCP)
tools. It supports stdio transport, allowing integration with AI clients like Claude Desktop, Cursor,
and Windsurf.

Running the server:
    python3 -m pocketrag.server
"""
from __future__ import annotations

from fastmcp import FastMCP

from .client import NotebookLMClient

# Initialize the FastMCP server instance.
mcp = FastMCP("pocketrag")


@mcp.tool()
async def list_notebooks() -> dict:
    """List all RAG notebooks (Data Stores) accessible to the caller.

    This tool retrieves the metadata of all notebooks in the configured project
    and region, allowing the LLM to inspect available workspaces.

    Returns:
        A dictionary containing the list of notebooks:
        {"notebooks": [{"notebookId": "...", "title": "...", ...}]}
    """
    async with NotebookLMClient() as client:
        return await client.notebooks.list()


@mcp.tool()
async def create_notebook(title: str) -> dict:
    """Create a new RAG notebook (Data Store).

    Use this tool to spin up a new isolated RAG workspace before adding sources.

    Args:
        title: The user-defined title for the new notebook.

    Returns:
        The metadata of the newly created notebook, including its generated notebookId.
    """
    async with NotebookLMClient() as client:
        return await client.notebooks.create(title)


@mcp.tool()
async def add_text_source(notebook_id: str, name: str, content: str) -> dict:
    """Add a raw-text source (e.g., notes, logs, or articles) to a notebook.

    Ingests direct text content as a grounding source in the specified notebook.

    Args:
        notebook_id: The ID of the target notebook.
        name: A descriptive name/title for the text source (e.g., "meeting_notes.txt").
        content: The raw text content to be ingested.

    Returns:
        A dictionary containing the metadata of the created source.
    """
    async with NotebookLMClient() as client:
        return await client.sources.add_text(notebook_id, name, content)


@mcp.tool()
async def upload_file_source(notebook_id: str, file_path: str, mime_type: str = "application/pdf") -> dict:
    """Upload a local file (e.g., PDF, TXT) to a notebook workspace.

    This tool reads a local file from the system running this MCP server and
    uploads it directly using the secure Scotty protocol. Max file size is 50MB.

    Args:
        notebook_id: The ID of the target notebook.
        file_path: The absolute or relative path to the local file to upload.
        mime_type: The MIME type of the file (defaults to "application/pdf").

    Returns:
        The metadata of the ingested file source.
    """
    async with NotebookLMClient() as client:
        return await client.sources.upload_file(notebook_id, file_path, mime_type)


@mcp.tool()
async def ask_notebook(notebook_id: str, query: str) -> dict:
    """Run a grounded, synthesized query against a notebook's sources.

    This tool issues a query to the NotebookLM RAG engine. It automatically retrieves
    all sources in the notebook to act as grounding context (using the interactSources protocol)
    and returns a synthesized answer based *only* on those sources.

    Args:
        notebook_id: The ID of the notebook containing the grounding sources.
        query: The natural language question or instruction.

    Returns:
        A dictionary containing:
        - "answer": The synthesized text response.
        - "citations": Grounding source citations used in the answer.
    """
    async with NotebookLMClient() as client:
        return await client.chat.ask(notebook_id, query)


@mcp.tool()
async def delete_notebook(notebook_id: str) -> dict:
    """Tear down and permanently delete a RAG notebook.

    Warning: This action is destructive and removes the notebook along with all
    associated ingested sources.

    Args:
        notebook_id: The ID of the notebook to delete.

    Returns:
        A confirmation dictionary indicating successful deletion.
    """
    async with NotebookLMClient() as client:
        return await client.notebooks.delete(notebook_id)


def main() -> None:
    """Entry point for running the FastMCP server via command line."""
    # stdio transport is what Cursor / Claude Desktop / Windsurf expect.
    mcp.run()


if __name__ == "__main__":
    main()
