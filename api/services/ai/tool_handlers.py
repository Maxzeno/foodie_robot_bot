"""
Tool handler implementations for AI function calling.
These handlers execute the actual business logic for each tool.
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from api.models import (
    User, Meal, Order, Recommendation, MealPreference,
    FitnessGoal, HealthCondition, Allergy, PreferredCuisine,
    Currency, Message, CurrentIntentChoices, City
)
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
import logging

logger = logging.getLogger(__name__)


class ToolHandler:
    """Handles execution of AI tools"""

    def __init__(self, user: User):
        self.user = user

    def get_daily_recommendations(self, time_period: str = "all") -> Dict[str, Any]:
        """
        Get user's meal recommendations for today.

        Args:
            time_period: 'morning', 'afternoon', 'evening', or 'all'

        Returns:
            Dict with success status and recommendations list
        """
        try:
            # Get today's recommendations
            today = timezone.now().date()
            query = Recommendation.objects.filter(
                user=self.user,
                recommended_at__date=today
            ).select_related('meal', 'meal__restaurant')

            # Filter by time period if not 'all'
            if time_period != "all":
                query = query.filter(time_period=time_period)

            recommendations = query.order_by('time_period', 'created_at')

            # Format results
            result_list = []
            for rec in recommendations:
                result_list.append({
                    "id": rec.id,
                    "meal_id": rec.meal.id,
                    "meal_name": rec.meal.name,
                    "description": rec.meal.description,
                    "price": float(rec.meal.price),
                    "restaurant": rec.meal.restaurant.name,
                    "time_period": rec.time_period,
                    "calories": rec.meal.calories,
                    "protein": float(rec.meal.protein) if rec.meal.protein else None
                })

            return {
                "success": True,
                "recommendations": result_list,
                "message": f"Found {len(result_list)} recommendations" if result_list else "No recommendations available for today"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "recommendations": []
            }

    def get_user_profile(self) -> Dict[str, Any]:
        """
        Get user's profile information.

        Returns:
            Dict with success status and profile data
        """
        try:
            profile = {
                "phone": self.user.phone,
                "city": self.user.city.name if self.user.city else None,
                "fitness_goal": self.user.fitness_goals.name if self.user.fitness_goals else None,
                "budget": float(self.user.average_meal_budget) if self.user.average_meal_budget else None,
                "allergies": [a.name for a in self.user.allergies.all()],
                "health_conditions": [h.name for h in self.user.health_conditions.all()],
                "preferred_cuisines": [c.name for c in self.user.preferred_cuisine.all()]
            }

            return {
                "success": True,
                "profile": profile
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def create_order(
        self,
        meal_id: int,
        quantity: int,
        delivery_address: str
    ) -> Dict[str, Any]:
        """
        Create a new order for a meal.

        Args:
            meal_id: ID of the meal to order
            quantity: Number of plates
            delivery_address: Delivery address

        Returns:
            Dict with success status and order details
        """
        try:
            # Validate quantity
            if quantity < 1:
                return {
                    "success": False,
                    "error": "Quantity must be at least 1"
                }

            # Get meal
            try:
                meal = Meal.objects.select_related('restaurant').get(id=meal_id)
            except Meal.DoesNotExist:
                return {
                    "success": False,
                    "error": f"Meal with ID {meal_id} not found"
                }

            # Calculate total price
            meal_price = meal.price
            delivery_fee = Decimal("0.00")  # TODO: Calculate based on distance
            total_price = (meal_price * quantity) + delivery_fee

            # Get or create default currency (USD)
            currency, _ = Currency.objects.get_or_create(
                code="NGN",
                defaults={"name": "Nigerian Naira", "symbol": "₦"}
            )

            # Create order (note: current schema supports one meal per order)
            order = Order.objects.create(
                user=self.user,
                meal=meal,
                quantity=quantity,
                total_price=total_price,
                meal_price=meal_price,
                delivery_fee=delivery_fee,
                amount_paid=Decimal("0.00"),
                paid=False,
                dropoff_street_address=delivery_address,
                currency=currency,
                status='pending'
            )

            return {
                "success": True,
                "order_id": order.id,
                "meal_name": meal.name,
                "quantity": quantity,
                "total_price": float(total_price),
                "delivery_address": delivery_address,
                "message": f"Order created successfully! Order ID: {order.id}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def update_preferences(
        self,
        fitness_goal: Optional[str] = None,
        budget: Optional[float] = None,
        allergies_to_add: Optional[List[str]] = None,
        allergies_to_remove: Optional[List[str]] = None,
        cuisines_to_add: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update user preferences.

        Args:
            fitness_goal: New fitness goal name
            budget: New budget amount
            allergies_to_add: List of allergy names to add
            allergies_to_remove: List of allergy names to remove
            cuisines_to_add: List of cuisine names to add

        Returns:
            Dict with success status
        """
        try:
            updated_fields = []

            # Update fitness goal
            if fitness_goal:
                goal, _ = FitnessGoal.objects.get_or_create(
                    name=fitness_goal,
                    defaults={"description": f"{fitness_goal} goal"}
                )
                self.user.fitness_goals = goal
                updated_fields.append("fitness_goal")

            # Update budget
            if budget is not None:
                self.user.average_meal_budget = Decimal(str(budget))
                updated_fields.append("budget")

            # Add allergies
            if allergies_to_add:
                for allergy_name in allergies_to_add:
                    allergy, _ = Allergy.objects.get_or_create(
                        name=allergy_name,
                        defaults={"description": f"{allergy_name} allergy"}
                    )
                    self.user.allergies.add(allergy)
                updated_fields.append("allergies_added")

            # Remove allergies
            if allergies_to_remove:
                for allergy_name in allergies_to_remove:
                    try:
                        allergy = Allergy.objects.get(name=allergy_name)
                        self.user.allergies.remove(allergy)
                    except Allergy.DoesNotExist:
                        pass
                updated_fields.append("allergies_removed")

            # Add cuisines
            if cuisines_to_add:
                for cuisine_name in cuisines_to_add:
                    cuisine, _ = PreferredCuisine.objects.get_or_create(
                        name=cuisine_name,
                        defaults={"description": f"{cuisine_name} cuisine"}
                    )
                    self.user.preferred_cuisine.add(cuisine)
                updated_fields.append("cuisines_added")

            self.user.save()

            return {
                "success": True,
                "updated_fields": updated_fields,
                "message": f"Successfully updated: {', '.join(updated_fields)}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_order_status(self, order_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get order status.

        Args:
            order_id: Specific order ID, or None for recent orders

        Returns:
            Dict with success status and order(s) data
        """
        try:
            if order_id:
                # Get specific order
                try:
                    order = Order.objects.select_related('user', 'meal').get(
                        id=order_id,
                        user=self.user
                    )
                    return {
                        "success": True,
                        "order": self._format_order(order)
                    }
                except Order.DoesNotExist:
                    return {
                        "success": False,
                        "error": f"Order {order_id} not found"
                    }
            else:
                # Get recent orders
                orders = Order.objects.filter(user=self.user).select_related('meal').order_by('-created_at')[:5]
                return {
                    "success": True,
                    "orders": [self._format_order(order) for order in orders],
                    "message": f"Found {len(orders)} recent orders"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def request_delivery_location(
        self,
        meal_id: int,
        reason: str = "to complete your order"
    ) -> Dict[str, Any]:
        """
        Request user to share their delivery location via WhatsApp map picker.
        This sends an interactive button that opens WhatsApp's location selector.

        Args:
            meal_id: The meal being ordered
            reason: Why we need the location

        Returns:
            Dict with success status and instructions for user
        """
        try:
            # Validate meal exists
            try:
                meal = Meal.objects.get(id=meal_id)
            except Meal.DoesNotExist:
                return {
                    "success": False,
                    "error": f"Meal with ID {meal_id} not found"
                }

            # Send WhatsApp location request button
            text = f"Great! To proceed with your order for {meal.name}, please share your delivery location.\n\nTap the 'Send Location' button below to select your address on the map."

            Message.bot_message_request_location(
                text,
                self.user,
                current_intent=CurrentIntentChoices.ADD_NEW_ORDER_DELIVERY_ADDRESS,
                metadata={"meal_id": meal_id}
            )

            return {
                "success": True,
                "message": "Location request sent. User will receive a 'Send Location' button.",
                "instruction_to_ai": "Tell the user to tap the 'Send Location' button that was just sent to select their delivery address on the map."
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def add_delivery_address(
        self,
        address: str,
        label: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        DEPRECATED: Use request_delivery_location instead.
        This method is kept for backward compatibility but should not be used.
        """
        return {
            "success": False,
            "error": "This method is deprecated. Use request_delivery_location to get addresses via WhatsApp map picker instead.",
            "instruction_to_ai": "Use the request_delivery_location tool instead of asking for typed addresses."
        }

    def get_previous_orders(self, limit: int = 5) -> Dict[str, Any]:
        """
        Get user's order history.

        Args:
            limit: Maximum number of orders to return

        Returns:
            Dict with success status and orders list
        """
        try:
            orders = Order.objects.filter(user=self.user).order_by('-created_at')[:limit]

            return {
                "success": True,
                "orders": [self._format_order(order) for order in orders],
                "count": len(orders)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def record_meal_feedback(self, meal_id: int, liked: bool) -> Dict[str, Any]:
        """
        Record user feedback on a meal.

        Args:
            meal_id: ID of the meal
            liked: True if user likes it, False otherwise

        Returns:
            Dict with success status
        """
        try:
            # Get meal
            try:
                meal = Meal.objects.get(id=meal_id)
            except Meal.DoesNotExist:
                return {
                    "success": False,
                    "error": f"Meal with ID {meal_id} not found"
                }

            # Create or update preference
            preference, created = MealPreference.objects.update_or_create(
                user=self.user,
                meal=meal,
                defaults={"liked": liked}
            )

            action = "recorded" if created else "updated"
            sentiment = "like" if liked else "dislike"

            return {
                "success": True,
                "meal_name": meal.name,
                "liked": liked,
                "message": f"Your {sentiment} for {meal.name} has been {action}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def _format_order(self, order: Order) -> Dict[str, Any]:
        """Helper method to format order data"""
        return {
            "id": order.id,
            "status": order.status,
            "meal_name": order.meal.name,
            "quantity": order.quantity,
            "meal_price": float(order.meal_price),
            "delivery_fee": float(order.delivery_fee),
            "total_price": float(order.total_price),
            "delivery_address": order.dropoff_street_address,
            "paid": order.paid,
            "created_at": order.created_at.isoformat()
        }

    # ===== ONBOARDING TOOLS =====

    def request_user_location(self, reason: str = "to determine your city and currency") -> Dict[str, Any]:
        """
        Request user to share their location via WhatsApp location picker.
        This is the FIRST step in onboarding.

        Args:
            reason: Why we need the location

        Returns:
            Dict with success status and instructions
        """
        try:
            text = f"Welcome! To get started, please share your location {reason}.\n\nTap the 'Send Location' button below."

            Message.bot_message_request_location(
                text,
                self.user,
                current_intent=CurrentIntentChoices.FIRST_LOCATION,
                metadata={"onboarding": True}
            )

            return {
                "success": True,
                "message": "Location request sent to user",
                "instruction_to_ai": "Tell the user to tap the 'Send Location' button to share their location."
            }

        except Exception as e:
            logger.error(f"Error requesting location: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def set_user_fitness_goal(self, fitness_goal: str) -> Dict[str, Any]:
        """
        Set user's fitness goal from natural language input.

        Args:
            fitness_goal: Fitness goal name

        Returns:
            Dict with success status
        """
        try:
            # Normalize fitness goal name
            normalized_goal = fitness_goal.title().strip()

            # Get or create fitness goal
            goal, created = FitnessGoal.objects.get_or_create(
                name=normalized_goal,
                defaults={"description": f"{normalized_goal} fitness goal"}
            )

            self.user.fitness_goals = goal
            self.user.save()

            action = "set" if created else "updated"
            return {
                "success": True,
                "fitness_goal": goal.name,
                "message": f"Fitness goal {action} to '{goal.name}'"
            }

        except Exception as e:
            logger.error(f"Error setting fitness goal: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def set_user_health_conditions(self, health_conditions: List[str]) -> Dict[str, Any]:
        """
        Set user's health conditions from natural language input.

        Args:
            health_conditions: List of health condition names

        Returns:
            Dict with success status
        """
        try:
            # Clear existing health conditions
            self.user.health_conditions.clear()

            if not health_conditions:
                return {
                    "success": True,
                    "health_conditions": [],
                    "message": "Health conditions cleared (none specified)"
                }

            # Add each health condition
            added_conditions = []
            for condition_name in health_conditions:
                normalized_name = condition_name.title().strip()
                condition, _ = HealthCondition.objects.get_or_create(
                    name=normalized_name,
                    defaults={"description": f"{normalized_name} health condition"}
                )
                self.user.health_conditions.add(condition)
                added_conditions.append(condition.name)

            return {
                "success": True,
                "health_conditions": added_conditions,
                "message": f"Health conditions set: {', '.join(added_conditions)}"
            }

        except Exception as e:
            logger.error(f"Error setting health conditions: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def set_user_allergies(self, allergies: List[str]) -> Dict[str, Any]:
        """
        Set user's food allergies from natural language input.

        Args:
            allergies: List of allergy names

        Returns:
            Dict with success status
        """
        try:
            # Clear existing allergies
            self.user.allergies.clear()

            if not allergies:
                return {
                    "success": True,
                    "allergies": [],
                    "message": "Allergies cleared (none specified)"
                }

            # Add each allergy
            added_allergies = []
            for allergy_name in allergies:
                normalized_name = allergy_name.title().strip()
                allergy, _ = Allergy.objects.get_or_create(
                    name=normalized_name,
                    defaults={"description": f"{normalized_name} allergy"}
                )
                self.user.allergies.add(allergy)
                added_allergies.append(allergy.name)

            return {
                "success": True,
                "allergies": added_allergies,
                "message": f"Allergies set: {', '.join(added_allergies)}"
            }

        except Exception as e:
            logger.error(f"Error setting allergies: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def set_user_preferred_cuisines(self, cuisines: List[str]) -> Dict[str, Any]:
        """
        Set user's preferred cuisines from natural language input.

        Args:
            cuisines: List of cuisine names

        Returns:
            Dict with success status
        """
        try:
            # Clear existing cuisines
            self.user.preferred_cuisine.clear()

            if not cuisines:
                return {
                    "success": True,
                    "cuisines": [],
                    "message": "Preferred cuisines cleared (none specified)"
                }

            # Add each cuisine
            added_cuisines = []
            for cuisine_name in cuisines:
                normalized_name = cuisine_name.title().strip()
                cuisine, _ = PreferredCuisine.objects.get_or_create(
                    name=normalized_name,
                    defaults={"description": f"{normalized_name} cuisine"}
                )
                self.user.preferred_cuisine.add(cuisine)
                added_cuisines.append(cuisine.name)

            return {
                "success": True,
                "cuisines": added_cuisines,
                "message": f"Preferred cuisines set: {', '.join(added_cuisines)}"
            }

        except Exception as e:
            logger.error(f"Error setting cuisines: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def set_user_budget(self, budget: float) -> Dict[str, Any]:
        """
        Set user's average meal budget.
        Should be called AFTER location is set.

        Args:
            budget: Budget amount in local currency

        Returns:
            Dict with success status
        """
        try:
            if budget < 0:
                return {
                    "success": False,
                    "error": "Budget must be a positive number"
                }

            self.user.average_meal_budget = Decimal(str(budget))
            self.user.save()

            currency_symbol = "₦"  # Default to Naira
            if self.user.city and hasattr(self.user.city, 'currency'):
                currency_symbol = self.user.city.currency.symbol

            return {
                "success": True,
                "budget": float(budget),
                "currency": currency_symbol,
                "message": f"Average meal budget set to {currency_symbol}{budget}"
            }

        except Exception as e:
            logger.error(f"Error setting budget: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def check_onboarding_status(self) -> Dict[str, Any]:
        """
        Check which onboarding steps the user has completed.

        Returns:
            Dict with completion status of each onboarding step
        """
        try:
            has_location = self.user.city is not None
            has_budget = self.user.average_meal_budget is not None
            has_fitness_goal = self.user.fitness_goals is not None
            has_health_conditions = self.user.health_conditions.exists()
            has_allergies = self.user.allergies.exists()
            has_cuisines = self.user.preferred_cuisine.exists()

            # Consider onboarding complete if user has location and at least fitness goal
            is_complete = has_location and has_fitness_goal

            missing_steps = []
            if not has_location:
                missing_steps.append("location")
            if not has_fitness_goal:
                missing_steps.append("fitness_goal")
            if not has_budget:
                missing_steps.append("budget")
            if not has_allergies:
                missing_steps.append("allergies")
            if not has_health_conditions:
                missing_steps.append("health_conditions")
            if not has_cuisines:
                missing_steps.append("preferred_cuisines")

            return {
                "success": True,
                "onboarding_complete": is_complete,
                "steps": {
                    "location": has_location,
                    "budget": has_budget,
                    "fitness_goal": has_fitness_goal,
                    "health_conditions": has_health_conditions,
                    "allergies": has_allergies,
                    "preferred_cuisines": has_cuisines
                },
                "missing_steps": missing_steps,
                "city": self.user.city.name if self.user.city else None,
                "message": "Onboarding complete" if is_complete else f"Missing: {', '.join(missing_steps)}"
            }

        except Exception as e:
            logger.error(f"Error checking onboarding status: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
