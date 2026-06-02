import json
from typing import Dict, List
from openai import OpenAI
from django.conf import settings

from api.models.user import User
from api.models.message import Message, RoleChoices
from api.services.ai.tool_definitions import get_tool_definitions
from api.services.ai import tool_handlers
from api.services.ai.embedding_filter import ToolEmbeddingFilter


class FoodBotAIHandler:
    def __init__(self, user: User, sender_message_id: str = None, reply_message_id: str = None, model: str = "gpt-5-nano", use_embedding_filter: bool = False, top_k_tools: int = 3): # gpt-5-nano gpt-4.1-nano
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model
        self.user = user
        self.use_embedding_filter = use_embedding_filter
        self.top_k_tools = top_k_tools

        # Register available tools/functions
        self.all_tools = get_tool_definitions()
        self.tool_functions = self._register_tool_functions()

        # Initialize embedding filter
        self.embedding_filter = ToolEmbeddingFilter(self.client)

        # Define essential tools that should always be available (regardless of embedding filter)
        # These are critical tools that provide core functionality or act as fallbacks
        self.essential_tools = [
            "meal_recommendations",  # Core feature
            "place_order",  # Core conversion action
            "contact_support"  # Fallback for any issues
        ]

        self.reply_message = Message.objects.filter(message_id=reply_message_id, role=RoleChoices.BOT).first()
        self.sender_message = Message.objects.filter(message_id=sender_message_id, role=RoleChoices.USER).first()
    
    def _register_tool_functions(self) -> Dict:
        return {
            "meal_recommendations": tool_handlers.meal_recommendations,
            "save_delivery_location": tool_handlers.save_delivery_location,
            "request_delivery_location": tool_handlers.request_delivery_location,
            # TODO: To be removed to reduce token usage
            "get_current_location": tool_handlers.get_current_location,
            
            "place_order": tool_handlers.place_order,
            "review_last_ordered_meal": tool_handlers.review_last_ordered_meal,
            "get_order_status": tool_handlers.get_order_status,
            "get_order_history": tool_handlers.get_order_history,
            
            "get_user_profile": tool_handlers.get_user_profile,
            "like_or_hate_meal": tool_handlers.like_or_hate_meal,
            # TODO: To be removed to reduce token usage
            "get_user_meal_preferences": tool_handlers.get_user_meal_preferences,
            
            "contact_support": tool_handlers.contact_support,
            "show_menu_options": tool_handlers.show_menu_options,
            
            # TODO: To be implemented
            # "request_update_info": tool_handlers.request_update_info,
            # "update_info": tool_handlers.update_info,

            # TODO: Potentially to be replaced with a more modular registration system
            "save_fitness_goal": tool_handlers.save_fitness_goal,
            "save_health_conditions": tool_handlers.save_health_conditions,
            "save_allergies": tool_handlers.save_allergies,
            "save_cuisine_preferences": tool_handlers.save_cuisine_preferences,
            "update_average_budget": tool_handlers.update_average_budget,
            
            # referral and balance tools
            "referral_link": tool_handlers.referral_link,
            "show_balance": tool_handlers.show_balance,
            # "make_withdraw": tool_handlers.make_withdraw,
            
            
            # TODO: potentially to be removed 
            # "search_meals": tool_handlers.search_meals,
            # "get_nutritional_info": tool_handlers.get_nutritional_info,
            "get_meal_details": tool_handlers.get_meal_details,
        }

    def get_conversation_history(self) -> List[Dict]:
        # Static system prompt for prompt caching (OpenAI automatically caches repeated content >1024 tokens)
        messages = [
{
  "role": "system",
  "content": "You are a WhatsApp food bot. Your behavior: ALWAYS call tools to handle user requests - this is your primary responsibility. CRITICAL: Never assume or default values for any parameter (required or optional). Only include parameters that the user explicitly specifies. The ONLY exception to calling tools is when you need to ask for missing required parameters - in this case respond with text asking for those specific parameters only (be very concise), then await user input before calling any tool. If the user's request doesn't match any available tool, call show_menu_options. Never expose internal metadata or implementation details in your responses."
}
        ]
        if self.reply_message and self.sender_message:
            messages.append({
                "role": "user",
                "content": self.reply_message.get_content_meta()
            })

            messages.append({
                "role": "user",
                "content": self.sender_message.get_content_meta()
            })

        else:   
            # Get recent messages from database
            db_messages = Message.objects.filter(user=self.user).order_by('-created_at')[:5]
            db_messages = reversed(db_messages)  # Oldest first
            for msg in db_messages:
                if msg.role == RoleChoices.USER:
                    messages.append({
                        "role": "user",
                        "content": msg.get_content_meta()
                    })
                elif msg.role == RoleChoices.BOT:
                    messages.append({
                        "role": "assistant",
                        "content": msg.get_content_meta()
                    })
            print("Conversation history:", messages)
        return messages
    
    def process_message(self) -> str:
        # Get conversation  (Including the current user message)
        messages = self.get_conversation_history()

        recent_user_messages = [
            msg["content"] for msg in reversed(messages)
        ]

        # Combine recent messages for context-aware filtering
        user_context = " | ".join(reversed(recent_user_messages))

        # Filter tools using embedding similarity if enabled
        if self.use_embedding_filter and user_context:
            tools = self.embedding_filter.filter_tools(
                user_query=user_context,
                all_tools=self.all_tools,
                top_k=self.top_k_tools,
                essential_tool_names=self.essential_tools
            )
            print(f"Using {len(tools)} filtered tools (from {len(self.all_tools)} total)")
        else:
            tools = self.all_tools
            print(f"Using all {len(tools)} tools (filtering disabled)")

        # LLM API call with automatic prompt caching
        # OpenAI automatically caches static prompt prefixes (system prompts, tool definitions)
        # Cache is reused when the same prefix is sent, reducing costs
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            # max_completion_tokens=150,
            reasoning_effort="low" # minimal
        )

        # Log usage including cache hits
        usage = response.usage
        print(f"LLM usage: {usage}")

        response_message = response.choices[0].message
        messages.append(response_message)

        if not response_message.tool_calls:
            return response_message.content

        print("Tool call detected:", response_message.tool_calls)
        # Execute each tool call
        for tool_call in response_message.tool_calls[:5]:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            # All tool handlers need the user object as first arg
            function_args["user"] = self.user

            # Execute the function
            try:
                function_response = self.tool_functions[function_name](**function_args)
                print("Function response:", function_response)
            except Exception as e:
                print(f"Error executing tool {function_name}: {e}")

        return None
    