# 🛠️ PocketRAG Skill: NotebookLM-as-a-RAG for Any LLM

This skill enables your AI assistant to programmatically turn **NotebookLM Enterprise** (via the **Vertex AI Discovery Engine API**) into an instant, managed RAG backend.

## 📖 What it does
By loading this skill, your assistant gains the ability to:
1.  **Check Registry:** Look up active RAG notebooks in the session memory registry.
2.  **Provision Notebooks:** Create new RAG notebooks (Discovery Engine Data Stores) on-demand.
3.  **Ingest Documents:** Ingest raw text or upload local files (like PDFs, scanned documents, and txt files) securely.
4.  **Query Grounded Knowledge:** Run highly accurate, grounded, and cited queries against your documents.
5.  **Resource Cleanup:** Delete notebooks once tasks are finished to keep your GCP environment clean.

## 🚀 How to trigger
To activate this skill during a chat session, simply say:
*   *"Ground my conversation in these files"*
*   *"Upload this document to my RAG"*
*   *"Run a query on my RAG"*
*   *"Create a RAG notebook for me"*
*   Or use the shortcut **`/rag`**
