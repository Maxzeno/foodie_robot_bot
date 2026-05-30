import json
import math
from typing import List, Dict, Tuple
from openai import OpenAI
from django.conf import settings
from django.core.cache import cache


class ToolEmbeddingFilter:
    """
    Filters tools using semantic similarity via embeddings.
    Reduces token costs by pre-selecting most relevant tools before LLM call.
    """

    EMBEDDING_MODEL = "text-embedding-3-small"
    CACHE_KEY_PREFIX = "tool_embedding_"
    CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 7 days

    def __init__(self, openai_client: OpenAI = None):
        self.client = openai_client or OpenAI(api_key=settings.OPENAI_API_KEY)

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI API."""
        response = self.client.embeddings.create(
            model=self.EMBEDDING_MODEL,
            input=text
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
        top_k: int = 5
    ) -> List[Dict]:
        """
        Filter tools based on semantic similarity to user query.

        Args:
            user_query: The user's message/query
            all_tools: List of all available tool definitions
            top_k: Number of most relevant tools to return

        Returns:
            List of top K most relevant tools
        """
        # Generate embedding for user query
        query_embedding = self._get_embedding(user_query)

        # Calculate similarity scores for each tool
        tool_scores: List[Tuple[Dict, float]] = []

        for tool in all_tools:
            tool_embedding = self._get_cached_tool_embedding(tool)
            similarity = self._cosine_similarity(query_embedding, tool_embedding)
            tool_scores.append((tool, similarity))

        # Sort by similarity (highest first) and take top K
        tool_scores.sort(key=lambda x: x[1], reverse=True)
        filtered_tools = [tool for tool, score in tool_scores[:top_k]]

        # Log for debugging
        print(f"Tool filtering results (top {top_k}):")
        for tool, score in tool_scores[:top_k]:
            tool_name = tool.get("function", {}).get("name", "unknown")
            print(f"  - {tool_name}: {score:.3f}")

        return filtered_tools

    def precompute_tool_embeddings(self, all_tools: List[Dict]):
        """
        Precompute and cache embeddings for all tools.
        Call this once on startup or when tools change.
        """
        print("Precomputing tool embeddings...")
        for tool in all_tools:
            self._get_cached_tool_embedding(tool)
        print(f"Cached embeddings for {len(all_tools)} tools")
