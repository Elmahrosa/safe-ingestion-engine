"""
connectors/base.py
==================
Abstract base class for all ingestion connectors.

To add a new connector (e.g. S3, Notion, Confluence):
1. Subclass BaseConnector
2. Implement fetch() and normalize()
3. Register it in connectors/__init__.py

Example
-------
class S3Connector(BaseConnector):
    source_type = "s3"

    async def fetch(self, url: str, **kwargs) -> bytes:
        ...

    async def normalize(self, raw: bytes) -> dict:
        ...
"""

import abc
from typing import Any


class BaseConnector(abc.ABC):
    """Base class for all Safe Ingestion Engine connectors."""

    #: Override in subclasses — used for routing and logging
    source_type: str = "base"

    @abc.abstractmethod
    async def fetch(self, url: str, **kwargs: Any) -> bytes:
        """
        Fetch raw content from the given URL/reference.

        Parameters
        ----------
        url:
            The resource to fetch.
        **kwargs:
            Connector-specific options (auth tokens, region, etc.)

        Returns
        -------
        bytes
            Raw content bytes.
        """

    @abc.abstractmethod
    async def normalize(self, raw: bytes, **kwargs: Any) -> dict:
        """
        Normalize raw content into a standard ingestion payload.

        Parameters
        ----------
        raw:
            Raw bytes from fetch().
        **kwargs:
            Connector-specific options.

        Returns
        -------
        dict with at minimum:
            {
                "text": str,       # extracted plain text
                "source": str,     # original URL
                "metadata": dict,  # title, author, content_type, etc.
            }
        """

    async def run(self, url: str, **kwargs: Any) -> dict:
        """Convenience method: fetch then normalize."""
        raw = await self.fetch(url, **kwargs)
        return await self.normalize(raw, **kwargs)


class HttpConnector(BaseConnector):
    """
    Default HTTP connector — fetches any public URL via httpx.
    Used for generic web pages when no specialised connector matches.
    """

    source_type = "http"

    async def fetch(self, url: str, **kwargs: Any) -> bytes:
        try:
            import httpx
        except ImportError:
            raise RuntimeError("httpx is required: pip install httpx")

        timeout = kwargs.get("timeout", 30)
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    async def normalize(self, raw: bytes, **kwargs: Any) -> dict:
        # Basic text extraction — replace with BeautifulSoup / trafilatura in prod
        text = raw.decode("utf-8", errors="replace")
        return {
            "text":     text,
            "source":   kwargs.get("url", ""),
            "metadata": {"content_type": "text/html"},
        }
