"""
Twitter Tool Module
Integrates with Twitter API v2 to fetch and analyze social sentiment, trending hashtags, and influencer mentions for cryptocurrencies, using TextBlob for sentiment analysis.
"""
import os
import requests
import time
import random
from strands import tool
from dotenv import load_dotenv
from textblob import TextBlob

def retry_api_call(func, max_retries=3, base_delay=1, max_delay=10, backoff_factor=2):
    """
    Purpose:
        Retry utility for API calls with exponential backoff and jitter.
    Args:
        func (callable): Function to retry.
        max_retries (int): Maximum number of retry attempts.
        base_delay (int): Initial delay in seconds.
        max_delay (int): Maximum delay in seconds.
        backoff_factor (int): Multiplier for exponential backoff.
    Returns:
        Any: Result of the function call or None if all retries failed.
    Exceptions:
        Raises the last exception if all retries fail.
    """
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                # Last attempt failed, re-raise the exception
                raise e
            
            # Calculate delay with exponential backoff and jitter
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            jitter = random.uniform(0, 0.1 * delay)  # Add 10% jitter
            total_delay = delay + jitter
            
            print(f"[DEBUG] API call failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
            print(f"[DEBUG] Retrying in {total_delay:.2f} seconds...")
            time.sleep(total_delay)
    
    return None

# Load environment variables
load_dotenv()

"""
Twitter API Integration for Social Sentiment Analysis

Required Environment Variable:
- TWITTER_BEARER_TOKEN: Twitter API v2 Bearer token for authentication

Note: This tool uses Twitter API v2 with Bearer token authentication.
TWITTER_API_KEY and TWITTER_API_SECRET are not used.
"""

TWITTER_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"

# Helper: Clean tweet text for sentiment analysis
import re
def clean_tweet(text):
    """
    Purpose:
        Clean tweet text for sentiment analysis by removing URLs, mentions, hashtags, and special characters.
    Args:
        text (str): The tweet text to clean.
    Returns:
        str: Cleaned tweet text.
    Exceptions:
        None
    """
    text = re.sub(r"http\S+", "", text)  # Remove URLs
    text = re.sub(r"@[A-Za-z0-9_]+", "", text)  # Remove mentions
    text = re.sub(r"#[A-Za-z0-9_]+", "", text)  # Remove hashtags
    text = re.sub(r"[^A-Za-z0-9\s]", "", text)  # Remove special chars
    return text.strip()

@tool
def get_social_sentiment(symbol: str, coin_name: str = None, max_tweets: int = 50) -> dict:
    """
    Purpose:
        Fetch and analyze social sentiment from Twitter for a given cryptocurrency.
    Args:
        symbol (str): The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol').
        coin_name (str, optional): The full name of the coin (for better search).
        max_tweets (int, optional): Number of tweets to analyze (default 50).
    Returns:
        dict: Sentiment breakdown, cited tweets, and raw tweet data.
    Exceptions:
        Returns error dict if API key is missing, request fails, or data is invalid.
    """
    twitter_bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not twitter_bearer_token:
        return {"status": "error", "result": f"Twitter API key missing. Please add TWITTER_BEARER_TOKEN to your .env file."}

    # Build crypto-specific search query
    symbol_upper = symbol.upper()
    primary_query = f'${symbol_upper}'
    crypto_keywords = ["crypto", "token", "coin", "blockchain", "defi", "nft", "trading", "price", "market", "bull", "bear", "pump", "dump", "moon", "hodl", "buy", "sell"]
    context_queries = [f'${symbol_upper} {keyword}' for keyword in crypto_keywords[:5]]
    query_parts = [primary_query] + context_queries

    # Fix: Only add coin_name context if coin_name is not empty and not equal to symbol
    if coin_name and coin_name.lower() != symbol.lower():
        # Avoid double quotes and empty segments
        coin_name_clean = coin_name.replace('"', '').strip()
        if coin_name_clean:
            coin_context_queries = [f'{coin_name_clean} {kw}' for kw in crypto_keywords[:3]]
            query_parts.extend(coin_context_queries)

    # Combine queries with OR, prioritizing the $ symbol format
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
        def make_twitter_request():
            response = requests.get(TWITTER_SEARCH_URL, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        try:
            data = retry_api_call(make_twitter_request)
            if not data or "data" not in data:
                # Robust error handling for empty or malformed responses
                return {"status": "error", "result": "No social sentiment data available (Twitter API returned no data)."}
            batch = data.get("data", [])
            tweets.extend(batch)
            fetched += len(batch)
            next_token = data.get("meta", {}).get("next_token")
            if not next_token or len(tweets) >= max_tweets:
                break
            time.sleep(1)  # Rate limit safety
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            print(f"[DEBUG] Twitter API HTTP error: {status_code}")
            if status_code == 400:
                # FIXME: Twitter API query is malformed or not supported
                return {"status": "error", "result": "Twitter API query was invalid (400 Bad Request). Please try a different coin or check query construction."}
            if status_code == 429:
                print("[DEBUG] Twitter rate limit exceeded, stopping tweet fetch")
                break
            elif status_code == 401:
                print("[DEBUG] Twitter API unauthorized - check bearer token")
                break
            elif status_code == 403:
                print("[DEBUG] Twitter API forbidden - check API permissions")
                break
            elif status_code >= 500:
                print("[DEBUG] Twitter server error, stopping tweet fetch")
                break
            else:
                print(f"[DEBUG] Twitter API error {status_code}, stopping tweet fetch")
                break
        except requests.exceptions.Timeout as e:
            print(f"[DEBUG] Twitter API timeout: {e}")
            break
        except requests.exceptions.ConnectionError as e:
            print(f"[DEBUG] Twitter API connection error: {e}")
            break
        except Exception as e:
            print(f"[DEBUG] Twitter API unexpected error: {e}")
            break
    tweets = tweets[:max_tweets]

    # Additional filtering: Only keep tweets that actually mention the crypto token
    filtered_tweets = []
    for tweet in tweets:
        text = tweet["text"].lower()
        if (f"${symbol_upper.lower()}" in text or 
            f"${symbol.lower()}" in text or
            (coin_name and coin_name.lower() in text and any(kw in text for kw in crypto_keywords))):
            filtered_tweets.append(tweet)
    tweets = filtered_tweets[:max_tweets]

    if not tweets:
        return {"status": "error", "result": "No relevant tweets found for sentiment analysis."}

    # Sentiment analysis (unchanged)
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
    Purpose:
        Get trending hashtags related to a specific cryptocurrency.
    Args:
        symbol (str): The cryptocurrency symbol.
    Returns:
        str: Trending hashtags and their sentiment (not implemented).
    Exceptions:
        None
    """
    # TODO: Implement actual Twitter API logic to fetch trending hashtags for the given symbol.
    # This is currently a placeholder and always returns a static string.
    return "(Not implemented)"

@tool
def get_influencer_mentions(symbol: str) -> str:
    """
    Purpose:
        Get mentions of a cryptocurrency by influential accounts.
    Args:
        symbol (str): The cryptocurrency symbol.
    Returns:
        str: Influencer mention data (not implemented).
    Exceptions:
        None
    """
    # TODO: Implement actual Twitter API logic to fetch influencer mentions for the given symbol.
    # This is currently a placeholder and always returns a static string.
    return "(Not implemented)" 