"""
AI Orchestrator - Main coordinator for AI-powered natural language understanding.
Handles OpenAI API calls, tool execution, and cost optimization.
"""
import json
import logging
import time
from typing import Dict, Any, Optional, List
from openai import OpenAI
from django.conf import settings

from api.services.ai.context_manager import ContextManager
from api.services.ai.tools import ToolRegistry
from api.services.ai.tool_handlers import ToolHandler
from api.services.ai.prompts import INTENT_CLASSIFICATION_PROMPT
from api.services.ai.resilience import (
    with_circuit_breaker, with_retry, handle_ai_errors,
    openai_circuit_breaker, ai_rate_limiter,
    CircuitBreakerOpenError, RateLimitExceededError
)

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Main orchestrator for AI interactions.

    Handles:
    - OpenAI API calls with cost optimization
    - Tool/function calling
    - Intent classification
    - Error handling and fallbacks
    """

    # Configuration
    DEFAULT_MODEL = "gpt-5-nano"
    MAX_RESPONSE_TOKENS = 150
    MAX_TOOL_CALL_TOKENS = 500
    TEMPERATURE = 1

    def __init__(self, user, model: Optional[str] = None):
        """
        Initialize orchestrator for a user.

        Args:
            user: Django User instance
            model: OpenAI model to use (defaults to gpt-5-nano)
        """
        self.user = user
        self.model = model or self.DEFAULT_MODEL
        self.context_manager = ContextManager(user)
        self.tool_handler = ToolHandler(user)
        self.client = OpenAI(api_key=settings.OPENAI_API)

        # Cost tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0

    @handle_ai_errors
    def process_message(
        self,
        user_message: str,
        enable_tools: bool = True
    ) -> Dict[str, Any]:
        """
        Process a user message with AI.

        Args:
            user_message: The user's message text
            enable_tools: Whether to enable function/tool calling

        Returns:
            Dict containing:
                - response: AI's response text
                - tool_calls: List of tool calls made (if any)
                - tokens_used: Token usage info
                - success: Whether processing succeeded
        """
        # Check rate limit
        user_key = str(self.user.id)
        if not ai_rate_limiter.is_allowed(user_key):
            raise RateLimitExceededError(f"Rate limit exceeded for user {user_key}")

        start_time = time.time()

        try:
            # Build context
            messages = self.context_manager.build_messages_for_ai(
                current_user_message=user_message,
                include_tools=enable_tools
            )

            # Log context size
            context_tokens = self.context_manager.get_total_context_tokens(messages)
            logger.info(f"Processing message with ~{context_tokens} context tokens")

            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.MAX_RESPONSE_TOKENS,
                "temperature": self.TEMPERATURE
            }

            # Add tools if enabled
            if enable_tools:
                api_params["tools"] = ToolRegistry.get_all_tools()
                api_params["tool_choice"] = "auto"
                api_params["max_tokens"] = self.MAX_TOOL_CALL_TOKENS

            # Make API call with circuit breaker and retry
            response = self._make_api_call_with_resilience(api_params)

            # Track token usage
            usage = response.usage
            self.total_prompt_tokens += usage.prompt_tokens
            self.total_completion_tokens += usage.completion_tokens

            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"API call complete. Tokens: {usage.prompt_tokens} prompt, "
                f"{usage.completion_tokens} completion, {usage.total_tokens} total. "
                f"Time: {response_time_ms}ms"
            )

            # Process response
            message = response.choices[0].message
            result = {
                "success": True,
                "response": message.content or "",
                "tool_calls": [],
                "tokens_used": {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens
                }
            }

            # Handle tool calls if present
            if message.tool_calls:
                tool_results = self._execute_tools(message.tool_calls)
                result["tool_calls"] = tool_results

                # If tools were called, get final response
                if tool_results:
                    final_response = self._get_final_response_after_tools(
                        messages, message, tool_results
                    )
                    result["response"] = final_response["response"]
                    result["tokens_used"]["total_tokens"] += final_response["tokens_used"]
                    response_time_ms += final_response.get("response_time_ms", 0)

            # Log usage to database
            self._log_usage(
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                tool_calls_count=len(result["tool_calls"]),
                success=True,
                response_time_ms=response_time_ms
            )

            return result

        except (CircuitBreakerOpenError, RateLimitExceededError):
            # These are handled by @handle_ai_errors decorator
            raise
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)

            # Log failed usage
            self._log_usage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                tool_calls_count=0,
                success=False,
                error_message=str(e),
                response_time_ms=int((time.time() - start_time) * 1000)
            )

            return {
                "success": False,
                "error": str(e),
                "response": "I'm having trouble processing your request. Please try again.",
                "tool_calls": [],
                "tokens_used": {}
            }

    def classify_intent(self, user_message: str) -> str:
        """
        Classify user intent using AI.

        Args:
            user_message: The user's message

        Returns:
            Intent string (e.g., 'order_meal', 'view_recommendations', etc.)
        """
        try:
            # Use a simple, fast classification call
            messages = [
                {"role": "system", "content": INTENT_CLASSIFICATION_PROMPT},
                {"role": "user", "content": user_message}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=10,  # Very small - just need intent name
                temperature=1  # Lower temp for more deterministic classification
            )

            intent = response.choices[0].message.content.strip().lower()
            logger.info(f"Classified intent: {intent}")

            return intent

        except Exception as e:
            logger.error(f"Error classifying intent: {e}")
            return "unclear"

    def _execute_tools(self, tool_calls) -> List[Dict[str, Any]]:
        """
        Execute tool calls from AI.

        Args:
            tool_calls: List of tool calls from OpenAI response

        Returns:
            List of tool execution results
        """
        results = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            logger.info(f"Executing tool: {function_name} with args: {function_args}")

            try:
                # Execute the tool
                result = self._call_tool(function_name, function_args)

                results.append({
                    "tool_call_id": tool_call.id,
                    "function_name": function_name,
                    "arguments": function_args,
                    "result": result
                })

            except Exception as e:
                logger.error(f"Error executing tool {function_name}: {e}", exc_info=True)
                results.append({
                    "tool_call_id": tool_call.id,
                    "function_name": function_name,
                    "arguments": function_args,
                    "result": {
                        "success": False,
                        "error": str(e)
                    }
                })

        return results

    def _call_tool(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route tool call to appropriate handler method.

        Args:
            function_name: Name of the tool/function
            arguments: Arguments for the function

        Returns:
            Result from the tool handler
        """
        # Map function names to handler methods
        tool_map = {
            "get_daily_recommendations": self.tool_handler.get_daily_recommendations,
            "get_user_profile": self.tool_handler.get_user_profile,
            "create_order": self.tool_handler.create_order,
            "update_preferences": self.tool_handler.update_preferences,
            "get_order_status": self.tool_handler.get_order_status,
            "request_delivery_location": self.tool_handler.request_delivery_location,
            "add_delivery_address": self.tool_handler.add_delivery_address,  # Deprecated but kept for compatibility
            "get_previous_orders": self.tool_handler.get_previous_orders,
            "record_meal_feedback": self.tool_handler.record_meal_feedback,
            # Onboarding tools
            "request_user_location": self.tool_handler.request_user_location,
            "set_user_fitness_goal": self.tool_handler.set_user_fitness_goal,
            "set_user_health_conditions": self.tool_handler.set_user_health_conditions,
            "set_user_allergies": self.tool_handler.set_user_allergies,
            "set_user_preferred_cuisines": self.tool_handler.set_user_preferred_cuisines,
            "set_user_budget": self.tool_handler.set_user_budget,
            "check_onboarding_status": self.tool_handler.check_onboarding_status
        }

        handler = tool_map.get(function_name)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown tool: {function_name}"
            }

        return handler(**arguments)

    def _get_final_response_after_tools(
        self,
        original_messages: List[Dict],
        assistant_message,
        tool_results: List[Dict]
    ) -> Dict[str, Any]:
        """
        Get final AI response after tool execution.

        Args:
            original_messages: Original message context
            assistant_message: The assistant's message with tool calls
            tool_results: Results from tool execution

        Returns:
            Dict with final response and token usage
        """
        try:
            # Build messages for second API call
            messages = original_messages.copy()

            # Add assistant's message with tool calls
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })

            # Add tool results
            for tool_result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_result["tool_call_id"],
                    "content": json.dumps(tool_result["result"])
                })

            # Get final response
            final_start = time.time()
            api_params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": self.MAX_RESPONSE_TOKENS,
                "temperature": self.TEMPERATURE
            }
            response = self._make_api_call_with_resilience(api_params)

            usage = response.usage
            self.total_prompt_tokens += usage.prompt_tokens
            self.total_completion_tokens += usage.completion_tokens

            return {
                "response": response.choices[0].message.content,
                "tokens_used": usage.total_tokens,
                "response_time_ms": int((time.time() - final_start) * 1000)
            }

        except Exception as e:
            logger.error(f"Error getting final response: {e}", exc_info=True)
            # Return a generic message based on tool results
            if tool_results and tool_results[0]["result"].get("success"):
                return {
                    "response": "Done! Your request has been processed.",
                    "tokens_used": 0
                }
            return {
                "response": "I encountered an issue. Please try again.",
                "tokens_used": 0
            }

    @with_circuit_breaker(openai_circuit_breaker)
    @with_retry(max_attempts=3, backoff_factor=2.0)
    def _make_api_call_with_resilience(self, api_params: Dict) -> Any:
        """
        Make OpenAI API call with circuit breaker and retry logic.

        Args:
            api_params: Parameters for API call

        Returns:
            API response
        """
        return self.client.chat.completions.create(**api_params)

    def _log_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        tool_calls_count: int = 0,
        success: bool = True,
        error_message: Optional[str] = None,
        response_time_ms: Optional[int] = None
    ):
        """
        Log AI usage to database.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens
            tool_calls_count: Number of tool calls
            success: Whether the call succeeded
            error_message: Error message if failed
            response_time_ms: Response time in milliseconds
        """
        try:
            from api.models import AIUsage

            AIUsage.log_usage(
                user=self.user,
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                tool_calls_count=tool_calls_count,
                success=success,
                error_message=error_message,
                response_time_ms=response_time_ms
            )
        except Exception as e:
            # Don't let logging errors break the main flow
            logger.error(f"Error logging AI usage: {e}")

    def get_token_usage_summary(self) -> Dict[str, int]:
        """Get summary of token usage for this session"""
        return {
            "prompt_tokens": self.total_prompt_tokens,
            "completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens
        }
