# Meal Recommendation System

## Overview

This is an optimized, embedding-based meal recommendation system that provides highly personalized meal suggestions while reducing costs by 95%+ compared to LLM-based approaches.

## Key Features

### Cost Optimization
- **95%+ cost reduction** compared to LLM-based recommendations
- Uses OpenAI's `text-embedding-3-small` model ($0.00002 per 1K tokens)
- Embeddings are cached in the database and reused
- No LLM call required per recommendation

### Personalization
The system considers multiple factors to recommend meals users will love:

1. **User Preferences**: Liked and hated meals (strong signals)
2. **Fitness Goals**: Weight loss, muscle gain, or maintenance
3. **Cuisine Preferences**: Preferred cuisine types
4. **Budget**: Recommends meals within user's budget range
5. **Nutritional Needs**: Optimizes for protein (muscle gain) or calories (weight loss)
6. **Health Constraints**: Excludes meals with restricted health conditions and allergies
7. **Time-of-Day**: Recommends appropriate meals for morning, afternoon, evening
8. **Variety**: Avoids meals recommended in the last 2 days
9. **Diversity**: Ensures variety in cuisines and meal types within recommendations

### Conversion Optimization
The scoring system is designed to maximize conversion:
- **+30 points** for liked meals (strong positive signal)
- **+20 points** for fitness goal match
- **+15 points** for cuisine preference match
- **+10 points** for optimal budget fit (80-100% of budget)
- **+5-10 points** for nutritional value alignment
- **-25 points** for meals recommended in last 2 days (variety)
- **+0-3 points** random exploration bonus

## Usage

### Basic Usage

```python
from api.services.recommendation.meal_recommendation import MealRecommendationService

service = MealRecommendationService()

# Get recommendations for a user
recommendations = service.get_recommendations(
    user=user,
    num_recommendations_per_period=2
)

# Returns:
# {
#     "morning": [meal_id1, meal_id2],
#     "afternoon": [meal_id3, meal_id4],
#     "evening": [meal_id5, meal_id6]
# }
```

### Exclude Specific Meals

```python
# Exclude certain meals (e.g., already shown)
recommendations = service.get_recommendations(
    user=user,
    num_recommendations_per_period=2,
    exclude_meal_ids=[123, 456]
)
```

### Generate Embeddings for Meals

Before using the system, generate embeddings for your meals:

```bash
# Generate embeddings for all meals without embeddings
python manage.py generate_meal_embeddings

# Force regenerate embeddings for all meals
python manage.py generate_meal_embeddings --force

# Process specific city only
python manage.py generate_meal_embeddings --city "Lagos"

# Control batch size
python manage.py generate_meal_embeddings --batch-size 100
```

### Run Database Migration

```bash
python manage.py migrate api
```

## Architecture

### Components

1. **EmbeddingRecommendationService** (`embedding_recommendation.py`)
   - Core recommendation engine
   - Handles embedding generation
   - Implements scoring algorithm
   - Manages diversity and recency logic

2. **MealRecommendationService** (`meal_recommendation.py`)
   - Main interface for recommendations
   - `get_recommendations()` - **RECOMMENDED**: Uses embedding-based approach
   - `get_recommendations_by_llm()` - Legacy LLM-based (expensive)
   - `get_recommendations_by_algo()` - Simple algorithm-based (basic)

3. **Management Command** (`generate_meal_embeddings.py`)
   - CLI tool to generate/regenerate embeddings
   - Supports batch processing
   - Handles errors gracefully

### Embedding Generation

Meals are represented as embeddings based on:
- Meal name and description
- Cuisine type
- Fitness goals
- Nutritional profile (calories, protein, carbs, fats)
- Time-of-day appropriateness

The embedding is a 1536-dimensional vector that captures the semantic meaning of the meal.

### Scoring Algorithm

The scoring system evaluates each meal based on:

```python
score = base_score
+ 30 (if meal is liked by user)
+ 20 (if fitness goal matches)
+ 15 (if cuisine preference matches)
+ 10 (if price is 80-100% of budget)
+ 5-10 (nutritional value alignment)
- 25 (if meal recommended in last 2 days)
+ 0-3 (random exploration factor)
```

### Diversity Logic

To ensure variety:
1. Filters meals by time-of-day appropriateness
2. Tracks selected cuisines and meal keywords
3. Avoids recommending too many similar meals
4. Penalizes meals recommended in last 2 days

## Cost Analysis

### Old LLM-Based System
- **Cost per request**: ~$0.003-0.005
- **100K users/day**: $300-500/day = $9,000-15,000/month
- **Token usage**: ~1000-1500 tokens per request

### New Embedding-Based System
- **One-time embedding cost**: $0.00002 per meal
- **1000 meals**: ~$0.02
- **Cost per request**: ~$0 (uses cached embeddings)
- **100K users/day**: <$1/day = <$30/month
- **Savings**: 95-99% cost reduction

## Migration Guide

### From LLM-Based to Embedding-Based

1. **Run migration**:
   ```bash
   python manage.py migrate api
   ```

2. **Generate embeddings**:
   ```bash
   python manage.py generate_meal_embeddings
   ```

3. **Update your code**:
   ```python
   # Old (expensive)
   recommendations = service.get_recommendations_by_llm(user)

   # New (optimized)
   recommendations = service.get_recommendations(user)
   ```

4. **Monitor performance**:
   - Check recommendation quality
   - Monitor conversion rates
   - Track cost savings

## Performance Considerations

- **Embedding generation**: ~50-100 meals per second
- **Recommendation generation**: <100ms per user
- **Database**: Uses JSONField for embedding storage (efficient in PostgreSQL)
- **Batch processing**: Process embeddings in batches for efficiency

## Future Enhancements

Potential improvements:
1. **Collaborative filtering**: Learn from other users' preferences
2. **Temporal patterns**: Learn user's meal timing preferences
3. **Weather/season consideration**: Recommend based on weather
4. **Social proof**: Factor in popularity and ratings
5. **A/B testing framework**: Test different scoring weights
6. **Real-time learning**: Update user preferences based on orders

## Troubleshooting

### Meals not being recommended
- Ensure embeddings are generated: `python manage.py generate_meal_embeddings`
- Check meal availability and city match
- Verify user has city set
- Check if meals are excluded by health/allergy filters

### Low conversion rates
- Review scoring weights in `_score_meal()` method
- Analyze user feedback (liked/hated meals)
- Check if budget constraints are too restrictive
- Verify nutritional data is present for meals

### High costs
- Ensure embeddings are cached (check `embedding` field in database)
- Verify you're using `get_recommendations()` not `get_recommendations_by_llm()`
- Monitor OpenAI API usage dashboard

## Support

For questions or issues:
1. Check this documentation
2. Review the code comments
3. Test with sample data
4. Monitor logs for errors
