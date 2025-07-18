#!/usr/bin/env python3
"""
Naomi - Crypto Assistant powered by xAI Grok and AWS Strands
Replicated from Google ADK crypto bot functionality
"""

import os
import re
import difflib
from dotenv import load_dotenv
from strands import Agent
from grok_model import GrokModel
from coingecko_tool import search_coin_id, get_coin_details, get_historical_performance
from nansen_tool import get_onchain_analytics, get_smart_money_flow, get_whale_movements, get_native_asset_smart_money_flow, get_token_smart_money_flow
from twitter_tool import get_social_sentiment, get_trending_hashtags, get_influencer_mentions
from conversation_tool import handle_conversation

# Load environment variables
load_dotenv()

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
PROHIBITED_KEYWORDS = [
    # Explicit/sexual coins
    "sexcoin", "titcoin", "porncoin", "clitcoin", "analcoin", "dickcoin", "pussycoin", "cumrocket", "cumcoin", "asscoin", "fapcoin", "boobcoin", "vaginacoin", "milfcoin", "hustlercoin", "xxxcoin", "porn", "sex", "rape", "child", "pedo", "incest", "loli", "lolita", "cp", "nsfw", "explicit", "nude", "nudes", "escort", "prostitute", "prostitution",
    # Hate/racism
    "nazi", "hitler", "kkk", "white power", "heil", "racist", "slur", "lynch", "genocide", "holocaust", "antisemitic", "antiblack", "antigay", "homophobic", "transphobic", "islamophobic", "jewish slur", "hate crime",
    # Violence/illegal
    "terror", "terrorist", "bomb", "shoot", "murder", "kill", "assassinate", "massacre", "school shooting", "gun violence", "drug", "cocaine", "heroin", "meth", "fentanyl", "scam", "fraud", "hack", "exploit", "phishing", "malware", "ransomware", "darkweb", "dark web", "illegal", "counterfeit", "money laundering", "launder", "traffick", "human trafficking", "organ trafficking"
]

PROHIBITED_REGEX = [
    r"child\s*(porn|sex|abuse|exploitation|molest|loli|lolita|cp)",
    r"\bsex\b.*coin", r"\btit\b.*coin", r"\bporn\b.*coin", r"\bboob\b.*coin", r"\bdick\b.*coin", r"\bass\b.*coin", r"\bcum\b.*coin", r"\bclit\b.*coin", r"\bpussy\b.*coin",
    r"\b(nazi|hitler|kkk|white power|heil|racist|slur|lynch|genocide|holocaust|antisemitic|antiblack|antigay|homophobic|transphobic|islamophobic|hate crime)\b",
    r"\b(terror|terrorist|bomb|shoot|murder|kill|assassinate|massacre|school shooting|gun violence)\b",
    r"\b(cocaine|heroin|meth|fentanyl)\b",
    r"\b(scam|fraud|hack|exploit|phishing|malware|ransomware)\b",
    r"\b(darkweb|dark web|illegal|counterfeit|money laundering|launder|traffick|human trafficking|organ trafficking)\b"
]

FUZZY_THRESHOLD = 0.85
AMBIGUOUS_KEYWORDS = ["controversial", "taboo", "offensive", "inappropriate", "nsfw", "illegal", "banned", "forbidden", "unethical", "problematic", "hate", "racist", "sex", "explicit", "adult"]

APOLOGY_BANNER = "We're sorry, but we cannot assist with that request as it violates our content safety policies. Please try a different question related to cryptocurrency or blockchain technology."
CLARIFY_BANNER = "Could you please clarify your question? I'm here to help with crypto-related topics!"

# Track repeated violations
violation_count = 0

def is_prohibited_content(user_input):
    """Advanced prohibited content detection with crypto context awareness."""
    text = user_input.lower()
    
    # Check if this is a legitimate crypto query first
    crypto_indicators = [
        "price", "market", "cap", "volume", "change", "performance", "chart", "token", "coin", "crypto", "blockchain", "defi", "nft", "mining", "staking", "yield", "liquidity", "swap", "trade", "buy", "sell", "hodl", "moon", "pump", "dump", "bull", "bear", "altcoin", "meme", "utility", "use case", "adoption", "partnership", "development", "roadmap", "whitepaper", "tokenomics", "circulating", "supply", "burn", "mint", "governance", "dao", "smart contract", "gas", "fee", "transaction", "wallet", "exchange", "dex", "cex", "amm", "liquidity pool", "yield farming", "lending", "borrowing", "collateral", "oracle", "bridge", "layer", "scaling", "consensus", "proof", "validator", "node", "network", "protocol", "dapp", "web3", "metaverse", "gamefi", "play to earn", "move to earn", "learn to earn", "socialfi", "creator economy", "royalties", "fractional", "synthetic", "derivative", "futures", "options", "perpetual", "leverage", "margin", "short", "long", "hedge", "arbitrage", "front running", "mev", "sandwich", "flash loan", "reentrancy", "rug pull", "honeypot", "scam", "legitimate", "audit", "security", "vulnerability", "exploit", "hack", "theft", "recovery", "insurance", "regulation", "compliance", "kyc", "aml", "tax", "reporting", "legal", "illegal", "banned", "restricted", "geoblocked", "vpn", "privacy", "anonymous", "pseudonymous", "transparent", "immutable", "decentralized", "centralized", "permissionless", "permissioned", "public", "private", "consortium", "hybrid", "sidechain", "rollup", "sharding", "fork", "upgrade", "hard fork", "soft fork", "backward compatible", "breaking change", "migration", "airdrop", "claim", "vesting", "lockup", "unlock", "release", "distribution", "allocation", "team", "foundation", "treasury", "reserve", "backing", "collateralized", "algorithmic", "stablecoin", "pegged", "floating", "volatile", "correlation", "beta", "alpha", "sharpe ratio", "risk", "reward", "volatility", "liquidity", "depth", "spread", "slippage", "impact", "market maker", "order book", "limit order", "market order", "stop loss", "take profit", "dca", "hodl", "diamond hands", "paper hands", "fomo", "fud", "shill", "moonboy", "maxi", "fanboy", "hater", "skeptic", "believer", "adopter", "early", "late", "fomo", "fud", "shill", "moonboy", "maxi", "fanboy", "hater", "skeptic", "believer", "adopter", "early", "late", "whale", "shark", "minnow", "dolphin", "octopus", "squid", "ape", "diamond", "paper", "rocket", "moon", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "galaxy", "universe", "cosmos", "polkadot", "cardano", "solana", "avalanche", "polygon", "binance", "coinbase", "kraken", "kucoin", "okx", "bybit", "huobi", "gate", "mexc", "bitget", "whitebit", "bitfinex", "gemini", "ftx", "celsius", "voyager", "blockfi", "nexo", "crypto.com", "robinhood", "webull", "etoro", "tradingview", "coingecko", "coinmarketcap", "messari", "glassnode", "santiment", "lunar", "intotheblock", "skew", "deribit", "okex", "bitmex"
    ]
    
    # If the query contains crypto-related terms, be more lenient
    has_crypto_context = any(indicator in text for indicator in crypto_indicators)
    
    # Direct keyword match (but be more careful with crypto context)
    for word in PROHIBITED_KEYWORDS:
        if word in text:
            # If it's a crypto context, check if it's part of a legitimate crypto term
            if has_crypto_context:
                # Skip if it's likely a legitimate crypto term
                if word in ["hack", "scam", "fraud", "exploit"] and any(crypto_term in text for crypto_term in ["security", "audit", "vulnerability", "protection", "prevention", "detection", "analysis", "report", "news", "alert", "warning", "risk", "safety"]):
                    continue
            return True
    
    # Regex match (but be more careful with crypto context)
    for pattern in PROHIBITED_REGEX:
        if re.search(pattern, text):
            # If it's a crypto context, check if it's part of a legitimate crypto term
            if has_crypto_context:
                # Skip if it's likely a legitimate crypto term
                if "hack" in pattern and any(crypto_term in text for crypto_term in ["security", "audit", "vulnerability", "protection", "prevention", "detection", "analysis", "report", "news", "alert", "warning", "risk", "safety"]):
                    continue
            return True
    
    # Fuzzy match for misspellings (but be more careful with crypto context)
    for word in PROHIBITED_KEYWORDS:
        for w in text.split():
            if difflib.SequenceMatcher(None, word, w).ratio() > FUZZY_THRESHOLD:
                # If it's a crypto context, check if it's part of a legitimate crypto term
                if has_crypto_context:
                    # Skip if it's likely a legitimate crypto term
                    if word in ["hack", "scam", "fraud", "exploit"] and any(crypto_term in text for crypto_term in ["security", "audit", "vulnerability", "protection", "prevention", "detection", "analysis", "report", "news", "alert", "warning", "risk", "safety"]):
                        continue
                return True
    
    return False

def is_ambiguous_content(user_input):
    """Check for ambiguous content that needs clarification."""
    text = user_input.lower()
    for word in AMBIGUOUS_KEYWORDS:
        if word in text:
            return True
    return False

def classify_intent(user_input: str) -> dict:
    """
    Classifies the user's intent and extracts coin name/symbol and timeframe if present.
    Returns a dict with keys: intent, coin_query, timeframe
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
    onchain_patterns = [r"whale", r"smart money", r"on.?chain", r"flow", r"wallet", r"transfer", r"movement", r"working", r"playing"]
    
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
            r"(\w+)\s+(?:smart\s+money|whale|flow)",  # "bitcoin smart money", "eth whale"
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
    Generate simple ASCII/emoji-based charts for visual representation.
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
        except:
            pass
    
    # Smart money flow chart
    if smart_money_data and "data" in smart_money_data:
        charts.append("💰 Smart Money Flow:")
        for timeframe in ["24h", "7d", "30d"]:
            if timeframe in smart_money_data["data"] and smart_money_data["data"][timeframe]["status"] == "success":
                flow = smart_money_data["data"][timeframe]["netflow_usd"]
                flow_str = smart_money_data["data"][timeframe]["flow_str"]
                trader_count = smart_money_data["data"][timeframe].get("trader_count", "N/A")
                
                if flow > 0:
                    charts.append(f"{timeframe}: 🟢 {flow_str} ({trader_count} traders)")
                elif flow < 0:
                    charts.append(f"{timeframe}: 🔴 {flow_str} ({trader_count} traders)")
                else:
                    charts.append(f"{timeframe}: ⚪ {flow_str} ({trader_count} traders)")
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

def main():
    """Main function that orchestrates the crypto analysis workflow."""
    global violation_count
    grok_api_key = os.getenv("GROK_API_KEY")
    if not grok_api_key:
        print("❌ GROK_API_KEY not found in environment variables")
        return
    
    grok_model = GrokModel(
        client_args={"api_key": grok_api_key},
        model_id="grok-3",
        params={"max_tokens": 1000, "temperature": 0.7}
    )
    
    print("\n🟣 Naomi Crypto Assistant (Strands+Grok4) 🟣\n")
    print("Ask me anything about crypto, blockchain, or NFTs!")
    print("Type 'exit' to quit.")
    conversation = []
    
    while True:
        try:
            user_input = input("\n> ")
            if user_input.lower() == "exit":
                print("\nNaomi: Later, legend! Keep those crypto vibes flowing! ")
                break
                
            # Content safety filtering
            if is_prohibited_content(user_input):
                violation_count += 1
                print(APOLOGY_BANNER)
                if violation_count >= 2:
                    print("If you need help, try asking about Bitcoin, Ethereum, or DeFi trends!")
                continue
            elif is_ambiguous_content(user_input):
                print(CLARIFY_BANNER)
                continue
            else:
                violation_count = 0
                
            # Classify intent and extract info
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
            
            if not coin_id:
                print(f"Naomi: Oops! I couldn't find {symbol.upper()} on CoinGecko. Maybe try a different spelling or check if it's listed? 🤷‍♀️")
                continue
            
            # Step 2: Get detailed coin information
            print(f"📊 Getting data for {symbol.upper()}...")
            coin_details = get_coin_details(coin_id)
            
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
            
            # Format the basic data summary
            data_summary = f"{coin_name.upper()} - Price: ${current_price}, 24h: {price_change_24h}%, 7d: {price_change_7d}%, Market Cap: ${market_cap}, Chain: {chain}"
            
            # Step 4: Get comprehensive data for synthesis
            additional_data = []
            smart_money_data = None
            social_data = None
            
            # Always get smart money flow data for comprehensive analysis
            print(f"🔗 Getting smart money analytics...")
            if is_native:
                # For native assets, use the chain name
                smart_money_data = get_native_asset_smart_money_flow(chain)
            else:
                # For tokens, use the contract address
                if chain and contract_address:
                    smart_money_data = get_token_smart_money_flow(chain, contract_address)
                else:
                    smart_money_data = get_smart_money_flow(symbol)
            
            if smart_money_data and smart_money_data.get("status") == "success":
                if "data" in smart_money_data:
                    # Enhanced smart money data with multiple timeframes
                    smart_money_summary = smart_money_data.get("summary", "Smart money data available")
                    smart_money_analysis = smart_money_data.get("analysis", {})
                    additional_data.append(f"Smart Money Flow: {smart_money_summary}")
                    if smart_money_analysis.get("recommendation"):
                        additional_data.append(f"Smart Money Signal: {smart_money_analysis['recommendation']}")
                else:
                    # Legacy smart money data
                    additional_data.append(f"Smart Money Flow: {smart_money_data.get('result', 'N/A')}")
            else:
                additional_data.append("Smart Money Flow: Data unavailable")
            
            # Always get social sentiment for comprehensive analysis
            print(f"📱 Getting social sentiment...")
            social_data = get_social_sentiment(symbol, coin_name=coin_name)
            if social_data and social_data.get("status") == "success":
                additional_data.append(f"Social Sentiment: {social_data['summary']}")
            else:
                additional_data.append("Social Sentiment: Data unavailable")
            
            # Get additional data based on specific intent
            if intent == "PERFORMANCE" and timeframe:
                print(f"📈 Getting {timeframe} performance data...")
                perf_data = get_historical_performance(coin_id, timeframe)
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
            charts = generate_simple_charts(price_data, smart_money_data, social_data['summary'] if social_data and social_data.get('status') == 'success' else None)
            
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
                        # Print cited tweets if available
                        if social_data and social_data.get('status') == 'success' and social_data.get('cited_tweets'):
                            print("\nMost Impactful Tweets:")
                            for t in social_data['cited_tweets']:
                                print(f"- [{t['sentiment'].capitalize()} | Engagement: {t['engagement']}] {t['url']}")
                        conversation.append({"role": "user", "content": user_input})
                        conversation.append({"role": "assistant", "content": content})
                    else:
                        # Fallback response
                        print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                        print(f"\n{charts}")
                        if social_data and social_data.get('status') == 'success' and social_data.get('cited_tweets'):
                            print("\nMost Impactful Tweets:")
                            for t in social_data['cited_tweets']:
                                print(f"- [{t['sentiment'].capitalize()} | Engagement: {t['engagement']}] {t['url']}")
                        conversation.append({"role": "user", "content": user_input})
                        conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
                else:
                    # Fallback response
                    print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                    print(f"\n{charts}")
                    if social_data and social_data.get('status') == 'success' and social_data.get('cited_tweets'):
                        print("\nMost Impactful Tweets:")
                        for t in social_data['cited_tweets']:
                            print(f"- [{t['sentiment'].capitalize()} | Engagement: {t['engagement']}] {t['url']}")
                    conversation.append({"role": "user", "content": user_input})
                    conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
            except Exception as e:
                print("Naomi: Sorry, my brain just lagged out (Grok-4 timeout or error). Try again in a moment!")
                # Fallback response
                print(f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀")
                print(f"\n{charts}")
                if social_data and social_data.get('status') == 'success' and social_data.get('cited_tweets'):
                    print("\nMost Impactful Tweets:")
                    for t in social_data['cited_tweets']:
                        print(f"- [{t['sentiment'].capitalize()} | Engagement: {t['engagement']}] {t['url']}")
                conversation.append({"role": "user", "content": user_input})
                conversation.append({"role": "assistant", "content": f"Naomi: {data_summary}"})
            
            # Limit conversation history
            if len(conversation) > 10:
                conversation = conversation[-10:]
                
        except KeyboardInterrupt:
            print("\n\nNaomi: Oops, looks like you're in a hurry! Catch you later!")
            break
        except Exception as e:
            print(f"\nNaomi: Yikes, something went sideways: {str(e)}")
            print("Let's try that again, shall we?")

if __name__ == "__main__":
    main() 