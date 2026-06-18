# 📄 PocketRAG

### *Bring your own documents to any LLM in 60 seconds — no vector DB, no pipeline, no servers.*

[![FastMCP](https://img.shields.io/badge/FastMCP-Server-orange.svg)](https://github.com/modelcontextprotocol)
[![GCP Vertex AI](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-blue.svg)](https://cloud.google.com/vertex-ai)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**PocketRAG** is a zero-infrastructure, ultra-portable agent plugin (combining a self-contained FastMCP server and a global agent skill) that turns **NotebookLM Enterprise** (powered by the **Vertex AI Discovery Engine API**) into an instant, managed RAG backend for any LLM client. 

Whether you are chatting with Claude Desktop, prompting in Cursor, or utilizing Gemini/Antigravity agents, PocketRAG allows you to instantly ground conversations in your local PDFs, text files, and notes in under a minute—keeping your data fully contained within your own Google Cloud security perimeter.

---

## 💡 Core Value Proposition

In traditional RAG setups, developer velocity is throttled by complex infrastructure pipelines. Standing up a chunker, embedder, vector database, and custom retrieval logic is excessive for ad-hoc coding tasks or project-specific document Q&A.

**PocketRAG is revolutionary because it is entirely infrastructure-free.** By utilizing Google's enterprise-grade Vertex AI Discovery Engine API (the same engine powering NotebookLM), all chunking, embedding, indexing, retrieval, and grounded synthesis are handled by a single managed API. Your documents are uploaded, processed, and ready for grounded queries in seconds, with zero servers to maintain and zero infrastructure overhead.

### Architecture & Complexity Comparison

| Feature / Aspect | Traditional RAG Pipeline | PocketRAG (NotebookLM-as-a-RAG) |
| :--- | :--- | :--- |
| **Infrastructure Setup** | Provisioning servers, vector databases, cache layers, and ingestion pipelines. | **Zero-Infra.** Instantly provisioned managed Data Stores on Google Cloud. |
| **Chunking & Embedding** | Writing custom chunking strategies (overlap, recursive) and maintaining embedding models. | **Fully Managed.** Google's state-of-the-art embedding models and optimal chunking out-of-the-box. |
| **Vector Database** | Managing, scaling, and paying for Pinecone, Weaviate, PGVector, etc. ($100s/mo). | **No Vector DB.** Uses Google's highly optimized, serverless Discovery Engine. |
| **Retrieval & Grounding** | Custom similarity search, MMR, re-ranking models, and context window packing. | **Automatic.** Google's managed `:answer` API performs high-fidelity retrieval and synthesis. |
| **Maintenance & Drift** | Pipeline monitoring, index rebuilding, and library version alignment. | **Zero Maintenance.** Directly calls Google Cloud serverless APIs with enterprise SLAs. |
| **Setup Time** | Days to weeks of development and tuning. | **⏱️ Under 60 seconds.** Run one installer and start querying. |

---

## ⚙️ How It Works (Architecture)

PocketRAG operates as a lightweight bridge between your local AI editor/client and Google Cloud. Instead of maintaining a complex database, the PocketRAG Model Context Protocol (MCP) server translates standard RAG tool calls from your AI client into direct REST calls to the **Vertex AI Discovery Engine API**. 

When you upload a document or ask a question, the MCP server orchestrates the interaction securely using your own Google Cloud credentials, ensuring your data never leaves your control.

```mermaid
flowchart TD
    subgraph Client["💻 Local AI Client (Claude / Cursor / Gemini)"]
        U["🧑 User / Developer"]
        AC["🤖 AI Assistant<br/>(Orchestrator)"]
        Mem[("🗄️ Session Registry<br/>(CLAUDE.md / .pocketrag_registry.json)")]
    end

    subgraph MCP["🔌 PocketRAG MCP Server (Local)"]
        Server["FastMCP Server<br/>(python3 -m pocketrag.server)"]
        ClientAPI["Async Client<br/>(OAuth / ADC Authorized)"]
    end

    subgraph GCP["☁️ Google Cloud Platform (User's Project)"]
        DE["Vertex AI Discovery Engine API<br/>(NotebookLM Enterprise Engine)"]
        DS[("Managed Data Store<br/>(The 'Notebook')")]
        GCS[("Cloud Storage Bucket<br/>(Large-File Stage Fallback)")]
    end

    U -->|"1. 'Ground in these docs'"| AC
    AC <-->|"2. Resolve active notebook ID"| Mem
    AC -->|"3. Call MCP Tools<br/>(create_notebook, upload_file_source)"| Server
    Server -->|"4. Ingest & Index Docs"| ClientAPI
    
    ClientAPI -->|"5a. Small File: Inline Base64 Import"| DE
    ClientAPI -->|"5b. Large File (>6MB): Upload & Stage"| GCS
    GCS -->|"5c. Import via gcsSource"| DE
    
    DE ---> DS
    
    AC -->|"6. Call ask_notebook(query)"| Server
    Server -->|"7. Grounded query (:answer)"| ClientAPI
    ClientAPI --> DE
    DE -->|"8. Retrieve & Synthesize"| DS
    DE -->>|"9. Return grounded response"| ClientAPI
    ClientAPI -->>|"10. Return synthesized answer"| AC
    AC -->>|"11. Display answer with citations"| U
```

---

## 🔌 Seamless Multi-Client Integration

PocketRAG is built on the open **Model Context Protocol (MCP)**, allowing it to integrate seamlessly with any modern AI editor or client.

### 1. Claude Desktop
The unified installer automatically registers PocketRAG with Claude Desktop. 

Under the hood, the installer appends the server configuration to your `claude_desktop_config.json` (located at `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS). It sets up the server to run in stdio transport mode:

```json
{
  "mcpServers": {
    "pocketrag": {
      "command": "/path/to/PocketRAG/mcp/.venv/bin/python3",
      "args": [
        "-m",
        "pocketrag.server"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
      }
    }
  }
}
```

### 2. Cursor
To use PocketRAG as a powerful grounding engine directly inside your Cursor editor:
1. Open **Cursor Settings** (gear icon in the top-right) > **Features** > **MCP**.
2. Click **+ Add New MCP Server**.
3. Configure the server with the following details:
   * **Name:** `pocketrag`
   * **Type:** `command`
   * **Command:** `/path/to/PocketRAG/mcp/.venv/bin/python3 -m pocketrag.server`
     
     > [!IMPORTANT]
     > Replace `/path/to/PocketRAG` with the actual absolute path to your cloned PocketRAG repository (e.g., `/Users/your-username/Projects/PocketRAG`). Avoid committing personal absolute paths to public repositories.

4. Click **Save**. The green status indicator should appear, showing that Cursor has successfully connected to the PocketRAG tools.

### 3. Gemini / Antigravity
PocketRAG is packaged with a pre-configured global agent skill. The installer automatically copies the skill descriptor (`skills/pocketrag/SKILL.md`) to your global customizations root:
* **macOS/Linux:** `~/.gemini/config/skills/pocketrag/`

Any Antigravity-powered autonomous agent or LLM client utilizing this customization root will automatically discover and load the `pocketrag` skill, equipping it with the ability to manage notebooks and query your documents programmatically.

---

## 👥 Collaborative RAG Sharing & Session Registry

One of PocketRAG's most innovative features is its **Session Registry**. AI assistants need to know which notebooks are already active in a workspace to avoid costly and slow re-indexing operations. PocketRAG implements a bi-directional persistence model that allows agents and human developers to collaborate seamlessly.

### How it Works: Shared RAG Context
When an agent creates a new RAG notebook or uploads documents, it automatically records the notebook's unique metadata (ID, title, and timestamp) in the project workspace. 

By default, the skill scans your workspace for active project instruction files in the following order of preference:
1. **`CLAUDE.md`**
2. **`AGENTS.md`**
3. **`GEMINI.md`**

If any of these files are present, the agent appends a structured XML/Markdown registry block at the very bottom of the file:

```markdown
## 🗄️ PocketRAG Session Registry
<!-- pocketrag_registry_start -->
{
  "active_notebooks": [
    {
      "id": "projects/YOUR_GCP_PROJECT_NUMBER/locations/us/collections/default_collection/dataStores/my-project-docs-12345",
      "title": "Project Architecture & Codebase Specs",
      "created_at": "2026-06-18T04:15:00Z"
    }
  ]
}
<!-- pocketrag_registry_end -->
```

> [!TIP]
> **Instant Collaborative RAG:** When you commit this registry block to your Git repository, **any team member or AI agent who clones or opens the repository instantly inherits the exact same RAG context!** They can immediately query the pre-indexed documents without uploading or paying for re-indexing, enabling friction-free team collaboration.

### Clean Workspace Fallback (`.pocketrag_registry.json`)
If your project does not use instruction files, or if you prefer to keep your active RAG sessions private and out of version control, PocketRAG falls back to writing a standalone local registry file:
* **Path:** `.pocketrag_registry.json` at your workspace root.

*Recommendation:* Add `.pocketrag_registry.json` to your project's `.gitignore` to prevent committing private RAG sessions to your public repository.

---

## 🛠️ Exposed RAG Tools

The FastMCP server exposes 5 core, high-fidelity tools designed to give LLMs full control over their RAG context:

### 1. `list_notebooks`
* **Description:** Retrieves the metadata of all active RAG notebooks (Data Stores) in your configured Google Cloud project and region. Allows the LLM to inspect available workspaces.
* **Arguments:** None.
* **Returns:** 
  ```json
  {
    "notebooks": [
      {
        "notebookId": "ds_example_123",
        "title": "API Specifications",
        "createTime": "2026-06-18T00:00:00Z"
      }
    ]
  }
  ```

### 2. `create_notebook`
* **Description:** Programmatically provisions a new, isolated RAG notebook (Discovery Engine Data Store) in your Google Cloud project.
* **Arguments:**
  * `title` *(string, required)*: A descriptive, user-friendly name for the notebook workspace.
* **Returns:** The metadata of the newly created notebook, including its generated `notebookId`.

### 3. `add_text_source`
* **Description:** Ingests raw text content (notes, logs, code snippets, or articles) directly into a notebook. Ideal for quick inline notes.
* **Arguments:**
  * `notebook_id` *(string, required)*: The ID of the target notebook.
  * `name` *(string, required)*: A descriptive name for the text source (e.g., `deployment_notes.txt`).
  * `content` *(string, required)*: The raw text content to ingest (must be less than 750 KB).
* **Returns:** Ingestion metadata confirming the source has been added.

### 4. `upload_file_source`
* **Description:** Uploads a local file (such as a PDF or TXT document) from the host system running the MCP server directly into a notebook using Google's secure Scotty protocol. Supports files up to 50MB.
* **Arguments:**
  * `notebook_id` *(string, required)*: The ID of the target notebook.
  * `file_path` *(string, required)*: The absolute or relative path to the local file.
  * `mime_type` *(string, optional)*: The MIME type of the file (defaults to `application/pdf`).
* **Returns:** Ingestion metadata confirming the file has been received and indexing has started.

### 5. `ask_notebook`
* **Description:** Issues a grounded, natural language query against all sources in the notebook. Retrieves relevant passages and returns a synthesized answer based *strictly* on your documents.
* **Arguments:**
  * `notebook_id` *(string, required)*: The ID of the notebook containing the grounding sources.
  * `query` *(string, required)*: The question or instructions for the RAG engine.
* **Returns:**
  ```json
  {
    "answer": "Synthesized, highly grounded response...",
    "citations": [ ... ]
  }
  ```

> [!NOTE]
> **Resource Cleanup:** For completeness, the server also exposes `delete_notebook(notebook_id)`, allowing the agent or user to permanently tear down the notebook and delete all associated documents when a task is finished, avoiding resource clutter.

---

## 🚀 Quickstart & Verification

Follow these steps to get PocketRAG running locally and connected to your live Google Cloud environment.

### 1. Run the Unified Installer
At the root of the repository, execute the unified installation script. This script automates the bootstrapping of the Python environment, installs the global Gemini skill, and registers the server with Claude Desktop:

```bash
chmod +x install.sh
./install.sh
```

#### What the installer does:
1. **Bootstraps Python:** Creates a virtual environment at `mcp/.venv` and installs all dependencies (including `fastmcp`, `google-cloud-discoveryengine`, and `pytest`).
2. **Registers Gemini/Antigravity Skill:** Installs the global skill instructions in your global customizations directory (`~/.gemini/config/skills/pocketrag/`).
3. **Configures Claude Desktop:** Automatically registers the `pocketrag` MCP server in your local `claude_desktop_config.json`.

---

### 2. Verify with the Decoupled Mock Test Suite
Before connecting to Google Cloud, verify that the MCP server and tool registry function correctly by running the offline test suite. This runs E2E RAG flows using a high-fidelity in-memory mock client:

```bash
cd mcp
.venv/bin/pytest tests/
```
All tests should pass, confirming that the tool routing, mocking, and registry operations are fully operational.

---

### 3. Switch to Live Google Cloud
To connect PocketRAG to your actual Google Cloud Platform environment, update the configuration file at **`mcp/config.yaml`**:

```yaml
project_number: "YOUR_GCP_PROJECT_NUMBER"  # e.g., "123456789012"
location: "us"                             # The GCP region for your data stores (e.g., 'us', 'eu')
api_version: "v1alpha"                     # Pinned to v1alpha for the /notebooks resource
mock_mode: false                           # Set to false to disable offline mock mode
```

> [!IMPORTANT]
> **Authentication Setup:** Ensure that your local environment has active Application Default Credentials (ADC) so the MCP server can authenticate with Google Cloud. Run the following command in your terminal:
> ```bash
> gcloud auth application-default login
> ```
> Your user account must have sufficient IAM permissions in the target GCP project to read and write Vertex AI Discovery Engine resources.

---

## 🗺️ Product Roadmap

We are actively hardening PocketRAG for production-grade workloads and team environments. The following items from our **Phase 2+ Production-Hardening & Performance** backlog are currently under active development:

* 🛡️ **MCP Tool Path Sandboxing (Security):** Enforcing strict path validation in `upload_file_source` to restrict uploads to files located strictly within the active project workspace, preventing arbitrary system file read exploits via prompt injection.
* ⚡ **FastMCP Lifespan Connection Pooling (Performance):** Restructuring the server to use FastMCP's lifespan context manager. This will share a single persistent `NotebookLMClient` and `httpx.AsyncClient` across all tool calls, cutting latency by 300–400ms per query.
* 🌀 **Non-Blocking Async Operations (Loop Safety):** Wrapping synchronous OAuth token refreshes and large file reads (up to 50MB) in `asyncio.to_thread` to offload them to a background thread pool, preventing event loop blocking.
* 🗂️ **Grounding Context Cache (Performance):** Implementing a short-lived (60-second TTL) in-memory cache of notebook sources in the client to eliminate duplicate GET notebook requests, cutting Q&A latency in half.
* 🛠️ **Tool Expansion & Deeper Integration:** Exposing `add_web_source` and `add_gcs_source` as native tools in the MCP server, and expanding test coverage with a comprehensive integration suite (`test_server_tools.py`).
