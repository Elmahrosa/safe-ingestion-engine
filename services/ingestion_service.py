from collectors.http_connector import HTTPConnector
from core.logging import logger
from core.pii import scrub_text
from core.policy import PolicyEngine


class IngestionService:
    def __init__(self, connector: HTTPConnector, policy_engine: PolicyEngine):
        self.connector = connector
        self.policy = policy_engine

    async def ingest(self, url: str) -> str:
        decision = self.policy.evaluate(url)
        if not decision["allowed"]:
            raise PermissionError(decision["reason"])

        result = await self.connector.fetch(url)
        cleaned = scrub_text(result.content)
        logger.info("ingestion.completed", url=url, status_code=result.status_code)
        return cleaned
