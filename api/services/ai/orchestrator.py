import json
from typing import Dict, List
from openai import OpenAI
from django.conf import settings

from api.models.user import User
from api.models.message import Message, RoleChoices
from api.services.ai.tool_definitions import get_tool_definitions
from api.services.ai import tool_handlers


class FoodBotAIHandler:
    def __init__(self, user: User, model: str = "gpt-5-nano"):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model 
        self.user = user

        # Register available tools/functions
        self.tools = get_tool_definitions()
        self.tool_functions = self._register_tool_functions()
    
    def _register_tool_functions(self) -> Dict:
        return {
            "save_fitness_goal": tool_handlers.save_fitness_goal,
            "save_health_conditions": tool_handlers.save_health_conditions,
            "save_allergies": tool_handlers.save_allergies,
            "save_cuisine_preferences": tool_handlers.save_cuisine_preferences,
            "save_delivery_location": tool_handlers.save_delivery_location,
            "generate_meal_recommendations": tool_handlers.generate_meal_recommendations,
            "get_nutritional_info": tool_handlers.get_nutritional_info,
            "request_delivery_location": tool_handlers.request_delivery_location,
        }

    def fetch_system_prompt(self):
        # This method can be used to update the system prompt dynamically if needed
        return {
                "role": "system",
                "content": f"""You are a WhatsApp bot.

Never ask for more than one information at a time. but you can example: successfully saved the user's allergies, now ask for their cuisine preferences. 
but you should not: What is your fitness goals, also tell me your preferred cuisines.

Period of day: {self.user.get_time_period()}

{tool_handlers.check_onboarding_status(self.user)}

Be friendly, concise (this is WhatsApp), and helpful. Ask clarifying questions when needed or if additional info is needed for a tool call.
"""
            }

    def get_conversation_history(self) -> List[Dict]:
        messages = [
            self.fetch_system_prompt()
        ]

        # Get recent messages from database (last 10 messages for context)
        db_messages = Message.objects.filter(user=self.user).order_by('-created_at')[:5]
        db_messages = reversed(db_messages)  # Oldest first
        for msg in db_messages:
            if msg.role == RoleChoices.USER:
                messages.append({
                    "role": "user",
                    "content": msg.content or ""
                })
            elif msg.role == RoleChoices.BOT:
                messages.append({
                    "role": "assistant",
                    "content": msg.content or ""
                })
        print("Conversation history:", messages)
        return messages
    
    def process_message(self) -> str:
        tool_calls_made = 0
        # Get conversation  (Including the current user message)
        messages = self.get_conversation_history()

        # Initial API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

        response_message = response.choices[0].message
        messages.append(response_message)

        # Handle tool calls (loop until no more tool calls)
        while response_message.tool_calls and tool_calls_made < 5:
            tool_calls_made += 1
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
                    function_response = {
                        "success": False,
                        "message": f"Error: {str(e)}"
                    }

                # Add function response to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(function_response)
                })

            # Get new response with function results
            messages[0] = self.fetch_system_prompt()

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            messages.append(response_message)

        return response_message.content
    
    