import logging

import httpx

logger = logging.getLogger("D2M:JINA")
JINA_READER_API = "https://r.jina.ai"


async def jina_reader(url: str, api_token: str | None = None) -> str:
    async with httpx.AsyncClient() as client:
        try:
            if api_token:
                headers = {"Authorization": f"Bearer {api_token}"}
            else:
                headers = {}
            response = await client.post(
                JINA_READER_API,
                headers=headers,
                json={"url": url},
            )
            return response.text
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return ""
