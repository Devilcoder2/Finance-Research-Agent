# pyrefly: ignore [missing-import]
import pytest
import uuid
import json
import subprocess
from unittest.mock import patch, MagicMock, AsyncMock
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.api.research import get_git_commit_hash, close_pool

class MockInterrupt:
    def __init__(self, id_val, value):
        self.id = id_val
        self.value = value

class MockTask:
    def __init__(self, interrupts):
        self.interrupts = interrupts

class MockStateInfo:
    def __init__(self, tasks, next_step, values):
        self.tasks = tasks
        self.next = next_step
        self.values = values

# 1. Test Git commit hash helper
def test_get_git_commit_hash_success():
    with patch("subprocess.check_output") as mock_run:
        mock_run.return_value = b"abc123f\n"
        git_hash = get_git_commit_hash()
        assert git_hash == "abc123f"
        mock_run.assert_called_once_with(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL)

def test_get_git_commit_hash_failure():
    with patch("subprocess.check_output") as mock_run:
        mock_run.side_effect = subprocess.SubprocessError("git not installed")
        git_hash = get_git_commit_hash()
        assert git_hash == "unknown"

def test_get_git_commit_hash_no_mock():
    # Verify execution without mocks does not crash and returns a string
    git_hash = get_git_commit_hash()
    assert isinstance(git_hash, str)
    assert len(git_hash) > 0

# 2. Test SSE streaming observability tagging
@pytest.mark.asyncio
async def test_api_tracing_config_stream():
    # Setup mock compiled application
    mock_compiled_app = MagicMock()
    
    # Mock astream_events as an async generator
    async def mock_astream_events(state, config, version):
        yield {"event": "on_chain_start", "metadata": {"langgraph_node": "mock_node"}}
        
    mock_compiled_app.astream_events = mock_astream_events
    
    # Mock aget_state
    mock_state_values = {
        "ticker_briefs": {
            "AAPL": {
                "executive_summary": "AAPL looks solid.",
                "business_overview": "Tech company",
                "financial_analysis": "Profitable",
                "risk_factors": "Competition",
                "verdict": "Buy"
            }
        },
        "ticker_scraped_data": {},
        "ticker_quant_data": {},
        "revision_count": 1
    }
    mock_state_info = MockStateInfo(tasks=[], next_step=None, values=mock_state_values)
    mock_compiled_app.aget_state = AsyncMock(return_value=mock_state_info)
    
    # Patch the compiler to return our mock application
    with patch("backend.app.api.research.portfolio_builder.compile", return_value=mock_compiled_app) as mock_compile:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Authenticate
            test_email = f"test_{uuid.uuid4()}@example.com"
            await ac.post("/api/auth/signup", json={"email": test_email, "password": "password"})
            login_res = await ac.post("/api/auth/login", json={"email": test_email, "password": "password"})
            assert login_res.status_code == 200
            token = login_res.json()["access_token"]
            ac.headers["Authorization"] = f"Bearer {token}"
            
            # Start research run session
            start_payload = {"tickers": ["AAPL"]}
            response = await ac.post("/api/research/start", json=start_payload)
            assert response.status_code == 201
            thread_id = response.json()["thread_id"]
            
            # Stream research
            captured_configs = []
            
            # We patch the call to astream_events to spy on the config passed
            original_astream_events = mock_compiled_app.astream_events
            async def spy_astream_events(state, config, version):
                captured_configs.append(config)
                async for event in original_astream_events(state, config, version):
                    yield event
                    
            mock_compiled_app.astream_events = spy_astream_events
            
            # Hit the stream endpoint
            async with ac.stream("GET", f"/api/research/stream/{thread_id}") as stream_res:
                assert stream_res.status_code == 200
                # Consume stream
                async for _ in stream_res.aiter_lines():
                    pass
            
            # Assert compilation and calls occurred
            mock_compile.assert_called_once()
            assert len(captured_configs) > 0
            
            # Verify the config contains metadata and tags
            config = captured_configs[0]
            assert "configurable" in config
            assert config["configurable"]["thread_id"] == thread_id
            assert "callbacks" in config
            
            # Check tags
            tags = config.get("tags", [])
            assert f"thread-{thread_id}" in tags
            assert any(tag.startswith("user-") for tag in tags)
            
            # Check metadata
            metadata = config.get("metadata", {})
            assert metadata["thread_id"] == thread_id
            assert "user_id" in metadata
            assert "git_commit_hash" in metadata
            assert isinstance(metadata["git_commit_hash"], str)

    await close_pool()

# 3. Test Resume endpoint observability tagging
@pytest.mark.asyncio
async def test_api_tracing_config_resume():
    mock_compiled_app = MagicMock()
    mock_compiled_app.ainvoke = AsyncMock()
    
    # Mock aget_state to return an interrupt for AAPL
    mock_interrupt = MockInterrupt(id_val="interrupt_1", value={"ticker": "AAPL"})
    mock_task = MockTask(interrupts=[mock_interrupt])
    
    # First aget_state inside resume (gets state to find the interrupt)
    # Second aget_state inside resume (gets state after invoking)
    mock_state_values = {
        "ticker_briefs": {
            "AAPL": {
                "executive_summary": "AAPL looks solid.",
                "business_overview": "Tech company",
                "financial_analysis": "Profitable",
                "risk_factors": "Competition",
                "verdict": "Buy"
            }
        },
        "ticker_scraped_data": {},
        "ticker_quant_data": {},
        "revision_count": 1
    }
    mock_state_info_before = MockStateInfo(tasks=[mock_task], next_step=["node"], values={})
    mock_state_info_after = MockStateInfo(tasks=[], next_step=None, values=mock_state_values)
    
    mock_compiled_app.aget_state = AsyncMock(side_effect=[mock_state_info_before, mock_state_info_after])
    
    with patch("backend.app.api.research.portfolio_builder.compile", return_value=mock_compiled_app) as mock_compile:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Authenticate
            test_email = f"test_{uuid.uuid4()}@example.com"
            await ac.post("/api/auth/signup", json={"email": test_email, "password": "password"})
            login_res = await ac.post("/api/auth/login", json={"email": test_email, "password": "password"})
            assert login_res.status_code == 200
            token = login_res.json()["access_token"]
            ac.headers["Authorization"] = f"Bearer {token}"
            
            # Start research run session
            start_payload = {"tickers": ["AAPL"]}
            response = await ac.post("/api/research/start", json=start_payload)
            assert response.status_code == 201
            thread_id = response.json()["thread_id"]
            
            # Resume research
            resume_payload = {
                "thread_id": thread_id,
                "ticker": "AAPL",
                "action": "approve"
            }
            resume_response = await ac.post("/api/research/resume", json=resume_payload)
            assert resume_response.status_code == 200
            
            mock_compile.assert_called_once()
            
            # Verify that aget_state and ainvoke were called with the correct config
            assert mock_compiled_app.aget_state.call_count == 2
            
            # Inspect configs passed to aget_state and ainvoke
            for call in mock_compiled_app.aget_state.call_args_list:
                config = call[0][0]
                assert config["configurable"]["thread_id"] == thread_id
                assert f"thread-{thread_id}" in config["tags"]
                assert config["metadata"]["thread_id"] == thread_id
                assert "git_commit_hash" in config["metadata"]
                
            ainvoke_call_args = mock_compiled_app.ainvoke.call_args
            assert ainvoke_call_args is not None
            config_ainvoke = ainvoke_call_args[1]["config"]
            assert config_ainvoke["configurable"]["thread_id"] == thread_id
            assert f"thread-{thread_id}" in config_ainvoke["tags"]
            assert config_ainvoke["metadata"]["thread_id"] == thread_id
            assert "git_commit_hash" in config_ainvoke["metadata"]

    await close_pool()
