from datetime import datetime, timezone

CATALYST_KEYWORDS = {
    "earnings": ["earnings", "quarter", "guidance", "revenue", "eps"],
    "mna": ["acquisition", "merger", "takeover", "buyout"],
    "legal": ["lawsuit", "investigation", "settlement", "probe"],
    "policy": ["regulation", "tariff", "policy", "government", "ban"],
    "contracts": ["contract", "award", "supplier", "deal"],
    "insider": ["insider", "13f", "filing", "stake"],
    "product": ["launch", "approval", "partnership", "product"]
}

def run(news_data=None):
    articles = news_data.get("articles", []) if isinstance(news_data, dict) else []
    catalysts = {k: [] for k in CATALYST_KEYWORDS.keys()}

    for article in articles:
        text = f"{article.get('title','')} {article.get('description','')}".lower()
        for cat, words in CATALYST_KEYWORDS.items():
            if any(w in text for w in words):
                catalysts[cat].append(article)

    return {
        "catalyst_categories": catalysts,
        "catalyst_count": sum(len(v) for v in catalysts.values()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
