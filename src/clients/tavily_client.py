import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class TavilyClient:
    def __init__(self, api_key: str, base_url: str = "https://api.tavily.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        logger.info("Initialized Tavily client")

    async def search(self, query: str, search_depth: str = "advanced") -> Dict[str, Any]:
        """Perform a search using Tavily API."""
        logger.info(f"Performing search with query: {query}")
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "query": query,
                    "search_depth": search_depth,
                    "include_answer": True,
                    "include_raw_content": False
                }
                
                logger.debug(f"Making request to Tavily API with payload: {payload}")
                response = await client.post(
                    f"{self.base_url}/search",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                logger.info(f"Successfully completed search for query: {query}")
                logger.debug(f"Search result: {result}")
                return result
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during search for query {query}: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during search for query {query}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during search for query {query}: {str(e)}", exc_info=True)
            raise 