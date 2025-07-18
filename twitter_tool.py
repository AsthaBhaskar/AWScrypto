import os
import requests
from strands import tool
from dotenv import load_dotenv
from textblob import TextBlob
import time

# Load environment variables
load_dotenv()

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

# Helper: Clean tweet text for sentiment analysis
import re
def clean_tweet(text):
    text = re.sub(r"http\S+", "", text)  # Remove URLs
    text = re.sub(r"@[A-Za-z0-9_]+", "", text)  # Remove mentions
    text = re.sub(r"#[A-Za-z0-9_]+", "", text)  # Remove hashtags
    text = re.sub(r"[^A-Za-z0-9\s]", "", text)  # Remove special chars
    return text.strip()

@tool
def get_social_sentiment(symbol: str, coin_name: str = None, max_tweets: int = 50) -> dict:
    """
    Fetch and analyze social sentiment from Twitter for a given cryptocurrency.
    Returns detailed sentiment percentages and cites impactful tweets.
    Args:
        symbol: The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol')
        coin_name: The full name of the coin (optional, for better search)
        max_tweets: Number of tweets to analyze (default 50)
    Returns:
        Dict with sentiment breakdown and cited tweets
    """
    twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not twitter_bearer_token:
        return {"status": "error", "result": f"Twitter API key missing. Please add TWITTER_BEARER_TOKEN to your .env file."}

    # Build crypto-specific search query
    # Prioritize $ symbol format and add crypto context to avoid false positives
    symbol_upper = symbol.upper()
    
    # Primary search: $SYMBOL format (most specific for crypto)
    primary_query = f'${symbol_upper}'
    
    # Secondary search: $SYMBOL with crypto context keywords
    crypto_keywords = ["crypto", "token", "coin", "blockchain", "defi", "nft", "trading", "price", "market", "bull", "bear", "pump", "dump", "moon", "hodl", "buy", "sell"]
    context_queries = []
    
    for keyword in crypto_keywords[:5]:  # Use top 5 most relevant keywords
        context_queries.append(f'${symbol_upper} {keyword}')
    
    # Combine queries with OR, prioritizing the $ symbol format
    query_parts = [primary_query] + context_queries
    
    # If coin_name is provided and different from symbol, add it with crypto context
    if coin_name and coin_name.lower() != symbol.lower():
        coin_context_queries = [f'"{coin_name}" {kw}' for kw in crypto_keywords[:3]]
        query_parts.extend(coin_context_queries)
    
    query = " OR ".join([f'"{q}"' for q in query_parts]) + " lang:en -is:retweet"

    headers = {"Authorization": f"Bearer {twitter_bearer_token}"}
    params = {
        "query": query,
        "max_results": 100 if max_tweets > 50 else max_tweets,
        "tweet.fields": "public_metrics,created_at,author_id,text"
    }

    tweets = []
    next_token = None
    fetched = 0
    while fetched < max_tweets:
        if next_token:
            params["next_token"] = next_token
        resp = requests.get(TWITTER_SEARCH_URL, headers=headers, params=params)
        if resp.status_code != 200:
            break
        data = resp.json()
        batch = data.get("data", [])
        tweets.extend(batch)
        fetched += len(batch)
        next_token = data.get("meta", {}).get("next_token")
        if not next_token or len(tweets) >= max_tweets:
            break
        time.sleep(1)  # Rate limit safety
    tweets = tweets[:max_tweets]

    # Additional filtering: Only keep tweets that actually mention the crypto token
    filtered_tweets = []
    for tweet in tweets:
        text = tweet["text"].lower()
        # Must contain $SYMBOL or be clearly about the crypto
        if (f"${symbol_upper.lower()}" in text or 
            f"${symbol.lower()}" in text or
            (coin_name and coin_name.lower() in text and any(kw in text for kw in crypto_keywords))):
            filtered_tweets.append(tweet)
    
    tweets = filtered_tweets[:max_tweets]

    # Sentiment analysis
    pos, neg, neu = 0, 0, 0
    cited_tweets = []
    tweet_sentiments = []
    for tweet in tweets:
        text = clean_tweet(tweet["text"])
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.15:
            pos += 1
            sentiment = "positive"
        elif polarity < -0.15:
            neg += 1
            sentiment = "negative"
        else:
            neu += 1
            sentiment = "neutral"
        tweet_sentiments.append({
            "id": tweet["id"],
            "text": tweet["text"],
            "sentiment": sentiment,
            "polarity": polarity,
            "engagement": tweet.get("public_metrics", {}).get("like_count", 0) + tweet.get("public_metrics", {}).get("retweet_count", 0)
        })

    total = max(pos + neg + neu, 1)
    pos_pct = round(100 * pos / total, 1)
    neg_pct = round(100 * neg / total, 1)
    neu_pct = round(100 * neu / total, 1)

    # Cite most impactful tweets (top 2 by engagement in each sentiment)
    impactful = {"positive": [], "negative": [], "neutral": []}
    for sentiment in impactful.keys():
        filtered = [t for t in tweet_sentiments if t["sentiment"] == sentiment]
        top = sorted(filtered, key=lambda t: t["engagement"], reverse=True)[:2]
        impactful[sentiment] = top

    # Format citations
    cited = []
    for sentiment, tweets in impactful.items():
        for t in tweets:
            cited.append({
                "sentiment": sentiment,
                "engagement": t["engagement"],
                "url": f"https://twitter.com/i/web/status/{t['id']}"
            })

    summary = (
        f"Social Sentiment for {symbol_upper}\n"
        f"Positive: {pos_pct}%  |  Negative: {neg_pct}%  |  Neutral: {neu_pct}%\n"
        f"(Based on {total} recent tweets)\n"
    )
    
    return {
        "status": "success",
        "summary": summary,
        "positive_pct": pos_pct,
        "negative_pct": neg_pct,
        "neutral_pct": neu_pct,
        "total_tweets": total,
        "cited_tweets": cited,
        "raw_tweets": tweet_sentiments
    }

@tool
def get_trending_hashtags(symbol: str) -> str:
    """
    Get trending hashtags related to a specific cryptocurrency.
    Args:
        symbol: The cryptocurrency symbol
    Returns:
        Trending hashtags and their sentiment
    """
    return "(Not implemented)"

@tool
def get_influencer_mentions(symbol: str) -> str:
    """
    Get mentions of a cryptocurrency by influential accounts.
    Args:
        symbol: The cryptocurrency symbol
    Returns:
        Influencer mention data
    """
    return "(Not implemented)" 