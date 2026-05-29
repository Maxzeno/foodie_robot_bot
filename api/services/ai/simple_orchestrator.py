"""
Simple AI Orchestrator - minimal prompts, focused on cost efficiency
"""
import json
import logging
from typing import Dict, Any
from openai import OpenAI
from django.conf import settings

from api.services.ai.simple_tools import ONBOARDING_TOOLS
from api.services.ai.simple_handler import SimpleAIHandler
from api.models import AIUsage

logger = logging.getLogger(__name__)


# Minimal system prompt - saves tokens
SYSTEM_PROMPT = """You are a helpful meal recommendation assistant.

**Onboarding flow:**
1. Fitness goal → call save_fitness_goal, then ask about health
2. Health conditions → call save_health_conditions, then ask about allergies
3. Allergies → call save_allergies, then ask about cuisines
4. Cuisines → call save_cuisines, then call request_location
5. Location → (user sends via button, system processes)

**After saving each field:** Acknowledge what was saved and ask the next question.

Example: "✅ Fitness goal set to weight loss. Do you have any health conditions like diabetes or hypertension?"

**After onboarding complete:** Ask if they want to see meal recommendations, then call get_recommendations.

Be friendly and conversational. Parse natural language."""


class SimpleOrchestrator:
    """Minimal AI orchestrator - low token usage"""

    def __init__(self, user):
        self.user = user
        self.handler = SimpleAIHandler(user)
        self.client = OpenAI(api_key=settings.OPENAI_API)
        self.model = "gpt-4o-mini"  # Fast and reliable model

    def process(self, user_message: str) -> Dict[str, Any]:
        """Process user message with AI"""
        try:
            # Build minimal context
            messages = self._build_messages(user_message)

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=ONBOARDING_TOOLS,
                tool_choice="auto",
                max_completion_tokens=150,  # Limit output
                temperature=1
            )

            # Log usage
            usage = response.usage
            AIUsage.log_usage(
                user=self.user,
                model=self.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                success=True
            )

            # Process response
            message = response.choices[0].message

            # Execute tools if called
            if message.tool_calls:
                tool_results = []
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    logger.info(f"Executing tool: {tool_name} with {tool_args}")
                    tool_result = self.handler.execute_tool(tool_name, tool_args)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "result": tool_result
                    })

                # Get AI's final response after tool execution
                final_response = self._get_final_response(messages, message, tool_results)
                return {
                    "response": final_response,
                    "success": True
                }
            else:
                # No tools called, use AI's direct response
                return {
                    "response": message.content or "",
                    "success": True
                }

        except Exception as e:
            logger.error(f"AI error: {e}", exc_info=True)
            AIUsage.log_usage(
                user=self.user,
                model=self.model,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                success=False,
                error_message=str(e)
            )
            return {
                "success": False,
                "response": "Sorry, I'm having trouble. Please try again."
            }

    def _build_messages(self, user_message: str) -> list:
        """Build minimal message context - saves tokens"""
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add user profile context (minimal)
        profile_info = self._get_user_status()
        if profile_info:
            messages.append({"role": "system", "content": f"User status: {profile_info}"})

        # Add current message
        messages.append({"role": "user", "content": user_message})

        return messages

    def _get_user_status(self) -> str:
        """Get minimal user status - saves tokens"""
        missing = self.handler.get_missing_fields()
        if not missing:
            return "Onboarding complete"
        return f"Missing: {', '.join(missing)}"

    def _get_final_response(self, original_messages: list, assistant_message, tool_results: list) -> str:
        """
        Get AI's final response after tool execution.
        This allows AI to acknowledge what was saved and ask the next question.
        """
        try:
            # Build conversation with tool results
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
            for tr in tool_results:
                # Format special responses
                content = json.dumps(tr["result"])

                # For location request, tell AI it was sent
                if tr["name"] == "request_location":
                    content = json.dumps({"success": True, "message": "WhatsApp location button sent to user"})

                # For recommendations, format nicely
                if tr["name"] == "get_recommendations" and tr["result"].get("success"):
                    meals = tr["result"].get("meals", [])
                    if meals:
                        meal_list = "\n".join([f"{i+1}. {m['name']} - {m['price']}" for i, m in enumerate(meals)])
                        content = json.dumps({"success": True, "meals": meal_list})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": content
                })

            # Get final response from AI
            final_response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=150,
                temperature=1
            )

            return final_response.choices[0].message.content or "Thanks!"

        except Exception as e:
            logger.error(f"Error getting final response: {e}", exc_info=True)
            # Fallback based on what was saved
            if any(tr["name"] == "request_location" for tr in tool_results):
                return ""  # Location button already sent
            return "Got it! Let me know when you're ready to continue."
