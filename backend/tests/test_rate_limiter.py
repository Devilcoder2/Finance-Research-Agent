# pyrefly: ignore [missing-import]
import pytest
import time
import asyncio
from backend.app.graphs.workers.scraper import TokenBucketLimiter, rate_limited

@pytest.mark.asyncio
async def test_token_bucket_limiter_rate():
    # Setup a limiter that allows 2 requests per second, capacity 2
    limiter = TokenBucketLimiter(rate=2, capacity=2)
    
    # Consume first two immediately
    start_time = time.time()
    await limiter.wait_for_token()
    await limiter.wait_for_token()
    elapsed_initial = time.time() - start_time
    assert elapsed_initial < 0.2  # Should be near instantaneous
    
    # The third request should require a token, which refreshes at 2 tokens/sec
    # Since we consumed 2 tokens, tokens is at 0. Refilling 1 token needs 0.5s.
    await limiter.wait_for_token()
    elapsed_total = time.time() - start_time
    assert elapsed_total >= 0.4  # Should take at least 0.4 seconds to get the third token

@pytest.mark.asyncio
async def test_rate_limited_decorator():
    # Setup a limiter that allows 5 requests per second, capacity 1
    limiter = TokenBucketLimiter(rate=5, capacity=1)
    
    call_count = 0
    
    @rate_limited(limiter)
    async def dummy_api_call():
        nonlocal call_count
        call_count += 1
        return call_count

    # Execute 3 calls
    start_time = time.time()
    res1 = await dummy_api_call()
    res2 = await dummy_api_call()
    res3 = await dummy_api_call()
    elapsed = time.time() - start_time
    
    assert res1 == 1
    assert res2 == 2
    assert res3 == 3
    # Capacity is 1, so the 2nd call waits 0.2s.
    # The 3rd call starts after the 2nd call finishes (0.2s elapsed), refilling the 1 token.
    # So total elapsed time should be at least 0.2s.
    assert elapsed >= 0.18
