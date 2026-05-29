"""
Context manager for optimizing token usage in AI conversations.
"""
from typing import List, Dict, Optional
from api.models import Message, RoleChoices
from .prompts import SYSTEM_PROMPT, get_user_context_prompt


class ContextManager:
    """
    Manages conversation context to minimize token usage.

    Strategies:
    1. Sliding window: Keep only last N messages
    2. User context: Load once, reuse
    3. Summarization: Older messages can be summarized (future)
    """

    MAX_MESSAGES = 5  # Maximum messages to include in context
    MAX_CONTEXT_TOKENS = 2000  # Approximate max tokens for context

    def __init__(self, user):
        self.user = user
        self._user_context = None

    def get_system_prompt(self) -> str:
        """Get cached system prompt"""
        return SYSTEM_PROMPT

    def get_user_context(self) -> str:
        """Get user context (cached within instance)"""
        if self._user_context is None:
            time_period = self.user.get_time_period()
            self._user_context = get_user_context_prompt(self.user, time_period)
        return self._user_context

    def get_conversation_history(
        self,
        max_messages: Optional[int] = None,
        include_current_intent: bool = True
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation history in OpenAI message format.

        Args:
            max_messages: Override default max messages
            include_current_intent: Whether to include intent context

        Returns:
            List of message dicts with 'role' and 'content'
        """
        max_msgs = max_messages or self.MAX_MESSAGES

        # Get recent messages (both user and bot)
        recent_messages = Message.objects.filter(
            user=self.user
        ).order_by('-created_at')[:max_msgs]

        # Reverse to chronological order
        recent_messages = list(reversed(recent_messages))

        conversation = []
        for msg in recent_messages:
            role = "assistant" if msg.role == RoleChoices.BOT else "user"

            # Build content
            content = msg.content or ""

            # Add intent context for bot messages if requested
            if include_current_intent and msg.role == RoleChoices.BOT and msg.current_intent:
                content = f"[Intent: {msg.current_intent}] {content}"

            conversation.append({
                "role": role,
                "content": content
            })

        return conversation

    def build_messages_for_ai(
        self,
        current_user_message: str,
        include_tools: bool = True
    ) -> List[Dict[str, str]]:
        """
        Build complete message array for OpenAI API.

        Args:
            current_user_message: The current message from user
            include_tools: Whether this is a tool-calling context

        Returns:
            List of messages ready for OpenAI API
        """
        messages = []

        # System prompt (cacheable)
        system_content = self.get_system_prompt()

        # Add user context to system prompt
        system_content += "\n\n" + self.get_user_context()

        messages.append({
            "role": "system",
            "content": system_content
        })

        # Add conversation history (recent only)
        history = self.get_conversation_history(
            max_messages=self.MAX_MESSAGES - 1  # Leave room for current message
        )
        messages.extend(history)

        # Add current user message
        messages.append({
            "role": "user",
            "content": current_user_message
        })

        return messages

    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation (4 chars ≈ 1 token for English).
        This is approximate; actual tokenization may vary.
        """
        return len(text) // 4

    def get_total_context_tokens(self, messages: List[Dict[str, str]]) -> int:
        """Estimate total tokens in message context"""
        total = 0
        for msg in messages:
            total += self.estimate_tokens(msg.get("content", ""))
        return total
