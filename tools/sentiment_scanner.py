from datetime import datetime, timezone

def run():
    return {
        "news_sentiment": "neutral_placeholder",
        "social_sentiment": "neutral_placeholder",
        "sentiment_score": 0.5,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
