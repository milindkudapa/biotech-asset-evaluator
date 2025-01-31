import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ExAiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.ex.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url
        logger.info("Initialized Ex.ai client")

    async def analyze_drug(self, drug_name: str) -> Dict[str, Any]:
        """Analyze a drug using Ex.ai API."""
        logger.info(f"Analyzing drug: {drug_name}")
        
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                logger.debug(f"Making request to Ex.ai API for drug: {drug_name}")
                response = await client.post(
                    f"{self.base_url}/analyze",
                    json={"drug_name": drug_name},
                    headers=headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                logger.info(f"Successfully analyzed drug: {drug_name}")
                logger.debug(f"Analysis result: {result}")
                return result
                
        except httpx.TimeoutException as e:
            logger.error(f"Timeout while analyzing drug {drug_name}: {str(e)}")
            raise
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error while analyzing drug {drug_name}: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while analyzing drug {drug_name}: {str(e)}", exc_info=True)
            raise 