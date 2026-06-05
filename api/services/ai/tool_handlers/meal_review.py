from typing import Optional

from api.models.user import User
from api.models.order import Order, OrderStatus
from api.models.review import Review
from api.models.message import Message


def review_order(
    user: User,
    order_id: int,
    meal_rating:int,
    sentiment: str,
    review_text: Optional[str] = None,
) -> bool:
    try:
        # Validate sentiment
        valid_sentiments = ['like', 'neutral', 'hate']
        if sentiment not in valid_sentiments:
            Message.bot_message(
                "Please specify if you liked, were neutral about, or hated the meal.",
                user=user
            )
            return False

        if type(meal_rating) != int:
            meal_rating = int(meal_rating)

        if meal_rating < 1 or meal_rating > 5:
            Message.bot_message(
                "Please provide a meal rating between 1 and 5 stars.",
                user=user
            )
            return False

        order = Order.objects.filter(
            pk=order_id,
        ).first()

        if not order:
            Message.bot_message(
                "We conldn't find your order. Please make sure you've placed an order before submitting a review.",
                user=user
            )
            return False
            

        # Check if order is paid (can only review delivered/paid orders)
        if not order.paid:
            Message.bot_message(
                f"You can only review orders that have been delivered. Order #{order.code} hasn't been paid for yet.",
                user=user
            )
            return False
        
        if order.status != OrderStatus.RECEIVED:
            Message.bot_message(
                f"You can only review orders that have been delivered. Order #{order.code}.",
                user=user
            )
            return False

        # Check if user already reviewed this meal from this order
        existing_review = Review.objects.filter(
            user=user,
            order=order
        ).first()

        if existing_review:
            # Update existing review
            existing_review.sentiment = sentiment
            existing_review.meal_rating = meal_rating
            
            if review_text:
                existing_review.comment = review_text
            existing_review.save()
            action = "updated"
        else:
            # Create new review
            Review.objects.create(
                user=user,
                order=order,
                sentiment=sentiment,
                comment=review_text or "",
                meal_rating=meal_rating
            )
            action = "submitted"

        # Format response message
        sentiment_emoji = {
            'like': '❤️',
            'neutral': '😐',
            'hate': '💔'
        }

        sentiment_text = {
            'like': 'loved',
            'neutral': 'were neutral about',
            'hate': 'disliked'
        }

        message = f"""
✅ Review {action} successfully!

You {sentiment_text[sentiment]} {order.meal.name} {sentiment_emoji[sentiment]}
""".strip()

        if review_text:
            message += f'\n\nYour comment: "{review_text}"'

        message += "\n\nThank you for your feedback! We'll use this to improve your recommendations."

        Message.bot_message(message, user=user)

        return True

    except Exception as e:
        print(f"Error submitting review: {e}")
        Message.bot_message(
            "Sorry, something went wrong while submitting your review. Please try again.",
            user=user
        )
        return False
