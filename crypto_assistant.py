#!/usr/bin/env python3
"""
Naomi - Crypto Assistant powered by xAI Grok and AWS Strands
Provides comprehensive crypto analysis by synthesizing data from CoinGecko, Nansen, Twitter, and Grok APIs. Replicates Google ADK crypto bot functionality with enhanced conversational and analytical features.
"""

import os
import re
import difflib
import logging
import time
import random 
import datetime
from dotenv import load_dotenv
from strands import Agent
from grok_model import GrokModel
from coingecko_tool import search_coin_id, get_coin_details, get_historical_performance
from nansen_tool import get_onchain_analytics, get_smart_money_flow, get_native_asset_smart_money_flow, get_token_smart_money_flow
from twitter_tool import get_social_sentiment, get_trending_hashtags, get_influencer_mentions
from conversation_tool import handle_conversation
import traceback
import requests  
import itertools

# Load environment variables
load_dotenv()

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

def check_network_connectivity():
    """
    Purpose:
        Check basic network connectivity to help diagnose connection issues with external APIs.
    Args:
        None
    Returns:
        dict: Status, status_code, and response_time for each tested API endpoint.
    Exceptions:
        Handles requests exceptions and generic exceptions. Returns error dict on failure.
    """
    
    test_urls = [
        "https://api.coingecko.com/api/v3/ping",
        "https://api.x.ai/v1/models",
        "https://api.twitter.com/2/tweets/search/recent"
    ]
    
    results = {}
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            results[url] = {
                "status": "connected",
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except requests.exceptions.ConnectionError:
            results[url] = {"status": "connection_failed"}
        except requests.exceptions.Timeout:
            results[url] = {"status": "timeout"}
        except Exception as e:
            results[url] = {"status": "error", "error": str(e)}
    
    return results

NAOMI_SYSTEM_PROMPT = '''
You are Naomi, a sharp-witted, Gen Z crypto market analyst created by Insight Labs AI. You are confident and you ALWAYS back up your sass with hard data. But never mention having the sass or the technology used in the backend like nansen, coingecko, twitter, grok 4, etc. 

Your workflow is to provide comprehensive crypto analysis by synthesizing multiple data sources:

1. **Price & Market Data**: Current price, market cap, 24h/7d/30d performance from CoinGecko
2. **Smart Money Flow**: 24h, 7d, 30d net flows, trader counts, and actionable signals from Nansen
3. **Social Sentiment**: Twitter sentiment and community buzz analysis
4. **Synthesis**: Correlate all data sources to provide actionable insights

When analyzing data:
- Always include current price and performance metrics (24h, 7d, 30d)
- Interpret smart money flows: positive flows = buying, negative flows = selling
- Correlate price movements with smart money behavior and social sentiment
- Provide clear, actionable recommendations based on the data
- Use your signature Gen Z style: confident, witty, and data-driven
- Give specific insights about what the data means for traders/investors

Remember: The market moves fast, so historical context (1h, 24h, 7d, 30d) is CRUCIAL for understanding momentum and trends. Don't just report numbers—interpret them and provide actionable alpha!
'''

# Content Safety Filtering
# PROHIBITED_KEYWORDS = [
#     # Explicit/sexual coins
#     "sexcoin", "titcoin", "porncoin", "clitcoin", "analcoin", "dickcoin", "pussycoin", "cumrocket", "cumcoin", "asscoin", "fapcoin", "boobcoin", "vaginacoin", "milfcoin", "hustlercoin", "xxxcoin", "porn", "sex", "rape", "child", "pedo", "incest", "loli", "lolita", "cp", "nsfw", "explicit", "nude", "nudes", "escort", "prostitute", "prostitution",
#     # Hate/racism
#     "nazi", "hitler", "kkk", "white power", "heil", "racist", "slur", "lynch", "genocide", "holocaust", "antisemitic", "antiblack", "antigay", "homophobic", "transphobic", "islamophobic", "jewish slur", "hate crime",
#     # Violence/illegal
#     "terror", "terrorist", "bomb", "shoot", "murder", "kill", "assassinate", "massacre", "school shooting", "gun violence", "drug", "cocaine", "heroin", "meth", "fentanyl", "scam", "fraud", "hack", "exploit", "phishing", "malware", "ransomware", "darkweb", "dark web", "illegal", "counterfeit", "money laundering", "launder", "traffick", "human trafficking", "organ trafficking"
# ]

# PROHIBITED_REGEX = [
#     r"child\s*(porn|sex|abuse|exploitation|molest|loli|lolita|cp)",
#     r"\bsex\b.*coin", r"\btit\b.*coin", r"\bporn\b.*coin", r"\bboob\b.*coin", r"\bdick\b.*coin", r"\bass\b.*coin", r"\bcum\b.*coin", r"\bclit\b.*coin", r"\bpussy\b.*coin",
#     r"\b(nazi|hitler|kkk|white power|heil|racist|slur|lynch|genocide|holocaust|antisemitic|antiblack|antigay|homophobic|transphobic|islamophobic|hate crime)\b",
#     r"\b(terror|terrorist|bomb|shoot|murder|kill|assassinate|massacre|school shooting|gun violence)\b",
#     r"\b(cocaine|heroin|meth|fentanyl)\b",
#     r"\b(scam|fraud|hack|exploit|phishing|malware|ransomware)\b",
#     r"\b(darkweb|dark web|illegal|counterfeit|money laundering|launder|traffick|human trafficking|organ trafficking)\b"
# ]

# FUZZY_THRESHOLD = 0.85
# AMBIGUOUS_KEYWORDS = ["controversial", "taboo", "offensive", "inappropriate", "nsfw", "illegal", "banned", "forbidden", "unethical", "problematic", "hate", "racist", "sex", "explicit", "adult"]

# APOLOGY_BANNER = "We're sorry, but we cannot assist with that request as it violates our content safety policies. Please try a different question related to cryptocurrency or blockchain technology."
# CLARIFY_BANNER = "Could you please clarify your question? I'm here to help with crypto-related topics!"

# Track repeated violations
# violation_count = 0

# def is_prohibited_content(user_input):
#     """
#     Purpose:
#         Advanced prohibited content detection with crypto context awareness.
#     Args:
#         user_input (str): User input string to check.
#     Returns:
#         bool: True if content is prohibited, False otherwise.
#     Exceptions:
#         None
#     """
#     text = user_input.lower()
    
#     # Check if this is a legitimate crypto query first
#     crypto_indicators = [
#         "price", "market", "cap", "volume", "change", "performance", "chart", "token", "coin", "crypto", "blockchain", "defi", "nft", "mining", "staking", "yield", "liquidity", "swap", "trade", "buy", "sell", "hodl", "moon", "pump", "dump", "bull", "bear", "altcoin", "meme", "utility", "use case", "adoption", "partnership", "development", "roadmap", "whitepaper", "tokenomics", "circulating", "supply", "burn", "mint", "governance", "dao", "smart contract", "gas", "fee", "transaction", "wallet", "exchange", "dex", "cex", "amm", "liquidity pool", "yield farming", "lending", "borrowing", "collateral", "oracle", "bridge", "layer", "scaling", "consensus", "proof", "validator", "node", "network", "protocol", "dapp", "web3", "metaverse", "gamefi", "play to earn", "move to earn", "learn to earn", "socialfi", "creator economy", "royalties", "fractional", "synthetic", "derivative", "futures", "options", "perpetual", "leverage", "margin", "short", "long", "hedge", "arbitrage", "front running", "mev", "sandwich", "flash loan", "reentrancy", "rug pull", "honeypot", "scam", "legitimate", "audit", "security", "vulnerability", "exploit", "hack", "theft", "recovery", "insurance", "regulation", "compliance", "kyc", "aml", "tax", "reporting", "legal", "illegal", "banned", "restricted", "geoblocked", "vpn", "privacy", "anonymous", "pseudonymous", "transparent", "immutable", "decentralized", "centralized", "permissionless", "permissioned", "public", "private", "consortium", "hybrid", "sidechain", "rollup", "sharding", "fork", "upgrade", "hard fork", "soft fork", "backward compatible", "breaking change", "migration", "airdrop", "claim", "vesting", "lockup", "unlock", "release", "distribution", "allocation", "team", "foundation", "treasury", "reserve", "backing", "collateralized", "algorithmic", "stablecoin", "pegged", "floating", "volatile", "correlation", "beta", "alpha", "sharpe ratio", "risk", "reward", "volatility", "liquidity", "depth", "spread", "slippage", "impact", "market maker", "order book", "limit order", "market order", "stop loss", "take profit", "dca", "hodl", "diamond hands", "paper hands", "fomo", "fud", "shill", "moonboy", "maxi", "fanboy", "hater", "skeptic", "believer", "adopter", "early", "late", "fomo", "fud", "shill", "moonboy", "maxi", "fanboy", "hater", "skeptic", "believer", "adopter", "early", "late", "shark", "minnow", "dolphin", "octopus", "squid", "ape", "diamond", "paper", "rocket", "moon", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "galaxy", "universe", "cosmos", "polkadot", "cardano", "solana", "avalanche", "polygon", "binance", "coinbase", "kraken", "kucoin", "okx", "bybit", "huobi", "gate", "mexc", "bitget", "whitebit", "bitfinex", "gemini", "ftx", "celsius", "voyager", "blockfi", "nexo", "crypto.com", "robinhood", "webull", "etoro", "tradingview", "coingecko", "coinmarketcap", "messari", "glassnode", "santiment", "lunar", "intotheblock", "skew", "deribit", "okex", "bitmex"
#     ]
    
#     # If the query contains crypto-related terms, be more lenient
#     has_crypto_context = any(indicator in text for indicator in crypto_indicators)
    
#     # Direct keyword match (but be more careful with crypto context)
#     for word in PROHIBITED_KEYWORDS:
#         if word in text:
#             # If it's a crypto context, check if it's part of a legitimate crypto term
#             if has_crypto_context:
#                 # Skip if it's likely a legitimate crypto term
#                 if word in ["hack", "scam", "fraud", "exploit"] and any(crypto_term in text for crypto_term in ["security", "audit", "vulnerability", "protection", "prevention", "detection", "analysis", "report", "news", "alert", "warning", "risk", "safety"]):
#                     continue
#             return True
    
#     # Regex match (but be more careful with crypto context)
#     for pattern in PROHIBITED_REGEX:
#         if re.search(pattern, text):
#             # If it's a crypto context, check if it's part of a legitimate crypto term
#             if has_crypto_context:
#                 # Skip if it's likely a legitimate crypto term
#                 if "hack" in pattern and any(crypto_term in text for crypto_term in ["security", "audit", "vulnerability", "protection", "prevention", "detection", "analysis", "report", "news", "alert", "warning", "risk", "safety"]):
#                     continue
#             return True
    
#     # Fuzzy match for misspellings (but be more careful with crypto context)
#     for word in PROHIBITED_KEYWORDS:
#         for w in text.split():
#             if difflib.SequenceMatcher(None, word, w).ratio() > FUZZY_THRESHOLD:
#                 # If it's a crypto context, check if it's part of a legitimate crypto term
#                 if has_crypto_context:
#                     # Skip if it's likely a legitimate crypto term
#                     if word in ["hack", "scam", "fraud", "exploit"] and any(crypto_term in text for crypto_term in ["security", "audit", "vulnerability", "protection", "prevention", "detection", "analysis", "report", "news", "alert", "warning", "risk", "safety"]):
#                         continue
#                 return True
    
#     return False

# def is_ambiguous_content(user_input):
#     """
#     Purpose:
#         Check for ambiguous content that needs clarification.
#     Args:
#         user_input (str): User input string to check.
#     Returns:
#         bool: True if content is ambiguous, False otherwise.
#     Exceptions:
#         None
#     """
#     text = user_input.lower()
#     for word in AMBIGUOUS_KEYWORDS:
#         if word in text:
#             return True
#     return False

def classify_intent(user_input: str) -> dict:
    """
    Purpose:
        Classify the user's intent and extract coin name/symbol and timeframe if present.
    Args:
        user_input (str): User input string to classify.
    Returns:
        dict: Keys: intent, coin_query, timeframe.
    Exceptions:
        None
    """
    user_input_lower = user_input.lower()
    
    # Conversational patterns
    greeting_patterns = [r"^hi\b", r"^hello\b", r"^hey\b", r"^sup\b", r"^what's up\b", r"^whats up\b", r"^howdy\b", r"^yo\b", r"^greetings\b", r"^good morning\b", r"^good afternoon\b", r"^good evening\b", r"^gm\b", r"^gn\b", r"^good night\b"]
    farewell_patterns = [r"^bye\b", r"^goodbye\b", r"^see you\b", r"^later\b", r"^cya\b", r"^take care\b", r"^peace\b", r"^peace out\b", r"^adios\b", r"^farewell\b"]
    how_are_you_patterns = [r"how are you", r"how's it going", r"how are things", r"what's new", r"how have you been", r"are you ok", r"are you alright"]
    
    # General conversational patterns (short responses, casual chat)
    general_conversation = [r"^ok\b", r"^okay\b", r"^yeah\b", r"^yep\b", r"^nope\b", r"^nah\b", r"^sure\b", r"^cool\b", r"^nice\b", r"^wow\b", r"^omg\b", r"^lol\b", r"^haha\b", r"^thanks\b", r"^thank you\b", r"^thx\b", r"^ty\b", r"^ho\b", r"^who\b", r"^what\b", r"^why\b", r"^when\b", r"^where\b", r"^how\b"]
    
    # Check for conversational intents first
    for pattern in greeting_patterns:
        if re.search(pattern, user_input_lower):
            return {"intent": "CONVERSATION", "coin_query": None, "timeframe": None}
    
    for pattern in farewell_patterns:
        if re.search(pattern, user_input_lower):
            return {"intent": "CONVERSATION", "coin_query": None, "timeframe": None}
    
    for pattern in how_are_you_patterns:
        if re.search(pattern, user_input_lower):
            return {"intent": "CONVERSATION", "coin_query": None, "timeframe": None}
    
    # Check for general conversation patterns
    for pattern in general_conversation:
        if re.search(pattern, user_input_lower):
            return {"intent": "CONVERSATION", "coin_query": None, "timeframe": None}
    
    # Price/performance patterns
    price_patterns = [r"price", r"cost", r"current value", r"trading at", r"market cap", r"volume"]
    
    # Timeframes
    timeframe_patterns = {"1h": r"1h|1 hour|last hour", "24h": r"24h|24 hours|day|today|yesterday", "7d": r"7d|7 days|week", "30d": r"30d|30 days|month"}
    
    # Smart money/on-chain patterns
    onchain_patterns = [r"smart money", r"on.?chain", r"flow", r"wallet", r"transfer", r"movement", r"working", r"playing"]
    
    # Social sentiment patterns
    social_patterns = [r"sentiment", r"twitter", r"social", r"community", r"hype", r"news", r"rumor"]
    
    # Extract coin query (symbol or name)
    coin_query = None
    match = re.search(r"\$(\w+)", user_input)
    if match:
        coin_query = match.group(1)
    else:
        # Enhanced coin extraction logic
        # First, try to find common crypto-related patterns
        crypto_patterns = [
            r"hows\s+(\w+)\s+doing",  # "hows pump doing", "hows bitcoin doing"
            r"how\s+(?:is|are)\s+(\w+)",  # "how is bitcoin", "how are eth"
            r"what\s+(?:is|about)\s+(\w+)",  # "what is bitcoin", "what about eth"
            r"tell\s+me\s+about\s+(\w+)",  # "tell me about bitcoin"
            r"(\w+)\s+(?:price|performance|chart|data)",  # "bitcoin price", "eth performance"
            r"(\w+)\s+(?:doing|performing|trading)",  # "bitcoin doing", "eth performing"
            r"(\w+)\s+(?:smart\s+money|flow)",  # "bitcoin smart money", "eth flow"
            r"(\w+)\s+(?:sentiment|social|twitter)",  # "bitcoin sentiment", "eth social"
        ]
        
        for pattern in crypto_patterns:
            match = re.search(pattern, user_input_lower)
            if match:
                potential_coin = match.group(1)
                # Filter out common words that aren't coins
                if potential_coin not in ["the", "a", "an", "this", "that", "what", "how", "when", "where", "why", "which", "who", "whose", "whom", "price", "cost", "current", "value", "trading", "at", "market", "cap", "volume", "of", "is", "for", "to", "in", "on", "and", "with", "show", "me", "much", "tell", "about", "give", "get", "latest", "recent", "news", "rumor", "sentiment", "twitter", "social", "community", "hype", "whale", "smart", "money", "flow", "wallet", "transfer", "movement", "performance", "over", "last", "days", "hours", "week", "month", "today", "yesterday", "doing", "performing", "chart", "data"]:
                    coin_query = potential_coin
                    break
        
        # If no pattern match, try to find standalone coin names
        if not coin_query:
            # Look for words that are likely coin names (3+ chars, alphanumeric)
            words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", user_input_lower)
            # Prioritize words that look like coin names (no common English words)
            common_words = ["price", "cost", "current", "value", "trading", "at", "market", "cap", "volume", "of", "the", "is", "for", "to", "in", "on", "and", "a", "an", "with", "show", "me", "how", "much", "what", "tell", "about", "give", "get", "latest", "recent", "news", "rumor", "sentiment", "twitter", "social", "community", "hype", "whale", "smart", "money", "flow", "wallet", "transfer", "movement", "performance", "over", "last", "days", "hours", "week", "month", "today", "yesterday", "doing", "performing", "chart", "data", "hows", "whats", "whens", "wheres", "whys", "whos", "thats", "this", "that", "these", "those", "have", "has", "had", "will", "would", "could", "should", "might", "may", "can", "must", "shall", "do", "does", "did", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "might", "may", "can", "must", "shall"]
            for word in words:
                if word not in common_words and len(word) >= 3:
                    coin_query = word
                    break
    
    # Special handling for "tell me about X" queries
    if "tell me about" in user_input_lower and coin_query:
        intent = "GENERAL"  # Treat as general crypto query to get comprehensive data
    
    # If no specific coin found but crypto-related keywords detected, treat as general crypto query
    if not coin_query and any(re.search(p, user_input_lower) for p in social_patterns + onchain_patterns + price_patterns):
        coin_query = "bitcoin"  # Default to bitcoin for general crypto queries
    
    # Extract timeframe
    timeframe = None
    for tf, pat in timeframe_patterns.items():
        if re.search(pat, user_input_lower):
            timeframe = tf
            break
    
    # Detect intent
    intent = "GENERAL"
    if any(re.search(p, user_input_lower) for p in price_patterns):
        intent = "PRICE"
    if any(re.search(p, user_input_lower) for p in onchain_patterns):
        intent = "ONCHAIN"
    if any(re.search(p, user_input_lower) for p in social_patterns):
        intent = "SOCIAL"
    if any(re.search(p, user_input_lower) for p in ["performance", "change", "gain", "loss", "return"]):
        intent = "PERFORMANCE"
    
    return {"intent": intent, "coin_query": coin_query, "timeframe": timeframe}

def generate_simple_charts(price_data, smart_money_data, social_sentiment):
    """
    Purpose:
        Generate simple ASCII/emoji-based charts for visual representation of price, smart money, and social sentiment.
    Args:
        price_data (dict): Price performance data.
        smart_money_data (dict): Smart money flow data.
        social_sentiment (str): Social sentiment summary.
    Returns:
        str: Formatted chart string or data unavailable message.
    Exceptions:
        Handles ValueError, TypeError, KeyError, AttributeError, OSError, IOError, and generic Exception. Returns chart with data unavailable on error.
    """
    charts = []
    
    # Price performance chart
    if price_data:
        try:
            price_24h = float(price_data.get("price_change_24h", 0))
            price_7d = float(price_data.get("price_change_7d", 0))
            
            charts.append("📈 Price Performance:")
            charts.append(f"24h: {'🟢' if price_24h > 0 else '🔴'} {price_24h:+.2f}%")
            charts.append(f"7d:  {'🟢' if price_7d > 0 else '🔴'} {price_7d:+.2f}%")
            charts.append("")
        except (ValueError, TypeError) as e:
            # Handle invalid price data gracefully
            charts.append("📈 Price Performance: Data unavailable")
            charts.append("")
        except (KeyError, AttributeError) as e:
            # Handle missing data structure issues
            print(f"Warning: Invalid price data structure: {str(e)}")
            charts.append("📈 Price Performance: Data unavailable")
            charts.append("")
        except (OSError, IOError) as e:
            # Handle system-level errors
            print(f"Warning: System error generating price charts: {str(e)}")
            charts.append("📈 Price Performance: Data unavailable")
            charts.append("")
        except Exception as e:
            # Log unexpected errors but don't crash - this should rarely be reached
            print(f"Warning: Unexpected error generating price charts: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            charts.append("📈 Price Performance: Data unavailable")
            charts.append("")
    
    # Smart money flow chart
    if smart_money_data and "data" in smart_money_data:
        charts.append("💰 Smart Money Flow:")
        # Defensive check and logging for smart_money_data['data']
        smart_money_data_data = smart_money_data.get('data') if isinstance(smart_money_data, dict) else None
        if isinstance(smart_money_data_data, dict):
            for tf in ["24h", "7d", "30d"]:
                if tf in smart_money_data_data:
                    flow = smart_money_data_data[tf]["netflow_usd"]
                    flow_str = smart_money_data_data[tf]["flow_str"]
                    trader_count = smart_money_data_data[tf].get("trader_count", "N/A")
                
                if flow > 0:
                        charts.append(f"{tf}: 🟢 {flow_str} ({trader_count} traders)")
                elif flow < 0:
                        charts.append(f"{tf}: 🔴 {flow_str} ({trader_count} traders)")
                else:
                        charts.append(f"{tf}: ⚪ {flow_str} ({trader_count} traders)")
        else:
            # Use print instead of logger.error for error reporting
            print(f"smart_money_data['data'] is not a dict: {repr(smart_money_data_data)} (smart_money_data: {repr(smart_money_data)})")
            # Optionally, add a fallback or skip this section
        charts.append("")
    
    # Social sentiment chart
    if social_sentiment:
        charts.append("📱 Social Sentiment:")
        if "positive" in social_sentiment.lower():
            charts.append("🟢 Bullish community sentiment")
        elif "negative" in social_sentiment.lower():
            charts.append("🔴 Bearish community sentiment")
        else:
            charts.append("⚪ Neutral community sentiment")
        charts.append("")
    
    return "\n".join(charts) if charts else "📊 Charts: Data unavailable"

# Helper to ensure tool results are always a dict

def safe_tool_result(result, default_msg="Data unavailable"):
    if not isinstance(result, dict):
        return {"status": "error", "result": default_msg}
    return result

def is_greeting(user_input: str) -> bool:
    """
    Returns True if the user_input is a greeting or conversational opener.
    """
    user_input_lower = user_input.lower().strip()
    greeting_patterns = [
        r"^hi\b", r"^hello\b", r"^hey\b", r"^sup\b", r"^what's up\b", r"^whats up\b", r"^howdy\b", r"^yo\b", r"^greetings\b", r"^good morning\b", r"^good afternoon\b", r"^good evening\b", r"^gm\b", r"^gn\b", r"^good night\b",
        r"^how are you\b", r"^how's it going\b", r"^how are things\b", r"^how have you been\b", r"^how's life\b", r"^how's everything\b", r"^how's your day\b", r"^how's your week\b", r"^how's your morning\b", r"^how's your evening\b",
        r"^what's new\b", r"^what's happening\b", r"^what's good\b", r"^what's cracking\b", r"^what's poppin\b", r"^yo\b", r"^oi\b", r"^hola\b", r"^bonjour\b", r"^ciao\b"
    ]
    for pat in greeting_patterns:
        if re.match(pat, user_input_lower):
            return True
    # Also treat short greetings as greetings
    if user_input_lower in ["hi", "hello", "hey", "gm", "gn", "yo", "sup", "hola", "oi", "bonjour", "ciao"]:
        return True
    return False

def random_naomi_greeting():
    # Generate a fresh, conversational greeting in Naomi's style
    time_of_day = datetime.datetime.now().hour
    if time_of_day < 12:
        tod = "morning"
    elif time_of_day < 18:
        tod = "afternoon"
    else:
        tod = "evening"
    openers = [
        f"Hi, I'm Naomi! Created by Insight Labs AI. Hope your {tod} is as bullish as the market!",
        f"Hey there! Naomi here, your Gen Z crypto analyst from Insight Labs AI. What's on your crypto radar this {tod}?",
        f"GM! Naomi in the house, powered by Insight Labs AI. Ready to catch some alpha this {tod}?",
        f"Hello! Naomi here, Insight Labs AI's sharp-witted crypto analyst. Got a coin or trend you want to chat about this {tod}?",
        f"Yo! Naomi here, your crypto confidante from Insight Labs AI. Let's dive into the markets together!",
        f"Howdy! Naomi at your service, crafted by Insight Labs AI. What crypto alpha are you hunting for today?",
        f"Hi! Naomi here, Insight Labs AI's resident crypto enthusiast. Ask me anything about the wild world of digital assets!",
        f"Hey! Naomi here. The charts are moving and so am I. What are we analyzing today?",
        f"Wassup! Naomi from Insight Labs AI. Ready to decode the blockchain chaos?",
        f"Hey legend! Naomi here. Let's make this {tod} a profitable one!"
    ]
    emojis = ["🚀", "😎", "💎", "🔥", "🦄", "🌞", "🌙", "💬", "📈", "🤑"]
    return f"{random.choice(openers)} {random.choice(emojis)}"

def extract_intents_and_coins(user_input: str):
    """
    Extracts a list of (intent, coin) pairs from the user input.
    Supports multi-coin and multi-intent queries.
    Returns: list of (intent, coin) tuples, and a flag for general/greeting intent, and a flag for investment advice request.
    """
    user_input_lower = user_input.lower()
    if is_greeting(user_input):
        return [], True, False, False
    # Patterns that require a comprehensive general analysis
    general_analysis_patterns = [
        r"what'?s up with ([a-zA-Z0-9$ ]+)",
        r"tell me more( about)? ([a-zA-Z0-9$ ]+)?",
        r"tell me about ([a-zA-Z0-9, $]+)",
        r"should i (?:invest in|buy|sell|hold|buy or sell|buy/sell|hold or sell|hold/sell|buy hold or sell|buy hold sell|buy or hold|buy/hold|sell or hold|sell/hold) ([a-zA-Z0-9$ ]+)",
        r"should i (?:buy|sell|hold|invest in) ([a-zA-Z0-9$ ]+)",
        r"give me an? (update|overview|summary) (on|of)? ([a-zA-Z0-9$ ]+)?",
        r"what do you think about ([a-zA-Z0-9$ ]+)",
        r"what can you tell me about ([a-zA-Z0-9$ ]+)",
        r"any news on ([a-zA-Z0-9$ ]+)",
        r"what'?s happening with ([a-zA-Z0-9$ ]+)",
        r"how'?s ([a-zA-Z0-9$ ]+) doing",
        r"how is ([a-zA-Z0-9$ ]+)",
        r"what about ([a-zA-Z0-9$ ]+)"
    ]
    # Expanded stopword list for solid filtering
    stopwords = set([
        'update', 'overview', 'summary', 'any', 'buy', 'sell', 'hold', 'my', 'on', 'of', 'the', 'a', 'an', 'is', 'are', 'do', 'does', 'did', 'should', 'i', 'me', 'about', 'in', 'to', 'for', 'with', 'at', 'by', 'from', 'it', 'this', 'that', 'these', 'those', 'and', 'or', 'but', 'so', 'if', 'then', 'than', 'as', 'be', 'been', 'being', 'was', 'were', 'will', 'would', 'can', 'could', 'may', 'might', 'must', 'shall', 'not', 'no', 'yes', 'you', 'your', 'yours', 'we', 'our', 'ours', 'they', 'their', 'theirs', 'he', 'him', 'his', 'she', 'her', 'hers', 'its', 'them', 'who', 'whom', 'whose', 'which', 'what', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'nor', 'too', 'very', 'can', 'just', 'now', 'out', 'up', 'down', 'over', 'under', 'again', 'further', 'then', 'once'
    ])
    for pat in general_analysis_patterns:
        m = re.search(pat, user_input_lower)
        if m:
            # Only use the last group (the coin) if present and not a stopword
            coin_part = None
            groups = m.groups()
            if groups:
                last_group = groups[-1]
                if last_group and last_group.strip():
                    candidate = last_group.strip()
                    candidate = re.sub(r"[?.!,]$", "", candidate)
                    if candidate.lower() not in stopwords:
                        coin_part = candidate
            coins = set()
            if coin_part:
                # If $SYMBOL, extract symbol
                m2 = re.findall(r"\$([a-zA-Z0-9]+)", coin_part)
                if m2:
                    coins.update([x.lower() for x in m2])
                else:
                    # Otherwise, just use the word(s) as coin name, skipping stopwords
                    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", coin_part)
                    for w in words:
                        if w.lower() not in stopwords:
                            coins.add(w.lower())
            # If no coin found, fallback to extracting the last $SYMBOL or last non-stopword word from the whole input
            if not coins:
                m3 = re.findall(r"\$([a-zA-Z0-9]+)", user_input_lower)
                if m3:
                    coins.add(m3[-1].lower())
                else:
                    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", user_input_lower)
                    for w in reversed(words):
                        if w.lower() not in stopwords:
                            coins.add(w.lower())
                            break
            return [("GENERAL", coin) for coin in coins] if coins else [], False, True, True
    # Investment advice patterns
    investment_advice_patterns = [
        r"should i invest", r"is it a good buy", r"is it worth", r"is it a good investment", r"should i buy", r"should i hold", r"should i sell", r"is it time to buy", r"is it time to sell", r"would you invest", r"do you recommend", r"would you buy", r"would you hold", r"would you sell", r"is it safe to invest", r"is it risky", r"is it safe", r"is it risky to invest", r"is it a scam", r"is it legit", r"is it legitimate", r"is it a rug", r"is it a rugpull", r"is it a rug pull", r"is it a pump and dump", r"is it a ponzi", r"is it a pyramid", r"is it a good idea", r"should i put money", r"should i put my money", r"should i trust", r"should i avoid", r"should i get in", r"should i get out", r"should i fomo", r"should i ape", r"should i diamond hand", r"should i paper hand", r"should i dca", r"should i go all in", r"should i go in", r"should i go out", r"should i exit", r"should i enter", r"should i jump in", r"should i jump out", r"should i participate", r"should i join", r"should i stay", r"should i leave", r"should i keep", r"should i continue", r"should i stop", r"should i quit", r"should i abandon", r"should i cash out", r"should i take profit", r"should i take profits", r"should i take my profit", r"should i take my profits", r"should i realize gains", r"should i realize losses", r"should i cut losses", r"should i cut my losses", r"should i cut my gains", r"should i cut my profit", r"should i cut my profits", r"should i cut my position", r"should i close position", r"should i close my position", r"should i close positions", r"should i close my positions", r"should i open position", r"should i open my position", r"should i open positions", r"should i open my positions", r"should i open a position", r"should i open new position", r"should i open new positions", r"should i open a new position", r"should i open a new positions", r"should i open another position", r"should i open another positions", r"should i open more position", r"should i open more positions", r"should i open more", r"should i buy more", r"should i sell more", r"should i hold more", r"should i invest more", r"should i put more", r"should i put more money", r"should i put more in", r"should i put more into", r"should i put more on", r"should i put more onto", r"should i put more towards", r"should i put more toward", r"should i put more for", r"should i put more with", r"should i put more to", r"should i put more at", r"should i put more by", r"should i put more from", r"should i put more of", r"should i put more off", r"should i put more out", r"should i put more over", r"should i put more under", r"should i put more up", r"should i put more down"
    ]
    investment_advice_requested = False
    for pattern in investment_advice_patterns:
        if re.search(pattern, user_input_lower):
            investment_advice_requested = True
            break
    # Special handling: If the input matches 'should i (buy|invest in|sell|hold) <coin>' or similar, extract <coin> directly
    # e.g. 'should i buy xrp?', 'should i invest in solana?', etc.
    advice_coin_match = re.search(r"should i (?:buy|invest in|sell|hold)\s+([a-zA-Z0-9$ ]+)", user_input_lower)
    if advice_coin_match:
        # Try to extract $SYMBOL or coin name
        coin_part = advice_coin_match.group(1).strip()
        # Remove trailing punctuation
        coin_part = re.sub(r"[?.!,]$", "", coin_part)
        # If $SYMBOL, extract symbol
        m = re.findall(r"\$([a-zA-Z0-9]+)", coin_part)
        coins = set()
        if m:
            coins.update([x.lower() for x in m])
        else:
            # Otherwise, just use the word(s) as coin name
            words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", coin_part)
            for w in words:
                coins.add(w.lower())
        # Default to GENERAL intent if not found
        found_intents = {"GENERAL"}
        pairs = list(itertools.product(found_intents, coins))
        return pairs, False, False, True
    if "tell me about" in user_input_lower:
        # General/comprehensive
        coins = re.findall(r"tell me about ([a-zA-Z0-9, ]+)", user_input_lower)
        if coins:
            coin_list = [c.strip() for c in re.split(r",| and | \& ", coins[0]) if c.strip()]
        else:
            coin_list = []
        return [("GENERAL", coin) for coin in coin_list] if coin_list else [], False, True, investment_advice_requested
    # Multi-coin extraction (split on 'and', ',', '&')
    coin_candidates = re.split(r" and |,| & ", user_input)
    # Remove empty and trim
    coin_candidates = [c.strip() for c in coin_candidates if c.strip()]
    # Intents
    intent_map = {
        "PRICE": [r"price", r"current value", r"trading at", r"cost"],
        "PERFORMANCE": [r"performance", r"change", r"gain", r"loss", r"return", r"24h", r"7d", r"30d", r"1h"],
        "SENTIMENT": [r"sentiment", r"twitter", r"social", r"community", r"hype", r"buzz", r"reacting", r"reaction", r"opinion", r"talking", r"discussing", r"feeling", r"mood", r"vibe", r"vibes"],
        "ONCHAIN": [r"smart money", r"on.?chain", r"flow", r"wallet", r"whale", r"accumulation", r"distribution", r"nansen", r"trader", r"trading"],
        "TRADING_PATTERN": [r"trading pattern", r"pattern analysis", r"trading analytics", r"pattern insight", r"pattern summary", r"pattern report"]
    }
    found_intents = set()
    for intent, pats in intent_map.items():
        for pat in pats:
            if re.search(pat, user_input_lower):
                found_intents.add(intent)
    # If no explicit intent, default to GENERAL
    if not found_intents:
        found_intents = {"GENERAL"}
    # Expanded stopword list for solid filtering
    stopwords = set([
        # ... (unchanged stopwords list) ...
    ])
    # Exclude intent words from being treated as coins
    intent_words = set([w for pats in intent_map.values() for w in [re.sub(r"[^a-zA-Z0-9]", "", p) for p in pats]])
    coins = set()
    for c in coin_candidates:
        # Skip if segment is just an investment advice phrase or 'it'
        if any(re.search(pattern, c.lower()) for pattern in investment_advice_patterns) or c.strip().lower() in ["it", "this", "that"]:
            continue
        # $SYMBOL
        m = re.findall(r"\$([a-zA-Z0-9]+)", c)
        if m:
            coins.update([x.lower() for x in m])
        else:
            # Try to find likely coin names (3+ chars, not stopwords or intent words)
            words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", c)
            for w in words:
                wl = w.lower()
                if wl not in stopwords and wl not in intent_words:
                    coins.add(wl)
    if not coins:
        # fallback: try to extract a single coin from the whole input
        m = re.findall(r"\b[a-zA-Z0-9]{3,}\b", user_input_lower)
        for w in m:
            wl = w.lower()
            if wl not in stopwords and wl not in intent_words:
                coins.add(wl)
                break
    # Build (intent, coin) pairs (cartesian product)
    pairs = list(itertools.product(found_intents, coins))
    return pairs, False, False, investment_advice_requested

def build_focused_response(pairs, investment_advice_requested=False):
    """
    Given a list of (intent, coin) pairs, fetch and format the relevant data for each.
    Returns a concise, conversational response in Naomi's style.
    If investment_advice_requested is True, append a disclaimer and do not provide financial advice.
    """
    # Varied templates for each intent
    price_templates = [
        "{coin}: ${price} — That's the latest price, but you know how wild crypto gets! {emoji}",
        "{coin}: ${price} — Fresh off the blockchain! {emoji}",
        "{coin}: ${price} — Markets move fast, so keep your eyes peeled! {emoji}",
        "{coin}: ${price} — Real-time alpha, just for you! {emoji}"
    ]
    price_emojis = ["🚀", "💸", "📈", "🤑", "🔥"]
    perf_templates = [
        "{coin} performance: {perf} — That's some serious price action! {emoji}",
        "{coin} performance: {perf} — Volatility vibes! {emoji}",
        "{coin} performance: {perf} — Up, down, and all around! {emoji}",
        "{coin} performance: {perf} — The charts never sleep! {emoji}"
    ]
    perf_emojis = ["📊", "📉", "📈", "🔥"]
    sentiment_templates = [
        "{coin} Twitter sentiment: {summary} — That's the vibe right now! {emoji}",
        "{coin} Twitter sentiment: {summary} — The community's buzzing! {emoji}",
        "{coin} Twitter sentiment: {summary} — Social signals incoming! {emoji}",
        "{coin} Twitter sentiment: {summary} — Crypto Twitter never disappoints! {emoji}"
    ]
    sentiment_emojis = ["💬", "🐦", "🔥", "😎"]
    smart_money_templates = [
        "{coin} smart money: {msg} — That's what the whales are up to! {emoji}",
        "{coin} smart money: {msg} — Whale watching in real time! {emoji}",
        "{coin} smart money: {msg} — On-chain alpha unlocked! {emoji}",
        "{coin} smart money: {msg} — The big players are making moves! {emoji}"
    ]
    smart_money_emojis = ["🐋", "🦈", "💰", "🌊"]
    responses = []
    for intent, coin in pairs:
        coin_id = search_coin_id(coin)
        if not coin_id:
            responses.append(f"{coin.upper()}: Not found on CoinGecko. Maybe it's too new or super obscure. 👀")
            continue
        if intent == "PRICE":
            details = get_coin_details(coin_id)
            if details.get("status") == "success":
                template = random.choice(price_templates)
                emoji = random.choice(price_emojis)
                responses.append(template.format(coin=coin.upper(), price=details.get('current_price', 'N/A'), emoji=emoji))
            else:
                responses.append(f"{coin.upper()}: Price unavailable. Even Naomi can't find it right now. 😅")
        elif intent == "PERFORMANCE":
            details = get_coin_details(coin_id)
            if details.get("status") == "success":
                perf = []
                for tf in ["1h", "24h", "7d", "30d"]:
                    val = details.get(f"price_change_{tf}", None)
                    if val not in [None, "N/A"]:
                        perf.append(f"{tf}: {val:+.2f}%" if isinstance(val, (int, float)) else f"{tf}: {val}")
                if perf:
                    template = random.choice(perf_templates)
                    emoji = random.choice(perf_emojis)
                    responses.append(template.format(coin=coin.upper(), perf=' | '.join(perf), emoji=emoji))
                else:
                    responses.append(f"{coin.upper()}: Performance data unavailable. Even the charts are shy today. 📉")
            else:
                responses.append(f"{coin.upper()}: Performance data unavailable. Even the charts are shy today. 📉")
        elif intent == "SENTIMENT":
            sentiment = get_social_sentiment(coin)
            if sentiment.get("status") == "success":
                template = random.choice(sentiment_templates)
                emoji = random.choice(sentiment_emojis)
                responses.append(template.format(coin=coin.upper(), summary=sentiment.get('summary', 'No summary available.'), emoji=emoji))
            else:
                responses.append(f"{coin.upper()}: Twitter sentiment unavailable. Couldn't fetch the vibes right now, but the community's always buzzing. 😅")
        elif intent == "ONCHAIN":
            nansen = get_smart_money_flow(coin)
            if nansen.get("status") == "success":
                template = random.choice(smart_money_templates)
                emoji = random.choice(smart_money_emojis)
                msg = nansen.get("message") or nansen.get("result")
                responses.append(template.format(coin=coin.upper(), msg=msg, emoji=emoji))
            else:
                responses.append(f"{coin.upper()}: Smart money data unavailable. Even the whales are hiding. 🐳")
        elif intent == "TRADING_PATTERN":
            # Only return trading pattern analysis for this intent
            nansen = get_smart_money_flow(coin)
            # Always generate a trading pattern summary using available Nansen smart money flow data
            def format_trading_pattern_analysis(smart_money_data):
                flows = smart_money_data.get('flows') if isinstance(smart_money_data, dict) else None
                if not flows or (not flows.get('24h') and not flows.get('7d')):
                    return f"{coin.upper()}: No trading pattern data available for this coin right now. It might be too new or too illiquid for on-chain analytics. 😅"
                analysis_lines = []
                for tf in ['24h', '7d']:
                    flow = flows.get(tf)
                    if not flow or 'raw' not in flow:
                        continue
                    raw = flow['raw']
                    analysis_lines.append(f"\n{tf.upper()}:")
                    whale_flow = raw.get('whaleFlow', 0)
                    whale_wallets = raw.get('whaleWallets', 'N/A')
                    smart_trader_flow = raw.get('smartTraderFlow', 0)
                    smart_trader_wallets = raw.get('smartTraderWallets', 'N/A')
                    top_pnl_flow = raw.get('topPnlFlow', 0)
                    top_pnl_wallets = raw.get('topPnlWallets', 'N/A')
                    exchange_flow = raw.get('exchangeFlow', 0)
                    public_figure_flow = raw.get('publicFigureFlow', 0)
                    public_figure_wallets = raw.get('publicFigureWallets', 'N/A')
                    analysis_lines.append(f"  • Whale Flow: ${whale_flow:,.2f} ({whale_wallets} wallets)")
                    analysis_lines.append(f"  • Smart Trader Flow: ${smart_trader_flow:,.2f} ({smart_trader_wallets} wallets)")
                    analysis_lines.append(f"  • Top PnL Flow: ${top_pnl_flow:,.2f} ({top_pnl_wallets} wallets)")
                    analysis_lines.append(f"  • Exchange Flow: ${exchange_flow:,.2f}")
                    analysis_lines.append(f"  • Public Figure Flow: ${public_figure_flow:,.2f} ({public_figure_wallets} wallets)")
                # Simple interpretation
                interpretation = []
                if flows.get('24h', {}) and flows['24h'].get('raw', {}).get('whaleFlow', 0) > 0 and flows.get('7d', {}) and flows['7d'].get('raw', {}).get('whaleFlow', 0) > 0:
                    interpretation.append("Whales are accumulating across both 24h and 7d.")
                if flows.get('24h', {}) and flows['24h'].get('raw', {}).get('topPnlFlow', 0) < 0:
                    interpretation.append("Top PnL wallets are taking profits in the last 24h.")
                if flows.get('24h', {}) and flows['24h'].get('raw', {}).get('exchangeFlow', 0) < 0:
                    interpretation.append("Large outflows from exchanges (bullish sign).")
                if not interpretation:
                    interpretation.append("No strong trading pattern detected from available data.")
                analysis_lines.append("\nPattern Summary: " + " ".join(interpretation))
                emojis = ["📊", "🐋", "🦈", "💸", "🔥", "😎"]
                return f"Naomi's Trading Pattern Analysis for {coin.upper()}:" + ''.join(analysis_lines) + f"\n{random.choice(emojis)}"
            pattern_analysis = format_trading_pattern_analysis(nansen)
            responses.append(pattern_analysis)
        else:  # GENERAL or fallback
            details = get_coin_details(coin_id)
            if details.get("status") == "success":
                responses.append(details.get("result"))
            else:
                responses.append(f"{coin.upper()}: Data unavailable. Naomi's got nothing on this one. 🤷‍♀️")
    if investment_advice_requested:
        responses.append("\n⚠️  Disclaimer: This is not financial advice. Naomi provides factual insights and data only. Always do your own research before making investment decisions!")
    return "\n".join(responses)

def main():
    """
    Purpose:
        Main function that orchestrates the crypto analysis workflow for Naomi assistant.
    Args:
        None
    Returns:
        None
    Exceptions:
        Handles and logs all exceptions, prints user-friendly error messages, and continues or exits as appropriate.
    """
    # Set up basic logging for AWS deployment
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('crypto_assistant.log') if os.path.exists('/tmp') else logging.NullHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Validate environment variables
    grok_api_key = os.getenv("GROK_API_KEY")
    if not grok_api_key:
        logger.error("GROK_API_KEY not found in environment variables")
        print("❌ GROK_API_KEY not found in environment variables")
        print("Please set the GROK_API_KEY environment variable to use this application.")
        return
    
    # Check for other optional API keys
    coingecko_api_key = os.getenv("COINGECKO_API_KEY")
    nansen_api_key = os.getenv("NANSEN_API_KEY")
    twitter_api_key = os.getenv("TWITTER_BEARER_TOKEN")
    
    if not coingecko_api_key:
        logger.warning("COINGECKO_API_KEY not found - will use free tier with rate limits")
        print("⚠️  COINGECKO_API_KEY not found - using free tier (rate limited)")
    if not nansen_api_key:
        logger.warning("NANSEN_API_KEY not found - smart money features will be limited")
        print("⚠️  NANSEN_API_KEY not found - smart money analytics will be unavailable")
        print("   Add NANSEN_API_KEY to your .env file for smart money flow data")
    if not twitter_api_key:
        logger.warning("TWITTER_BEARER_TOKEN not found - social sentiment features will be limited")
        print("⚠️  TWITTER_BEARER_TOKEN not found - social sentiment will be unavailable")
        print("   Add TWITTER_BEARER_TOKEN to your .env file for social sentiment analysis")
        print("   Note: TWITTER_API_KEY and TWITTER_API_SECRET are not used by this application")
    
    try:
        grok_model = GrokModel(
            client_args={"api_key": grok_api_key},
            model_id="grok-4-0709",
            params={"max_tokens": 1000, "temperature": 0.7}
        )
        logger.info("Grok model initialized successfully")
    except (ValueError, KeyError) as e:
        logger.error(f"Invalid configuration for Grok model: {e}")
        print(f"❌ Invalid configuration for Grok model: {e}")
        print("Please check your GROK_API_KEY and model parameters.")
        return
    except ConnectionError as e:
        logger.error(f"Network error initializing Grok model: {e}")
        print(f"❌ Network error: Cannot connect to Grok API. Check your internet connection.")
        return
    except TimeoutError as e:
        logger.error(f"Timeout initializing Grok model: {e}")
        print(f"❌ Timeout: Grok API is not responding. Please try again later.")
        return
    except ImportError as e:
        logger.error(f"Import error with Grok model: {e}")
        print(f"❌ Import error: Required dependencies not found. Please check your installation.")
        return
    except Exception as e:
        logger.error(f"Unexpected error initializing Grok model: {e}")
        print(f"❌ Failed to initialize Grok model: {e}")
        print(f"Error type: {type(e).__name__}")
        return
    
    print("\n🟣 Naomi Crypto Assistant (Strands+Grok4) 🟣\n")
    print("Ask me anything about crypto, blockchain, or NFTs!")
    print("Type 'exit' to quit.")
    conversation = []
    
    logger.info("Crypto assistant started successfully")
    
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() == "exit":
                print("\nNaomi: Later, legend! Keep those crypto vibes flowing! ")
                break
            
            # Check for network diagnostic command
            if user_input.lower().strip() in ["network", "connection", "connectivity", "ping", "test connection"]:
                print("Naomi: 🔍 Checking network connectivity...")
                connectivity_results = check_network_connectivity()
                
                print("\n📊 Network Status Report:")
                for url, result in connectivity_results.items():
                    service_name = url.split("//")[1].split("/")[0]
                    if result["status"] == "connected":
                        print(f"✅ {service_name}: Connected ({result['response_time']:.2f}s)")
                    elif result["status"] == "connection_failed":
                        print(f"❌ {service_name}: Connection failed")
                    elif result["status"] == "timeout":
                        print(f"⏰ {service_name}: Timeout")
                    else:
                        print(f"⚠️ {service_name}: Error - {result.get('error', 'Unknown')}")
                
                print("\n💡 If you see connection issues, try:")
                print("• Checking your internet connection")
                print("• Restarting your network/router")
                print("• Checking if the services are down")
                continue
                
            # New: Use enhanced intent/entity extraction
            pairs, is_greeting, is_general, investment_advice_requested = extract_intents_and_coins(user_input)
            if is_greeting:
                greeting = random_naomi_greeting()
                print(greeting)
                conversation.append({"role": "user", "content": user_input})
                conversation.append({"role": "assistant", "content": greeting})
                continue
            if is_general:
                # Fallback to old comprehensive/general analysis
                intent_data = classify_intent(user_input)
                intent = intent_data["intent"]
                symbol = intent_data["coin_query"]
                timeframe = intent_data["timeframe"]

                # Handle conversation intent first
                if intent == "CONVERSATION":
                    conversation_response = handle_conversation(user_input)
                    print(conversation_response)
                    conversation.append({"role": "user", "content": user_input})
                    conversation.append({"role": "assistant", "content": conversation_response})
                    continue
                
                # For crypto queries, we need to find the coin first
                if not symbol:
                    print("Naomi: Hey! What crypto are you asking about? Try something like 'price of bitcoin' or 'how is ethereum doing'? 🤔")
                    continue
                
                # Step 1: Search for the coin on CoinGecko
                print(f"🔍 Searching for {symbol.upper()}...")
                coin_id = search_coin_id(symbol)
                print(f"DEBUG: coin_id={repr(coin_id)} type={type(coin_id)}")
                coin_id = coin_id if isinstance(coin_id, str) and coin_id.strip() else None
                if not coin_id:
                    print(f"Naomi: Oops! I couldn't find {symbol.upper()} on CoinGecko. Maybe try a different spelling or check if it's listed? 🤷‍♀️")
                    continue
                if not re.match(r'^[a-zA-Z0-9-]+$', coin_id):
                    print(f"Naomi: Invalid coin ID format for {symbol.upper()}. Please try a different symbol or check the spelling.")
                    continue
                
                # Step 2: Get detailed coin information
                print(f"📊 Getting data for {symbol.upper()}...")
                coin_details = safe_tool_result(get_coin_details(coin_id), "Coin details unavailable.")
                print(f"DEBUG: coin_details={repr(coin_details)} type={type(coin_details)}")
                if coin_details.get("status") != "success":
                    print(f"Naomi: Yikes! Something went wrong getting data for {symbol.upper()}. Try again in a moment! 😅")
                    continue
                
                # Step 3: Build the data summary
                coin_name = coin_details.get("coin_id", symbol.upper())
                current_price = coin_details.get("current_price", "N/A")
                market_cap = coin_details.get("market_cap", "N/A")
                price_change_24h = coin_details.get("price_change_24h", "N/A")
                price_change_7d = coin_details.get("price_change_7d", "N/A")
                chain = coin_details.get("chain", "Unknown")
                is_native = coin_details.get("is_native_asset", False)
                contract_address = coin_details.get("contract_address")
                data_summary = f"{coin_name.upper()} - Price: ${current_price}, 24h: {price_change_24h}%, 7d: {price_change_7d}%, Market Cap: ${market_cap}, Chain: {chain}"
                
                # Step 4: Get comprehensive data for synthesis
                additional_data = []
                smart_money_data = None
                social_data = None
                
                print(f"🔗 Getting smart money analytics...")
                if is_native:
                    if chain and chain.lower() != "unknown":
                        smart_money_data = safe_tool_result(get_native_asset_smart_money_flow(chain), "Smart money data unavailable.")
                        print(f"DEBUG: smart_money_data={repr(smart_money_data)} type={type(smart_money_data)}")
                        if smart_money_data.get("status") == "error":
                            error_msg = smart_money_data.get("result", "")
                            if "not supported for native asset" in error_msg:
                                print(f"⚠️ Smart money flow not available for {symbol.upper()} on {chain}, using alternative data")
                                smart_money_data = {
                                    "status": "success",
                                    "result": f"Smart money flow data not available for {symbol.upper()} on {chain}. Consider checking price action and volume patterns instead.",
                                    "fallback": True
                                }
                            else:
                                print(f"⚠️ Smart money flow error for {symbol.upper()}, using fallback method")
                                smart_money_data = safe_tool_result(get_smart_money_flow(symbol), "Smart money data unavailable.")
                                print(f"DEBUG: fallback smart_money_data={repr(smart_money_data)} type={type(smart_money_data)}")
                        if smart_money_data.get("fallback") and smart_money_data.get("analytics_type") == "alternative_native_asset":
                            print(f"📊 Using alternative analytics for {symbol.upper()} on {chain}")
                            if smart_money_data.get("alternative_suggestions"):
                                suggestions = smart_money_data["alternative_suggestions"]
                                smart_money_data["result"] += f"\n\nAlternative analysis suggestions:\n" + "\n".join([f"• {suggestion}" for suggestion in suggestions])
                    else:
                        print(f"⚠️ Chain information unavailable for {symbol.upper()}, using fallback method")
                        smart_money_data = safe_tool_result(get_smart_money_flow(symbol), "Smart money data unavailable.")
                        print(f"DEBUG: fallback smart_money_data={repr(smart_money_data)} type={type(smart_money_data)}")
                else:
                    if chain and chain.lower() != "unknown" and contract_address:
                        smart_money_data = safe_tool_result(get_token_smart_money_flow(chain, contract_address), "Smart money data unavailable.")
                        print(f"DEBUG: smart_money_data={repr(smart_money_data)} type={type(smart_money_data)}")
                    else:
                        print(f"⚠️ Chain or contract address unavailable for {symbol.upper()}, using fallback method")
                        smart_money_data = safe_tool_result(get_smart_money_flow(symbol), "Smart money data unavailable.")
                        print(f"DEBUG: fallback smart_money_data={repr(smart_money_data)} type={type(smart_money_data)}")

                # Always display the smart money analytics summary if available
                if smart_money_data and 'result' in smart_money_data:
                    print("\nSmart Money Analytics:")
                    print(smart_money_data['result'])
                    additional_data.append(f"Smart Money Analytics:\n{smart_money_data['result']}")

                # Enhanced Trading Pattern Analysis (if trading_patterns is error and flows are available)
                def format_trading_pattern_analysis(smart_money_data):
                    flows = smart_money_data.get('flows') if isinstance(smart_money_data, dict) else None
                    if not flows:
                        return None
                    analysis_lines = []
                    for tf in ['24h', '7d']:
                        flow = flows.get(tf)
                        if not flow or flow.get('status') != 'success' or 'raw' not in flow:
                            continue
                        raw = flow['raw']
                        analysis_lines.append(f"\n{tf.upper()}:")
                        whale_flow = raw.get('whaleFlow', 0)
                        whale_wallets = raw.get('whaleWallets', 'N/A')
                        smart_trader_flow = raw.get('smartTraderFlow', 0)
                        smart_trader_wallets = raw.get('smartTraderWallets', 'N/A')
                        top_pnl_flow = raw.get('topPnlFlow', 0)
                        top_pnl_wallets = raw.get('topPnlWallets', 'N/A')
                        exchange_flow = raw.get('exchangeFlow', 0)
                        public_figure_flow = raw.get('publicFigureFlow', 0)
                        public_figure_wallets = raw.get('publicFigureWallets', 'N/A')
                        analysis_lines.append(f"  • Whale Flow: ${whale_flow:,.2f} ({whale_wallets} wallets)")
                        analysis_lines.append(f"  • Smart Trader Flow: ${smart_trader_flow:,.2f} ({smart_trader_wallets} wallets)")
                        analysis_lines.append(f"  • Top PnL Flow: ${top_pnl_flow:,.2f} ({top_pnl_wallets} wallets)")
                        analysis_lines.append(f"  • Exchange Flow: ${exchange_flow:,.2f}")
                        analysis_lines.append(f"  • Public Figure Flow: ${public_figure_flow:,.2f} ({public_figure_wallets} wallets)")
                    if not analysis_lines:
                        return None
                    # Simple interpretation
                    interpretation = []
                    if flows.get('24h', {}).get('raw', {}).get('whaleFlow', 0) > 0 and flows.get('7d', {}).get('raw', {}).get('whaleFlow', 0) > 0:
                        interpretation.append("Whales are accumulating across both 24h and 7d.")
                    if flows.get('24h', {}).get('raw', {}).get('topPnlFlow', 0) < 0:
                        interpretation.append("Top PnL wallets are taking profits in the last 24h.")
                    if flows.get('24h', {}).get('raw', {}).get('exchangeFlow', 0) < 0:
                        interpretation.append("Large outflows from exchanges (bullish sign).")
                    if not interpretation:
                        interpretation.append("No strong trading pattern detected from available data.")
                    analysis_lines.append("\nPattern Summary: " + " ".join(interpretation))
                    return "Trading Pattern Analysis (Nansen Data):\n" + "\n".join(analysis_lines)

                # If trading_patterns is error, add enhanced analysis
                if smart_money_data and isinstance(smart_money_data, dict):
                    trading_patterns = smart_money_data.get('trading_patterns')
                    if trading_patterns and trading_patterns.get('status') == 'error':
                        pattern_analysis = format_trading_pattern_analysis(smart_money_data)
                        if pattern_analysis:
                            additional_data.append(pattern_analysis)

                print(f"📱 Getting social sentiment...")
                social_data = safe_tool_result(get_social_sentiment(symbol, coin_name=coin_name), "No social sentiment data available.")
                print(f"DEBUG: social_data={repr(social_data)} type={type(social_data)}")
                if not isinstance(social_data, dict):
                    logger.error(f"social_data is not a dict: {repr(social_data)}")
                    social_data = {"status": "error", "result": "No social sentiment data available."}
                if social_data.get("status") == "success":
                    additional_data.append(f"Social Sentiment: {social_data['summary']}")
                else:
                    if social_data.get("status") == "error":
                        error_msg = social_data.get("result", "")
                        if "API key missing" in error_msg:
                            additional_data.append("Social Sentiment: Twitter API key required - add TWITTER_BEARER_TOKEN to .env")
                        else:
                            additional_data.append(f"Social Sentiment: {error_msg}")
                    else:
                        additional_data.append("Social Sentiment: Data unavailable")
                
                if intent == "PERFORMANCE" and timeframe:
                    print(f"📈 Getting {timeframe} performance data...")
                    perf_data = safe_tool_result(get_historical_performance(coin_id, timeframe), "Performance data unavailable.")
                    print(f"DEBUG: perf_data={repr(perf_data)} type={type(perf_data)}")
                    if perf_data.get("status") == "success":
                        additional_data.append(f"Performance ({timeframe}): {perf_data.get('result', 'N/A')}")
                    else:
                        additional_data.append(f"Performance data unavailable: {perf_data.get('result', 'Error')}")
                
                # Step 5: Create comprehensive synthesis
                all_data = [data_summary] + additional_data
                data_text = "\n".join(all_data)
                
                # Generate visual charts
                price_data = {
                    "price_change_24h": price_change_24h,
                    "price_change_7d": price_change_7d
                }
                charts = generate_simple_charts(
                    price_data,
                    smart_money_data,
                    social_data['summary'] if isinstance(social_data, dict) and social_data.get('status') == 'success' else None
                )
                
                # Enhanced prompt with comprehensive data
                if intent == "PRICE":
                    prompt = f"User asked about {symbol.upper()} price. Here's the comprehensive data:\n{data_text}\n\nAnalyze the price movements, smart money flows, and social sentiment. Correlate these factors and provide insights in Naomi's confident, witty Gen Z style."
                elif intent == "PERFORMANCE":
                    prompt = f"User asked about {symbol.upper()} performance. Here's the comprehensive data:\n{data_text}\n\nAnalyze the performance trends, smart money behavior, and market sentiment. Provide performance insights in Naomi's style."
                elif intent == "ONCHAIN":
                    prompt = f"User asked about {symbol.upper()} on-chain data. Here's the comprehensive data:\n{data_text}\n\nFocus on smart money flows, trader behavior, and on-chain signals. Provide smart money insights in Naomi's style."
                elif intent == "SOCIAL":
                    prompt = f"User asked about {symbol.upper()} social sentiment. Here's the comprehensive data:\n{data_text}\n\nAnalyze social sentiment, smart money correlation, and market psychology. Provide social analysis in Naomi's style."
                else:
                    prompt = f"User asked about {symbol.upper()}. Here's the comprehensive data:\n{data_text}\n\nProvide a complete analysis including:\n1. Price analysis and market context\n2. Smart money flow interpretation\n3. Social sentiment correlation\n4. Overall market positioning and recommendations\n\nRespond in Naomi's confident, witty Gen Z style with actionable insights."
                
                # Generate response using Grok
                messages = [
                    {"role": "system", "content": NAOMI_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ]
                
                try:
                    response = grok_model.chat_completion(messages)
                    if isinstance(response, dict) and "choices" in response and response["choices"]:
                        content = response["choices"][0]["message"]["content"]
                        if content and len(content.strip()) > 10:
                            print(content)
                            print(f"\n{charts}")  # Display charts after the analysis
                            if smart_money_data and 'result' in smart_money_data:
                                print("\nSmart Money Analytics:")
                                print(smart_money_data['result'])
                            # Print cited tweets if available
                            cited_tweets = social_data.get('cited_tweets') if isinstance(social_data, dict) else None
                            if isinstance(cited_tweets, list):
                                print("\nMost Impactful Tweets:")
                                for t in cited_tweets:
                                    print(f"- [{t.get('sentiment', '').capitalize()} | Engagement: {t.get('engagement', 0)}] {t.get('url', '')}")
                            else:
                                logger.error(f"cited_tweets is not a list or missing: {repr(cited_tweets)} (social_data: {repr(social_data)})")
                            conversation.append({"role": "user", "content": user_input})
                            conversation.append({"role": "assistant", "content": content})
                        else:
                            # Fallback response
                            print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                            print(f"\n{charts}")
                            # Print smart money analytics summary
                            if smart_money_data and 'result' in smart_money_data:
                                print("\nSmart Money Analytics:")
                                print(smart_money_data['result'])
                            cited_tweets = social_data.get('cited_tweets') if isinstance(social_data, dict) else None
                            if isinstance(cited_tweets, list):
                                print("\nMost Impactful Tweets:")
                                for t in cited_tweets:
                                    print(f"- [{t.get('sentiment', '').capitalize()} | Engagement: {t.get('engagement', 0)}] {t.get('url', '')}")
                            else:
                                logger.error(f"cited_tweets is not a list or missing: {repr(cited_tweets)} (social_data: {repr(social_data)})")
                            conversation.append({"role": "user", "content": user_input})
                            conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
                    else:
                        # Fallback response
                        print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                        print(f"\n{charts}")
                        # Print smart money analytics summary
                        if smart_money_data and 'result' in smart_money_data:
                            print("\nSmart Money Analytics:")
                            print(smart_money_data['result'])
                        cited_tweets = social_data.get('cited_tweets') if isinstance(social_data, dict) else None
                        if isinstance(cited_tweets, list):
                            print("\nMost Impactful Tweets:")
                            for t in cited_tweets:
                                print(f"- [{t.get('sentiment', '').capitalize()} | Engagement: {t.get('engagement', 0)}] {t.get('url', '')}")
                        else:
                            logger.error(f"cited_tweets is not a list or missing: {repr(cited_tweets)} (social_data: {repr(social_data)})")
                        conversation.append({"role": "user", "content": user_input})
                        conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
                except TimeoutError as e:
                    print("Naomi: Grok is taking too long to respond (timeout). Let me give you the data directly!")
                    print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                    print(f"\n{charts}")
                    # Print smart money analytics summary
                    if smart_money_data and 'result' in smart_money_data:
                        print("\nSmart Money Analytics:")
                        print(smart_money_data['result'])
                    cited_tweets = social_data.get('cited_tweets') if isinstance(social_data, dict) else None
                    if isinstance(cited_tweets, list):
                        print("\nMost Impactful Tweets:")
                        for t in cited_tweets:
                            print(f"- [{t.get('sentiment', '').capitalize()} | Engagement: {t.get('engagement', 0)}] {t.get('url', '')}")
                    else:
                        logger.error(f"cited_tweets is not a list or missing: {repr(cited_tweets)} (social_data: {repr(social_data)})")
                    conversation.append({"role": "user", "content": user_input})
                    conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
                except ConnectionError as e:
                    print("Naomi: Can't connect to Grok right now (network issue). Here's what I found:")
                    print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                    print(f"\n{charts}")
                    # Print smart money analytics summary
                    if smart_money_data and 'result' in smart_money_data:
                        print("\nSmart Money Analytics:")
                        print(smart_money_data['result'])
                    cited_tweets = social_data.get('cited_tweets') if isinstance(social_data, dict) else None
                    if isinstance(cited_tweets, list):
                        print("\nMost Impactful Tweets:")
                        for t in cited_tweets:
                            print(f"- [{t.get('sentiment', '').capitalize()} | Engagement: {t.get('engagement', 0)}] {t.get('url', '')}")
                    else:
                        logger.error(f"cited_tweets is not a list or missing: {repr(cited_tweets)} (social_data: {repr(social_data)})")
                    conversation.append({"role": "user", "content": user_input})
                    conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
                except (ValueError, KeyError) as e:
                    print(f"Naomi: Got some weird data from Grok: {str(e)}. Here's what I found:")
                    print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                    print(f"\n{charts}")
                    # Print smart money analytics summary
                    if smart_money_data and 'result' in smart_money_data:
                        print("\nSmart Money Analytics:")
                        print(smart_money_data['result'])
                    cited_tweets = social_data.get('cited_tweets') if isinstance(social_data, dict) else None
                    if isinstance(cited_tweets, list):
                        print("\nMost Impactful Tweets:")
                        for t in cited_tweets:
                            print(f"- [{t.get('sentiment', '').capitalize()} | Engagement: {t.get('engagement', 0)}] {t.get('url', '')}")
                    else:
                        logger.error(f"cited_tweets is not a list or missing: {repr(cited_tweets)} (social_data: {repr(social_data)})")
                    conversation.append({"role": "user", "content": user_input})
                    conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
                except Exception as e:
                    print(f"Naomi: Unexpected error with Grok: {str(e)}. Here's what I found:")
                    print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                    print(f"\n{charts}")
                    # Print smart money analytics summary
                    if smart_money_data and 'result' in smart_money_data:
                        print("\nSmart Money Analytics:")
                        print(smart_money_data['result'])
                    cited_tweets = social_data.get('cited_tweets') if isinstance(social_data, dict) else None
                    if isinstance(cited_tweets, list):
                        print("\nMost Impactful Tweets:")
                        for t in cited_tweets:
                            print(f"- [{t.get('sentiment', '').capitalize()} | Engagement: {t.get('engagement', 0)}] {t.get('url', '')}")
                    else:
                        logger.error(f"cited_tweets is not a list or missing: {repr(cited_tweets)} (social_data: {repr(social_data)})")
                    conversation.append({"role": "user", "content": user_input})
                    conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
                
                # Limit conversation history
                if len(conversation) > 10:
                    conversation = conversation[-10:]
                    
                continue # Continue to the next iteration of the while loop
            if not pairs:
                print("Naomi: Hey! What crypto are you asking about? Try something like 'price of bitcoin' or 'how is ethereum doing'? 🤔")
                continue
            # Focused, modular response for all other queries
            response = build_focused_response(pairs, investment_advice_requested=investment_advice_requested)
            print(response)
            conversation.append({"role": "user", "content": user_input})
            conversation.append({"role": "assistant", "content": response})
        except KeyboardInterrupt:
            print("\n\nNaomi: Oops, looks like you're in a hurry! Catch you later!")
            break
        except EOFError:
            print("\n\nNaomi: Input stream ended. See you later!")
            break
        except (ValueError, TypeError) as e:
            logger.error(f"Data type error in main loop: {e}")
            print(f"\nNaomi: Oops, got some weird data: {str(e)}")
            print("Let's try that again with a different approach!")
        except (KeyError, AttributeError) as e:
            logger.error(f"Data structure error in main loop: {e}")
            print(f"\nNaomi: Data structure issue: {str(e)}")
            print("Let's try that again!")
        except (OSError, IOError) as e:
            logger.error(f"System error in main loop: {e}")
            print(f"\nNaomi: System error: {str(e)}")
            print("Please check your system and try again!")
        except ImportError as e:
            logger.error(f"Import error in main loop: {e}")
            print(f"\nNaomi: Missing dependency: {str(e)}")
            print("Please check your installation and try again!")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            print(f"\nNaomi: Unexpected error occurred: {str(e)}")
            print("This is unusual! Please try again or contact support if it persists.")
            print(f"Error type: {type(e).__name__}")
            # Log the full error for debugging (in production, this would go to a log file)
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            print(f"Debug info: {traceback.format_exc()}")

if __name__ == "__main__":
    main() 