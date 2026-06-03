from typing import Optional, Dict

from api.models.user import User
from api.models.order import Order, OrderStatus
from api.models.review import Review, SentimentChoices
from api.models.message import Message


def review_last_ordered_meal(
    user: User,
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

        # Get latest completed/delivered order
        order = Order.objects.filter(
            user=user,
            paid=True
        ).order_by('-created_at').first()

        if not order:
            Message.bot_message(
                "You haven't received any orders yet. Once you receive an order, you can review it!",
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
            meal=order.meal
        ).first()

        if existing_review:
            # Update existing review
            existing_review.sentiment = sentiment
            if review_text:
                existing_review.comment = review_text
            existing_review.save()
            action = "updated"
        else:
            # Create new review
            Review.objects.create(
                user=user,
                meal=order.meal,
                sentiment=sentiment,
                comment=review_text or ""
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
