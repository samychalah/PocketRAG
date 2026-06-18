---
name: pocketrag
description: Zero-infrastructure portable RAG skill to ground conversations in documents using Vertex AI Discovery Engine (NotebookLM Enterprise). Triggers on "ground in these files", "run a query on my documents", "create a RAG", "upload document", or "/rag".
alwaysApply: false
allowed-tools:
  - list_notebooks
  - create_notebook
  - add_text_source
  - ask_notebook
  - delete_notebook
---

# Portable RAG Skill (PocketRAG)

Use this skill to turn any set of documents (PDF/TXT) into an instant, managed RAG backend without managing vector databases or pipeline code.

## 🧭 Core Workflow

When the user asks to analyze or chat with documents:

1.  **Resolve & Check Registry:**
    *   **Registry Location Resolution:** Look for the session registry at the workspace root in the following order of preference:
        1. Inside the active project instruction file if it exists (`CLAUDE.md`, `AGENTS.md`, or `GEMINI.md`). Check the very bottom of the file for the `<!-- pocketrag_registry_start -->` block.
        2. If none of the above files exist, look for a local `.pocketrag_registry.json` file at the workspace root.
    *   **Check Active Notebooks:** Parse the registry. If active notebooks are found, list them and ask: *"Would you like to reuse your existing RAG notebook '{title}' or start a fresh one?"*
    *   **Provisioning:** If starting fresh or no registry is found, trigger `create_notebook` to establish a new Data Store.

2.  **Ingest Documents:**
    *   Ask the user for the text content or file path.
    *   For raw text notes or small documents, use `add_text_source` to ingest them inline.
    *   For local files, use `upload_file_source`.
    *   **Update Registry:** Write the notebook metadata (ID, title, created timestamp) back to the resolved registry location (appending the JSON block to the active instruction file, or writing to `.pocketrag_registry.json`).

3.  **Perform Grounded Queries:**
    *   Use `ask_notebook` to query the notebook.
    *   Present the answer beautifully to the user. All answers are fully grounded in the uploaded documents.

4.  **Resource Hygiene:**
    *   If the user is done with their task or requests a cleanup, use `delete_notebook` to tear down the Discovery Engine Data Store and prevent resource leaks. Remove the deleted notebook ID from the session registry.

## 🛠️ Tool Reference

*   `list_notebooks()`: List all active RAG notebooks in the workspace.
*   `create_notebook(title)`: Programmatically provision a new RAG notebook (Data Store).
*   `add_text_source(notebook_id, name, content)`: Ingest raw text or small documents inline.
*   `ask_notebook(notebook_id, query)`: Issue a grounded, synthesized RAG query against the notebook.
*   `delete_notebook(notebook_id)`: Tear down and delete the RAG notebook.

## 📝 Session Memory Registry

To maintain persistence across chat sessions and enable **collaborative RAG sharing** (so other team members or agents opening this repository can immediately reuse the same RAG notebooks), always persist active notebook metadata.

### Option A: Project Instruction Files (Recommended for Shared Repositories)
If `CLAUDE.md`, `AGENTS.md`, or `GEMINI.md` exists at the workspace root, append the registry JSON block at the very bottom of that file:

```markdown
## 🗄️ PocketRAG Session Registry
<!-- pocketrag_registry_start -->
{
  "active_notebooks": [
    {
      "id": "ds_1234abcd",
      "title": "API Specification Docs",
      "created_at": "2026-06-18T02:15:00Z"
    }
  ]
}
<!-- pocketrag_registry_end -->
```

### Option B: Local Registry File (Recommended for Private/Clean Workspaces)
If no project instruction files exist, create and maintain a dedicated `.pocketrag_registry.json` file at the workspace root:

```json
{
  "active_notebooks": [
    {
      "id": "ds_1234abcd",
      "title": "API Specification Docs",
      "created_at": "2026-06-18T02:15:00Z"
    }
  ]
}
```
*(Tip: Suggest the user add `.pocketrag_registry.json` to `.gitignore` if they want to keep their active RAG notebooks private).*

### Registry Rules
* **Size Cap:** Ensure the registry does not grow indefinitely; cap it to the **last 10 notebooks** and prune older ones, notifying the user.
* **Graceful Parsing:** If the registry file or JSON block is malformed or corrupted, log a warning, notify the user, and rebuild it gracefully starting from an empty list.
