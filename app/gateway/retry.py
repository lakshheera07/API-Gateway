import asyncio
import httpx

async def retry_request(
        url: str,
        max_retries: int = 3,
        base_delay: float = 1.0,
):
    last_exception = None

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
            if response.status_code < 500:
                return response
            raise Exception(f"Server error: {response.status_code}")
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
    raise last_exception