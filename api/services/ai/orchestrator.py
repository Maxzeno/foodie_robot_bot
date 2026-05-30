import json
from typing import Dict, List
from openai import OpenAI
from django.conf import settings

from api.models.user import User
from api.models.message import Message, RoleChoices
from api.services.ai.tool_definitions import get_tool_definitions
from api.services.ai import tool_handlers


class FoodBotAIHandler:
    def __init__(self, user: User, sender_message_id: str = None, reply_message_id: str = None, model: str = "gpt-5-nano"):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model 
        self.user = user

        # Register available tools/functions
        self.tools = get_tool_definitions()
        self.tool_functions = self._register_tool_functions()
        
        self.reply_message = Message.objects.filter(message_id=reply_message_id, role=RoleChoices.BOT).first()
        self.sender_message = Message.objects.filter(message_id=sender_message_id, role=RoleChoices.USER).first()
    
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
            "like_or_hate_meal": tool_handlers.like_or_hate_meal,
            "place_order": tool_handlers.place_order,
            "get_order_status": tool_handlers.get_order_status,
            "get_order_history": tool_handlers.get_order_history,
            "search_meals": tool_handlers.search_meals,
            "get_meal_details": tool_handlers.get_meal_details,
            "get_user_profile": tool_handlers.get_user_profile,
            "update_average_budget": tool_handlers.update_average_budget,
            "get_user_meal_preferences": tool_handlers.get_user_meal_preferences,
            "get_payment_status": tool_handlers.get_payment_status,
            "contact_support": tool_handlers.contact_support,
            "review_last_ordered_meal": tool_handlers.review_last_ordered_meal
        }

    def get_conversation_history(self) -> List[Dict]:
        messages = [
            {
                "role": "system",
                "content": f"""
WhatsApp bot. Ask 1 question at a time. Period: {self.user.get_time_period()}. 
For unknown requests, say you can't help. Be concise.
"""
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
            # Get recent messages from database (last 10 messages for context)
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

        # LLM API call
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=self.tools,
            tool_choice="auto"
        )

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
    