import json
import math
from typing import List, Dict, Tuple
from openai import OpenAI
from django.conf import settings
from django.core.cache import cache

from api.services.ai.llm_client import get_ai_client


class ToolEmbeddingFilter:
    """
    Filters tools using semantic similarity via embeddings.
    Reduces token costs by pre-selecting most relevant tools before LLM call.
    """

    EMBEDDING_MODEL = settings.AI_EMBEDDING_MODEL
    EMBEDDING_DIMENSIONS = settings.AI_EMBEDDING_DIMENSIONS
    CACHE_KEY_PREFIX = "tool_embedding_"
    CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 7 days

    def __init__(self, openai_client: OpenAI = None):
        self.client = openai_client or get_ai_client()

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text via Alibaba Cloud DashScope."""
        response = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text,
            dimensions=self.EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _create_tool_text(self, tool: Dict) -> str:
        """
        Create a text representation of a tool for embedding.
        Combines name and description for better semantic matching.
        """
        function = tool.get("function", {})
        name = function.get("name", "")
        description = function.get("description", "")

        # Format: "function_name: description"
        return f"{name}: {description}"

    def _get_cached_tool_embedding(self, tool: Dict) -> List[float]:
        """Get tool embedding from cache or generate and cache it."""
        tool_name = tool.get("function", {}).get("name", "")
        cache_key = f"{self.CACHE_KEY_PREFIX}{tool_name}"

        # Try to get from cache
        cached_embedding = cache.get(cache_key)
        if cached_embedding is not None:
            return cached_embedding

        # Generate and cache
        tool_text = self._create_tool_text(tool)
        embedding = self._get_embedding(tool_text)
        cache.set(cache_key, embedding, self.CACHE_TIMEOUT)

        return embedding

    def filter_tools(
        self,
        user_query: str,
        all_tools: List[Dict],
        top_k: int = 5,
        essential_tool_names: List[str] = None
    ) -> List[Dict]:
        """
        Filter tools based on semantic similarity to user query.

        Args:
            user_query: The user's message/query
            all_tools: List of all available tool definitions
            top_k: Number of most relevant tools to return
            essential_tool_names: List of tool names that should always be included

        Returns:
            List of top K most relevant tools plus essential tools
        """
        essential_tool_names = essential_tool_names or []

        # Separate essential tools from others
        essential_tools = []
        other_tools = []

        for tool in all_tools:
            tool_name = tool.get("function", {}).get("name", "")
            if tool_name in essential_tool_names:
                essential_tools.append(tool)
            else:
                other_tools.append(tool)

        # Generate embedding for user query
        query_embedding = self._get_embedding(user_query)

        # Calculate similarity scores for non-essential tools
        tool_scores: List[Tuple[Dict, float]] = []

        for tool in other_tools:
            tool_embedding = self._get_cached_tool_embedding(tool)
            similarity = self._cosine_similarity(query_embedding, tool_embedding)
            tool_scores.append((tool, similarity))

        # Sort by similarity (highest first)
        tool_scores.sort(key=lambda x: x[1], reverse=True)

        # Calculate how many additional tools we need (after essential tools)
        additional_tools_needed = max(0, top_k - len(essential_tools))
        filtered_tools = [tool for tool, score in tool_scores[:additional_tools_needed]]

        # Combine essential tools + filtered tools
        final_tools = essential_tools + filtered_tools

        # Log for debugging
        print(f"Tool filtering results:")
        print(f"  Essential tools: {len(essential_tools)}")
        print(f"  Filtered tools (top {additional_tools_needed}):")
        for tool, score in tool_scores[:additional_tools_needed]:
            tool_name = tool.get("function", {}).get("name", "unknown")
            print(f"    - {tool_name}: {score:.3f}")

        return final_tools

    def precompute_tool_embeddings(self, all_tools: List[Dict]):
        """
        Precompute and cache embeddings for all tools.
        Call this once on startup or when tools change.
        """
        print("Precomputing tool embeddings...")
        for tool in all_tools:
            self._get_cached_tool_embedding(tool)
        print(f"Cached embeddings for {len(all_tools)} tools")
