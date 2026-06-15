# pyrefly: ignore [missing-import]
import pytest
import uuid
# pyrefly: ignore [missing-import]
from httpx import AsyncClient, ASGITransport
# pyrefly: ignore [missing-import]
from sqlalchemy import select
from backend.app.main import app
from backend.app.db.session import async_session
from backend.app.db.models import User, Thread, CostMetric
from backend.app.api.research import close_pool

@pytest.mark.asyncio
async def test_analytics_unauthorized():
    """Verify that requesting the analytics endpoint without a valid token returns 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/research/analytics")
        assert response.status_code == 401

@pytest.mark.asyncio
async def test_analytics_empty_data():
    """Verify that a newly registered user with no threads returns empty summary metrics."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # 1. Register and login test user
        test_email = f"user_empty_{uuid.uuid4()}@example.com"
        await ac.post("/api/auth/signup", json={"email": test_email, "password": "password"})
        login_res = await ac.post("/api/auth/login", json={"email": test_email, "password": "password"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        
        # 2. Get analytics
        response = await ac.get("/api/research/analytics")
        assert response.status_code == 200
        data = response.json()
        
        assert "summary" in data
        assert data["summary"]["total_runs"] == 0
        assert data["summary"]["total_cost_usd"] == 0.0
        assert data["summary"]["total_prompt_tokens"] == 0
        assert data["summary"]["total_completion_tokens"] == 0
        assert data["summary"]["average_latency_seconds"] == 0.0
        assert "details" in data
        assert len(data["details"]) == 0

@pytest.mark.asyncio
async def test_analytics_isolation_and_aggregation():
    """Verify that calculations correctly aggregate the current user's runs, and isolate them from others."""
    async with async_session() as session:
        # Create User A (our test target)
        user_a = User(email=f"usera_{uuid.uuid4()}@example.com", password_hash="hash")
        session.add(user_a)
        await session.flush()
        
        # Create User B (isolation check)
        user_b = User(email=f"userb_{uuid.uuid4()}@example.com", password_hash="hash")
        session.add(user_b)
        await session.flush()
        
        # Threads for User A
        thread_a1 = Thread(user_id=user_a.id, name="User A Thread 1", tickers=["AAPL"], status="completed")
        thread_a2 = Thread(user_id=user_a.id, name="User A Thread 2", tickers=["MSFT"], status="completed")
        session.add(thread_a1)
        session.add(thread_a2)
        await session.flush()
        
        # Thread for User B
        thread_b = Thread(user_id=user_b.id, name="User B Thread", tickers=["GOOG"], status="completed")
        session.add(thread_b)
        await session.flush()
        
        # Cost metrics for User A
        cm_a1 = CostMetric(
            thread_id=thread_a1.thread_id,
            prompt_tokens=1000,
            completion_tokens=500,
            estimated_cost_usd=0.00375,
            latency_seconds=5.0
        )
        cm_a2 = CostMetric(
            thread_id=thread_a2.thread_id,
            prompt_tokens=2000,
            completion_tokens=1000,
            estimated_cost_usd=0.0075,
            latency_seconds=10.0
        )
        session.add(cm_a1)
        session.add(cm_a2)
        
        # Cost metric for User B (should be hidden from User A)
        cm_b = CostMetric(
            thread_id=thread_b.thread_id,
            prompt_tokens=9999,
            completion_tokens=9999,
            estimated_cost_usd=9.99,
            latency_seconds=99.9
        )
        session.add(cm_b)
        await session.commit()
        
        user_a_id = user_a.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Authenticate as User A
        # Since we bypass standard registration helper in test db setup to link cost metrics manually, 
        # we can just login using signup route to get a real token.
        test_email = f"usera_auth_{uuid.uuid4()}@example.com"
        await ac.post("/api/auth/signup", json={"email": test_email, "password": "password"})
        login_res = await ac.post("/api/auth/login", json={"email": test_email, "password": "password"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        
        # Wait, the logged in user is `test_email` (which has a newly generated UUID). 
        # But we inserted metrics under `user_a.id`. Let's update `test_email`'s user id in the database 
        # to match `user_a.id` so that our API token decodes to the correct owner!
        async with async_session() as session:
            db_user_res = await session.execute(select(User).where(User.email == test_email))
            db_user = db_user_res.scalar_one()
            user_to_delete_id = db_user.id
            
            # Change email and password_hash of user_a to match test credentials
            # This updates the existing record with the target ID so it decodes successfully
            await session.delete(db_user)
            await session.commit()
            
            # Now update user_a to have the target credentials by querying it in the active session
            db_user_a_res = await session.execute(select(User).where(User.id == user_a_id))
            db_user_a = db_user_a_res.scalar_one()
            
            from backend.app.api.auth import hash_password
            db_user_a.email = test_email
            db_user_a.password_hash = hash_password("password")
            await session.commit()
            
        # Re-login to get the updated token
        login_res = await ac.post("/api/auth/login", json={"email": test_email, "password": "password"})
        assert login_res.status_code == 200, f"Login failed with status {login_res.status_code}: {login_res.text}"
        token = login_res.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"

        # Fetch analytics
        response = await ac.get("/api/research/analytics")
        assert response.status_code == 200
        data = response.json()
        
        # Verify aggregates (1000 + 2000 = 3000 prompt; 500 + 1000 = 1500 completion; cost = 0.01125)
        # Latency = (5.0 + 10.0)/2 = 7.5
        assert data["summary"]["total_runs"] == 2
        assert pytest.approx(data["summary"]["total_cost_usd"], rel=1e-5) == 0.01125
        assert data["summary"]["total_prompt_tokens"] == 3000
        assert data["summary"]["total_completion_tokens"] == 1500
        assert pytest.approx(data["summary"]["average_latency_seconds"], rel=1e-5) == 7.5
        
        # Verify details list (should have 2 entries)
        assert len(data["details"]) == 2
        details = data["details"]
        
        # Confirm they map to User A's thread names
        thread_names = {d["thread_name"] for d in details}
        assert thread_names == {"User A Thread 1", "User A Thread 2"}
        
        # Confirm user B's thread cost metric is NOT returned
        assert "User B Thread" not in thread_names
        for d in details:
            assert d["estimated_cost_usd"] != 9.99

    await close_pool()
