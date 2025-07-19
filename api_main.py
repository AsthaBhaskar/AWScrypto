#!/usr/bin/env python3
"""
Naomi Crypto Assistant API - FastAPI version
Exposes all crypto assistant functionalities through REST API endpoints

Required Environment Variables (.env file):
- GROK_API_KEY: Required - xAI Grok API key for AI responses
- COINGECKO_API_KEY: Optional - CoinGecko Pro API key (falls back to free tier)
- NANSEN_API_KEY: Optional - Nansen API key for smart money analytics
- TWITTER_BEARER_TOKEN: Optional - Twitter API v2 Bearer token for social sentiment
"""

import os
import re
import difflib
import logging
import time
import random
from typing import Optional, Dict, List, Any
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from grok_model import GrokModel
from coingecko_tool import search_coin_id, get_coin_details, get_historical_performance
from nansen_tool import get_onchain_analytics, get_smart_money_flow, get_native_asset_smart_money_flow, get_token_smart_money_flow
from twitter_tool import get_social_sentiment, get_trending_hashtags, get_influencer_mentions
from conversation_tool import handle_conversation

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Naomi Crypto Assistant API",
    description="Comprehensive crypto analysis API powered by xAI Grok and multiple data sources",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for request/response
class CoinSearchRequest(BaseModel):
    query: str = Field(..., description="Coin name or symbol to search for")

class CoinAnalysisRequest(BaseModel):
    symbol: str = Field(..., description="Coin symbol or name")
    intent: Optional[str] = Field("GENERAL", description="Analysis intent: PRICE, PERFORMANCE, ONCHAIN, SOCIAL, GENERAL")
    timeframe: Optional[str] = Field(None, description="Timeframe for analysis: 1h, 24h, 7d, 30d")

class ConversationRequest(BaseModel):
    message: str = Field(..., description="User message for conversation")
    context: Optional[List[Dict[str, str]]] = Field([], description="Previous conversation context")

class SmartMoneyRequest(BaseModel):
    chain: str = Field(..., description="Blockchain chain (ethereum, solana, etc.)")
    token_address: Optional[str] = Field(None, description="Token contract address (optional for native assets)")

class SocialSentimentRequest(BaseModel):
    symbol: str = Field(..., description="Coin symbol")
    coin_name: Optional[str] = Field(None, description="Full coin name")

class NetworkTestResponse(BaseModel):
    status: str
    results: Dict[str, Dict[str, Any]]

class CoinSearchResponse(BaseModel):
    status: str
    coin_id: Optional[str] = None
    message: Optional[str] = None

class CoinDetailsResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None

class AnalysisResponse(BaseModel):
    status: str
    analysis: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    charts: Optional[str] = None
    message: Optional[str] = None

class ConversationResponse(BaseModel):
    status: str
    response: str
    context: List[Dict[str, str]]

# Global variables
grok_model = None
violation_count = 0

# Content Safety Filtering (same as crypto_assistant.py)
PROHIBITED_KEYWORDS = [
    "sexcoin", "titcoin", "porncoin", "clitcoin", "analcoin", "dickcoin", "pussycoin", "cumrocket", "cumcoin", "asscoin", "fapcoin", "boobcoin", "vaginacoin", "milfcoin", "hustlercoin", "xxxcoin", "porn", "sex", "rape", "child", "pedo", "incest", "loli", "lolita", "cp", "nsfw", "explicit", "nude", "nudes", "escort", "prostitute", "prostitution",
    "nazi", "hitler", "kkk", "white power", "heil", "racist", "slur", "lynch", "genocide", "holocaust", "antisemitic", "antiblack", "antigay", "homophobic", "transphobic", "islamophobic", "jewish slur", "hate crime",
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

def is_prohibited_content(user_input):
    """Advanced prohibited content detection with crypto context awareness."""
    text = user_input.lower()
    
    # Check if this is a legitimate crypto query first
    crypto_indicators = [
        "price", "market", "cap", "volume", "change", "performance", "chart", "token", "coin", "crypto", "blockchain", "defi", "nft", "mining", "staking", "yield", "liquidity", "swap", "trade", "buy", "sell", "hodl", "moon", "pump", "dump", "bull", "bear", "altcoin", "meme", "utility", "use case", "adoption", "partnership", "development", "roadmap", "whitepaper", "tokenomics", "circulating", "supply", "burn", "mint", "governance", "dao", "smart contract", "gas", "fee", "transaction", "wallet", "exchange", "dex", "cex", "amm", "liquidity pool", "yield farming", "lending", "borrowing", "collateral", "oracle", "bridge", "layer", "scaling", "consensus", "proof", "validator", "node", "network", "protocol", "dapp", "web3", "metaverse", "gamefi", "play to earn", "move to earn", "learn to earn", "socialfi", "creator economy", "royalties", "fractional", "synthetic", "derivative", "futures", "options", "perpetual", "leverage", "margin", "short", "long", "hedge", "arbitrage", "front running", "mev", "sandwich", "flash loan", "reentrancy", "rug pull", "honeypot", "scam", "legitimate", "audit", "security", "vulnerability", "exploit", "hack", "theft", "recovery", "insurance", "regulation", "compliance", "kyc", "aml", "tax", "reporting", "legal", "illegal", "banned", "restricted", "geoblocked", "vpn", "privacy", "anonymous", "pseudonymous", "transparent", "immutable", "decentralized", "centralized", "permissionless", "permissioned", "public", "private", "consortium", "hybrid", "sidechain", "rollup", "sharding", "fork", "upgrade", "hard fork", "soft fork", "backward compatible", "breaking change", "migration", "airdrop", "claim", "vesting", "lockup", "unlock", "release", "distribution", "allocation", "team", "foundation", "treasury", "reserve", "backing", "collateralized", "algorithmic", "stablecoin", "pegged", "floating", "volatile", "correlation", "beta", "alpha", "sharpe ratio", "risk", "reward", "volatility", "liquidity", "depth", "spread", "slippage", "impact", "market maker", "order book", "limit order", "market order", "stop loss", "take profit", "dca", "hodl", "diamond hands", "paper hands", "fomo", "fud", "shill", "moonboy", "maxi", "fanboy", "hater", "skeptic", "believer", "adopter", "early", "late", "fomo", "fud", "shill", "moonboy", "maxi", "fanboy", "hater", "skeptic", "believer", "adopter", "early", "late", "shark", "minnow", "dolphin", "octopus", "squid", "ape", "diamond", "paper", "rocket", "moon", "mars", "jupiter", "saturn", "uranus", "neptune", "pluto", "galaxy", "universe", "cosmos", "polkadot", "cardano", "solana", "avalanche", "polygon", "binance", "coinbase", "kraken", "kucoin", "okx", "bybit", "huobi", "gate", "mexc", "bitget", "whitebit", "bitfinex", "gemini", "ftx", "celsius", "voyager", "blockfi", "nexo", "crypto.com", "robinhood", "webull", "etoro", "tradingview", "coingecko", "coinmarketcap", "messari", "glassnode", "santiment", "lunar", "intotheblock", "skew", "deribit", "okex", "bitmex"
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

def retry_api_call(func, max_retries=3, base_delay=1, max_delay=10, backoff_factor=2):
    """Retry utility for API calls with exponential backoff."""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries:
                raise e
            
            delay = min(base_delay * (backoff_factor ** attempt), max_delay)
            jitter = random.uniform(0, 0.1 * delay)
            total_delay = delay + jitter
            
            logger.debug(f"API call failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}")
            time.sleep(total_delay)
    
    return None

def check_network_connectivity():
    """Check basic network connectivity to help diagnose connection issues."""
    import requests
    
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

def generate_simple_charts(price_data, smart_money_data, social_sentiment):
    """Generate simple ASCII/emoji-based charts for visual representation."""
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
        except (ValueError, TypeError):
            charts.append("📈 Price Performance: Data unavailable")
            charts.append("")
    
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

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup."""
    global grok_model
    
    # Validate environment variables
    grok_api_key = os.getenv("GROK_API_KEY")
    if not grok_api_key:
        logger.error("GROK_API_KEY not found in environment variables")
        raise Exception("GROK_API_KEY not found in environment variables")
    
    # Check for other optional API keys
    coingecko_api_key = os.getenv("COINGECKO_API_KEY")
    nansen_api_key = os.getenv("NANSEN_API_KEY")
    twitter_api_key = os.getenv("TWITTER_BEARER_TOKEN")
    
    if not coingecko_api_key:
        logger.warning("COINGECKO_API_KEY not found - will use free tier with rate limits")
    if not nansen_api_key:
        logger.warning("NANSEN_API_KEY not found - smart money features will be limited")
    if not twitter_api_key:
        logger.warning("TWITTER_BEARER_TOKEN not found - social sentiment features will be limited")
    
    try:
        grok_model = GrokModel(
            client_args={"api_key": grok_api_key},
            model_id="grok-3",
            params={"max_tokens": 1000, "temperature": 0.7}
        )
        logger.info("Grok model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Grok model: {e}")
        raise e

# Health check endpoint
@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Naomi Crypto Assistant API is running"}

# Network connectivity test endpoint
@app.get("/network/test", response_model=NetworkTestResponse)
async def test_network_connectivity():
    """Test network connectivity to external APIs."""
    try:
        results = check_network_connectivity()
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        logger.error(f"Network test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Network test failed: {str(e)}")

# Coin search endpoint
@app.post("/coin/search", response_model=CoinSearchResponse)
async def search_coin(request: CoinSearchRequest):
    """Search for a coin ID on CoinGecko."""
    try:
        # Content safety check
        if is_prohibited_content(request.query):
            return {
                "status": "error",
                "message": "Content violates safety policies"
            }
        
        coin_id = search_coin_id(request.query)
        
        if not coin_id:
            return {
                "status": "error",
                "message": f"Coin '{request.query}' not found"
            }
        
        return {
            "status": "success",
            "coin_id": coin_id
        }
    except Exception as e:
        logger.error(f"Coin search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Coin search failed: {str(e)}")

# Coin details endpoint
@app.get("/coin/{coin_id}/details", response_model=CoinDetailsResponse)
async def get_coin_details_endpoint(coin_id: str):
    """Get detailed information about a coin."""
    try:
        # Validate coin_id format
        if not re.match(r'^[a-zA-Z0-9-]+$', coin_id):
            return {
                "status": "error",
                "message": "Invalid coin ID format"
            }
        
        details = get_coin_details(coin_id)
        
        if details.get("status") != "success":
            return {
                "status": "error",
                "message": details.get("result", "Failed to get coin details")
            }
        
        return {
            "status": "success",
            "data": details
        }
    except Exception as e:
        logger.error(f"Get coin details failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get coin details failed: {str(e)}")

# Historical performance endpoint
@app.get("/coin/{coin_id}/performance", response_model=Dict[str, Any])
async def get_historical_performance_endpoint(
    coin_id: str,
    timeframe: str = Query("all", description="Timeframe: 1h, 24h, 7d, 30d, all")
):
    """Get historical performance data for a coin."""
    try:
        # Validate coin_id format
        if not re.match(r'^[a-zA-Z0-9-]+$', coin_id):
            raise HTTPException(status_code=400, detail="Invalid coin ID format")
        
        performance = get_historical_performance(coin_id, timeframe)
        return performance
    except Exception as e:
        logger.error(f"Get historical performance failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get historical performance failed: {str(e)}")

# Smart money flow endpoint
@app.post("/smart-money/flow", response_model=Dict[str, Any])
async def get_smart_money_flow_endpoint(request: SmartMoneyRequest):
    """Get smart money flow data for a token or native asset."""
    try:
        if request.token_address:
            # Token smart money flow
            result = get_token_smart_money_flow(request.chain, request.token_address)
        else:
            # Native asset smart money flow
            result = get_native_asset_smart_money_flow(request.chain)
        
        return result
    except Exception as e:
        logger.error(f"Get smart money flow failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get smart money flow failed: {str(e)}")

# Social sentiment endpoint
@app.post("/social/sentiment", response_model=Dict[str, Any])
async def get_social_sentiment_endpoint(request: SocialSentimentRequest):
    """Get social sentiment analysis for a coin."""
    try:
        result = get_social_sentiment(request.symbol, coin_name=request.coin_name)
        return result
    except Exception as e:
        logger.error(f"Get social sentiment failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get social sentiment failed: {str(e)}")

# Trending hashtags endpoint
@app.get("/social/trending", response_model=Dict[str, Any])
async def get_trending_hashtags_endpoint():
    """Get trending crypto hashtags on Twitter."""
    try:
        result = get_trending_hashtags()
        return result
    except Exception as e:
        logger.error(f"Get trending hashtags failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get trending hashtags failed: {str(e)}")

# Influencer mentions endpoint
@app.get("/social/influencers", response_model=Dict[str, Any])
async def get_influencer_mentions_endpoint(
    symbol: str = Query(..., description="Coin symbol to search for")
):
    """Get influencer mentions for a coin."""
    try:
        result = get_influencer_mentions(symbol)
        return result
    except Exception as e:
        logger.error(f"Get influencer mentions failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get influencer mentions failed: {str(e)}")

# Conversation endpoint
@app.post("/conversation", response_model=ConversationResponse)
async def handle_conversation_endpoint(request: ConversationRequest):
    """Handle conversational queries with Naomi."""
    try:
        # Content safety check
        if is_prohibited_content(request.message):
            return {
                "status": "error",
                "response": "Content violates safety policies",
                "context": request.context
            }
        
        if is_ambiguous_content(request.message):
            return {
                "status": "error",
                "response": "Could you please clarify your question? I'm here to help with crypto-related topics!",
                "context": request.context
            }
        
        response = handle_conversation(request.message)
        
        # Update context
        new_context = request.context + [
            {"role": "user", "content": request.message},
            {"role": "assistant", "content": response}
        ]
        
        # Limit context length
        if len(new_context) > 10:
            new_context = new_context[-10:]
        
        return {
            "status": "success",
            "response": response,
            "context": new_context
        }
    except Exception as e:
        logger.error(f"Conversation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Conversation failed: {str(e)}")

# Comprehensive analysis endpoint
@app.post("/analysis", response_model=AnalysisResponse)
async def comprehensive_analysis(request: CoinAnalysisRequest):
    """Get comprehensive crypto analysis including price, smart money, and social sentiment."""
    try:
        # Content safety check
        if is_prohibited_content(request.symbol):
            return {
                "status": "error",
                "message": "Content violates safety policies"
            }
        
        # Step 1: Search for the coin
        coin_id = search_coin_id(request.symbol)
        if not coin_id:
            return {
                "status": "error",
                "message": f"Coin '{request.symbol}' not found"
            }
        
        # Step 2: Get coin details
        coin_details = get_coin_details(coin_id)
        if coin_details.get("status") != "success":
            return {
                "status": "error",
                "message": coin_details.get("result", "Failed to get coin details")
            }
        
        # Step 3: Extract data
        coin_name = coin_details.get("coin_id", request.symbol.upper())
        current_price = coin_details.get("current_price", "N/A")
        market_cap = coin_details.get("market_cap", "N/A")
        price_change_24h = coin_details.get("price_change_24h", "N/A")
        price_change_7d = coin_details.get("price_change_7d", "N/A")
        chain = coin_details.get("chain", "Unknown")
        is_native = coin_details.get("is_native_asset", False)
        contract_address = coin_details.get("contract_address")
        
        # Step 4: Get smart money data
        smart_money_data = None
        if is_native and chain and chain.lower() != "unknown":
            smart_money_data = get_native_asset_smart_money_flow(chain)
            if smart_money_data and smart_money_data.get("status") == "error":
                error_msg = smart_money_data.get("result", "")
                if "not supported for native asset" in error_msg:
                    smart_money_data = {
                        "status": "success",
                        "result": f"Smart money flow data not available for {request.symbol.upper()} on {chain}. Consider checking price action and volume patterns instead.",
                        "fallback": True
                    }
        elif chain and chain.lower() != "unknown" and contract_address:
            smart_money_data = get_token_smart_money_flow(chain, contract_address)
        else:
            smart_money_data = get_smart_money_flow(request.symbol)
        
        # Step 5: Get social sentiment
        social_data = get_social_sentiment(request.symbol, coin_name=coin_name)
        
        # Step 6: Build data summary
        data_summary = f"{coin_name.upper()} - Price: ${current_price}, 24h: {price_change_24h}%, 7d: {price_change_7d}%, Market Cap: ${market_cap}, Chain: {chain}"
        
        # Step 7: Generate analysis prompt
        intent = request.intent or "GENERAL"
        if intent == "PRICE":
            prompt = f"User asked about {request.symbol.upper()} price. Here's the comprehensive data:\n{data_summary}\n\nAnalyze the price movements, smart money flows, and social sentiment. Correlate these factors and provide insights in Naomi's confident, witty Gen Z style."
        elif intent == "PERFORMANCE":
            prompt = f"User asked about {request.symbol.upper()} performance. Here's the comprehensive data:\n{data_summary}\n\nAnalyze the performance trends, smart money behavior, and market sentiment. Provide performance insights in Naomi's style."
        elif intent == "ONCHAIN":
            prompt = f"User asked about {request.symbol.upper()} on-chain data. Here's the comprehensive data:\n{data_summary}\n\nFocus on smart money flows, trader behavior, and on-chain signals. Provide smart money insights in Naomi's style."
        elif intent == "SOCIAL":
            prompt = f"User asked about {request.symbol.upper()} social sentiment. Here's the comprehensive data:\n{data_summary}\n\nAnalyze social sentiment, smart money correlation, and market psychology. Provide social analysis in Naomi's style."
        else:
            prompt = f"User asked about {request.symbol.upper()}. Here's the comprehensive data:\n{data_summary}\n\nProvide a complete analysis including:\n1. Price analysis and market context\n2. Smart money flow interpretation\n3. Social sentiment correlation\n4. Overall market positioning and recommendations\n\nRespond in Naomi's confident, witty Gen Z style with actionable insights."
        
        # Step 8: Generate AI analysis
        messages = [
            {"role": "system", "content": NAOMI_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        response = grok_model.chat_completion(messages)
        if isinstance(response, dict) and "choices" in response and response["choices"]:
            content = response["choices"][0]["message"]["content"]
        else:
            content = f"Naomi: {data_summary} Pretty wild times in crypto, right? 🚀"
        
        # Step 9: Generate charts
        price_data = {
            "price_change_24h": price_change_24h,
            "price_change_7d": price_change_7d
        }
        charts = generate_simple_charts(price_data, smart_money_data, social_data.get('summary') if social_data and social_data.get('status') == 'success' else None)
        
        # Step 10: Prepare response data
        response_data = {
            "coin_details": coin_details,
            "smart_money_data": smart_money_data,
            "social_data": social_data,
            "analysis_intent": intent,
            "timeframe": request.timeframe
        }
        
        return {
            "status": "success",
            "analysis": content,
            "data": response_data,
            "charts": charts
        }
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Naomi Crypto Assistant API",
        "version": "1.0.0",
        "description": "Comprehensive crypto analysis API powered by xAI Grok and multiple data sources",
        "endpoints": {
            "health": "/health",
            "network_test": "/network/test",
            "coin_search": "/coin/search",
            "coin_details": "/coin/{coin_id}/details",
            "coin_performance": "/coin/{coin_id}/performance",
            "smart_money_flow": "/smart-money/flow",
            "social_sentiment": "/social/sentiment",
            "trending_hashtags": "/social/trending",
            "influencer_mentions": "/social/influencers",
            "conversation": "/conversation",
            "comprehensive_analysis": "/analysis"
        },
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8000
    port = int(os.getenv("PORT", 8000))
    
    # Run the FastAPI application
    uvicorn.run(
        "api_main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    ) 