"""
Web Search Tool for CS DB Chat.

Uses SerpAPI (https://serpapi.com) for real-time web search.
Requires SERPAPI_KEY environment variable.

As a fallback, uses DuckDuckGo Instant Answer API (no key required)
for basic searches when no SerpAPI key is configured.
"""

import os
import json
import logging
from typing import Type

import httpx
from pydantic import BaseModel, Field

from vanna.core.tool import Tool, ToolContext, ToolResult
from vanna.components import (
    UiComponent,
    NotificationComponent,
    ComponentType,
    SimpleTextComponent,
)

logger = logging.getLogger("WebSearchTool")


class WebSearchArgs(BaseModel):
    query: str = Field(description="The search query to look up on the internet")
    num_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of search results to return (1-10)",
    )


class WebSearchTool(Tool[WebSearchArgs]):
    """
    Real-time web search tool.

    Uses SerpAPI when SERPAPI_KEY is set, otherwise falls back to
    DuckDuckGo Instant Answer API for basic lookups.
    """

    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the internet for real-time information, current events, news, "
            "prices, or any information that may not be in the database. "
            "Use this when the user asks about something that requires up-to-date "
            "or general knowledge beyond the database."
        )

    def get_args_schema(self) -> Type[WebSearchArgs]:
        return WebSearchArgs

    async def _search_serpapi(self, query: str, num_results: int) -> dict:
        """Search using SerpAPI."""
        params = {
            "q": query,
            "api_key": self.serpapi_key,
            "num": num_results,
            "hl": "en",
            "gl": "us",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://serpapi.com/search", params=params
            )
            response.raise_for_status()
            return response.json()

    async def _search_duckduckgo(self, query: str, num_results: int) -> dict:
        """Fallback: DuckDuckGo Instant Answer API."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
            )
            response.raise_for_status()
            return response.json()

    def _format_serpapi_results(self, data: dict, num_results: int) -> str:
        """Format SerpAPI results into readable text."""
        lines = []

        # Answer box (quick answer)
        if "answer_box" in data:
            box = data["answer_box"]
            answer = box.get("answer") or box.get("snippet", "")
            if answer:
                lines.append(f"**Quick Answer:** {answer}\n")

        # Organic results
        organic = data.get("organic_results", [])[:num_results]
        if organic:
            lines.append("**Search Results:**")
            for i, result in enumerate(organic, 1):
                title = result.get("title", "No title")
                snippet = result.get("snippet", "No description")
                link = result.get("link", "")
                lines.append(f"{i}. **{title}**")
                lines.append(f"   {snippet}")
                if link:
                    lines.append(f"   Source: {link}")
                lines.append("")

        return "\n".join(lines) if lines else "No results found."

    def _format_duckduckgo_results(self, data: dict) -> str:
        """Format DuckDuckGo results into readable text."""
        lines = []

        abstract = data.get("AbstractText", "")
        source = data.get("AbstractSource", "")
        abstract_url = data.get("AbstractURL", "")

        if abstract:
            lines.append(f"**Summary ({source}):** {abstract}")
            if abstract_url:
                lines.append(f"Source: {abstract_url}")
            lines.append("")

        # Related topics
        related = data.get("RelatedTopics", [])[:5]
        if related:
            lines.append("**Related Information:**")
            for item in related:
                if isinstance(item, dict) and "Text" in item:
                    lines.append(f"- {item['Text']}")

        if not lines:
            answer = data.get("Answer", "")
            if answer:
                lines.append(f"**Answer:** {answer}")
            else:
                lines.append(
                    "No direct answer found. The query may require a more specific search engine."
                )

        return "\n".join(lines)

    async def execute(self, context: ToolContext, args: WebSearchArgs) -> ToolResult:
        """Execute web search and return results."""
        try:
            logger.info(f"[WebSearch] Searching for: {args.query}")

            if self.serpapi_key:
                data = await self._search_serpapi(args.query, args.num_results)
                result_text = self._format_serpapi_results(data, args.num_results)
                source_label = "SerpAPI"
            else:
                data = await self._search_duckduckgo(args.query, args.num_results)
                result_text = self._format_duckduckgo_results(data)
                source_label = "DuckDuckGo"

            logger.info(f"[WebSearch] Results retrieved from {source_label}")

            full_result = (
                f"Web search results for: **{args.query}**\n\n"
                f"{result_text}\n\n"
                f"_Source: {source_label} — Retrieved in real-time_"
            )

            return ToolResult(
                success=True,
                result_for_llm=full_result,
                ui_component=UiComponent(
                    rich_component=NotificationComponent(
                        type=ComponentType.NOTIFICATION,
                        level="info",
                        message=f"🌐 Web search completed for: {args.query}",
                    ),
                    simple_component=SimpleTextComponent(text=full_result),
                ),
                metadata={
                    "query": args.query,
                    "source": source_label,
                    "num_results": args.num_results,
                },
            )

        except httpx.TimeoutException:
            error = "Web search timed out. Please try again."
            return ToolResult(
                success=False,
                result_for_llm=error,
                ui_component=UiComponent(
                    rich_component=NotificationComponent(
                        type=ComponentType.NOTIFICATION,
                        level="warning",
                        message=error,
                    ),
                    simple_component=SimpleTextComponent(text=error),
                ),
                error=error,
            )

        except Exception as e:
            error = f"Web search failed: {str(e)}"
            logger.error(f"[WebSearch] Error: {e}")
            return ToolResult(
                success=False,
                result_for_llm=error,
                ui_component=UiComponent(
                    rich_component=NotificationComponent(
                        type=ComponentType.NOTIFICATION,
                        level="error",
                        message=error,
                    ),
                    simple_component=SimpleTextComponent(text=error),
                ),
                error=error,
            )
