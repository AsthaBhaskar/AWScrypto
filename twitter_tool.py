import os
import requests
import time
import random
from strands import tool
from dotenv import load_dotenv
from textblob import TextBlob

def retry_api_call(func, max_retries=3, base_delay=1, max_delay=10, backoff_factor=2):
    """
    Retry utility for API calls with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_factor: Multiplier for exponential backoff
    
    Returns:
        Result of the function call or None if all retries failed
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
            
        def make_twitter_request():
            response = requests.get(TWITTER_SEARCH_URL, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        
        try:
            data = retry_api_call(make_twitter_request)
            if not data:
                print(f"[DEBUG] Failed to fetch tweets from Twitter after retries for {symbol}")
                break
                
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