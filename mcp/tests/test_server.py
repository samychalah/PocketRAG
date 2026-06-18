import pytest
from pocketrag.config import Config
from pocketrag.client import NotebookLMClient
from pocketrag.exceptions import NotebookNotFoundError


@pytest.mark.asyncio
async def test_mock_flow():
    # Force mock mode and fast polling/timeouts for testing
    cfg = Config(
        project_number="0",
        location="us",
        api_version="v1",
        mock_mode=True,
        poll_initial_seconds=0.1,
        poll_max_seconds=0.2,
        poll_timeout_seconds=2,
        retry_max_attempts=1,
    )
    async with NotebookLMClient(config=cfg) as client:
        assert client.cfg.mock_mode is True
        
        # 1. Create
        nb = await client.notebooks.create("Test Notebook")
        assert nb["title"] == "Test Notebook"
        nid = nb["notebookId"]
        assert nid is not None
        
        # 2. Get
        got = await client.notebooks.get(nid)
        assert got["title"] == "Test Notebook"
        
        # 3. Add Source
        source = await client.sources.add_text(nid, "source1", "This is mock content")
        assert len(source["sources"]) == 1
        
        # 4. Ask
        ans = await client.chat.ask(nid, "What is this?")
        assert "[MOCK]" in ans["answer"]
        
        # 5. List
        lst = await client.notebooks.list()
        assert len(lst["notebooks"]) >= 1
        
        # 6. Delete
        await client.notebooks.delete(nid)
        
        # 7. Verify deletion
        with pytest.raises(NotebookNotFoundError):
            await client.notebooks.get(nid)
