import os
import requests
import json
from strands import tool
from dotenv import load_dotenv
from coingecko_tool import search_coin_id, get_coin_details

# Load environment variables
load_dotenv()

def get_token_address_from_coingecko(symbol: str) -> tuple:
    """
    Get the token contract address and chain from CoinGecko for a given symbol.
    
    Args:
        symbol: The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol')
        
    Returns:
        Tuple of (chain, token_address) or (None, None) if not found
    """
    try:
        # Get coin details from CoinGecko
        coin_id = search_coin_id(symbol)
        if not coin_id:
            return None, None
        
        coin_details = get_coin_details(coin_id)
        if coin_details.get("status") != "success":
            return None, None
        
        # Check if it's a native asset
        is_native = coin_details.get("is_native_asset", False)
        chain = coin_details.get("chain")
        contract_address = coin_details.get("contract_address")
        
        if is_native:
            # For native assets, use the chain name
            if chain:
                return chain, None
            else:
                return None, None
        else:
            # For tokens, use the contract address and chain
            if chain and contract_address:
                return chain, contract_address
            else:
                return None, None
                
    except Exception as e:
        print(f"[DEBUG] Error getting token address from CoinGecko: {e}")
        return None, None

# Nansen Tools
# ------------------------------------------------------------------------------
def _fetch_nansen_flow_intelligence(chain: str, token_address: str, timeframe: str = "1d") -> dict:
    """Helper to fetch and process smart money flow from Nansen using flow-intelligence for a given timeframe."""
    api_key = os.getenv("NANSEN_API_KEY")
    if not api_key:
        print("[DEBUG] Nansen API key is missing.")
        return {"status": "error", "result": "Nansen API key is missing."}

    url = "https://api.nansen.ai/api/beta/tgm/flow-intelligence"
    headers = {"apiKey": api_key, "Content-Type": "application/json"}
    
    payload = {
        "parameters": {
            "chain": chain.lower(),
            "tokenAddress": token_address,
            "timeframe": timeframe,
        }
    }

    print(f"[DEBUG] Fetching Nansen smart money flow for chain: {chain}, token_address: {token_address}, timeframe: {timeframe}")
    print(f"[DEBUG] Payload: {payload}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[DEBUG] Nansen API status code: {response.status_code}")
        print(f"[DEBUG] Nansen API raw response: {response.text}")
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list) or not data:
            print("[DEBUG] No recent smart money data was found.")
            return {"status": "success", "result": "No recent smart money data was found."}
        
        latest_entry = data[0]
        netflow_usd = float(latest_entry.get("smartTraderFlow") or 0)
        # Try to extract profitable trader/investor flows if available
        profitable_trader_flow = float(latest_entry.get("profitableTraderFlow") or 0) if "profitableTraderFlow" in latest_entry else None
        profitable_investor_flow = float(latest_entry.get("profitableInvestorFlow") or 0) if "profitableInvestorFlow" in latest_entry else None

        # Format the output string
        if abs(netflow_usd) >= 1_000_000:
            flow_str = f"${netflow_usd / 1_000_000:,.2f}M"
        elif abs(netflow_usd) >= 1_000:
            flow_str = f"${netflow_usd / 1_000:,.2f}K"
        else:
            flow_str = f"${netflow_usd:,.2f}"

        return {
            "status": "success",
            "result": flow_str,
            "raw": latest_entry,
            "netflow_usd": netflow_usd,
            "profitable_trader_flow": profitable_trader_flow,
            "profitable_investor_flow": profitable_investor_flow
        }

    except requests.exceptions.HTTPError as e:
        print(f"[DEBUG] Nansen API HTTP error: {e.response.status_code} - {e.response.text}")
        if e.response.status_code == 404:
            return {"status": "error", "result": "Unsupported chain or token for Nansen smart money flow."}
        return {"status": "error", "result": f"Nansen API returned an error: {e.response.status_code} - {e.response.text}"}
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Network error connecting to Nansen: {e}")
        return {"status": "error", "result": f"Network error connecting to Nansen: {e}"}

def _fetch_nansen_trading_patterns(chain: str, token_address: str) -> dict:
    """Fetch trading patterns for a token from Nansen (example endpoint, adjust as needed)."""
    api_key = os.getenv("NANSEN_API_KEY")
    if not api_key:
        return {"status": "error", "result": "Nansen API key is missing."}
    # This endpoint is illustrative; adjust to the actual Nansen endpoint for trading patterns
    url = f"https://api.nansen.ai/api/beta/tgm/trading-patterns"
    headers = {"apiKey": api_key, "Content-Type": "application/json"}
    payload = {
        "parameters": {
            "chain": chain.lower(),
            "tokenAddress": token_address,
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {"status": "success", "result": data}
    except Exception as e:
        return {"status": "error", "result": str(e)}

def get_smart_money_advice(netflow_usd, profitable_trader_flow, profitable_investor_flow):
    advice = []
    # Smart money
    if netflow_usd is not None:
        if netflow_usd > 0:
            advice.append("Smart money is accumulating (buying) this token.")
        elif netflow_usd < 0:
            advice.append("Smart money is distributing (selling) this token.")
        else:
            advice.append("No significant smart money movement detected.")
    # Profitable traders
    if profitable_trader_flow is not None:
        if profitable_trader_flow > 0:
            advice.append("Profitable traders are also buying.")
        elif profitable_trader_flow < 0:
            advice.append("Profitable traders are selling.")
        else:
            advice.append("No significant profitable trader movement detected.")
    # Profitable investors
    if profitable_investor_flow is not None:
        if profitable_investor_flow > 0:
            advice.append("Profitable investors are buying.")
        elif profitable_investor_flow < 0:
            advice.append("Profitable investors are selling.")
        else:
            advice.append("No significant profitable investor movement detected.")
    return " ".join(advice)

def get_comprehensive_smart_money_flow(chain: str, token_address: str) -> dict:
    """
    Fetches comprehensive smart money flow data from Nansen for multiple timeframes.
    Returns detailed analytics including flows, trader counts, and actionable insights.
    
    Args:
        chain: The blockchain name (e.g., 'ethereum', 'solana')
        token_address: The token contract address
        
    Returns:
        Dictionary with comprehensive smart money analytics
    """
    if not all([chain, token_address]):
        return {"status": "error", "result": "Missing chain or token address."}

    api_key = os.getenv("NANSEN_API_KEY")
    if not api_key:
        return {"status": "error", "result": "Nansen API key is missing."}

    # Define timeframes to fetch
    timeframes = {
        "24h": "1d",
        "7d": "7d", 
        "30d": "30d"
    }
    
    comprehensive_data = {}
    
    for label, tf in timeframes.items():
        print(f"[DEBUG] Fetching {label} smart money flow for {chain}:{token_address}")
        
        url = "https://api.nansen.ai/api/beta/tgm/flow-intelligence"
        headers = {"apiKey": api_key, "Content-Type": "application/json"}
        
        payload = {
            "parameters": {
                "chain": chain.lower(),
                "tokenAddress": token_address,
                "timeframe": tf,
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and data:
                latest_entry = data[0]
                
                # Extract key metrics
                netflow_usd = float(latest_entry.get("smartTraderFlow") or 0)
                profitable_trader_flow = float(latest_entry.get("profitableTraderFlow") or 0) if "profitableTraderFlow" in latest_entry else None
                profitable_investor_flow = float(latest_entry.get("profitableInvestorFlow") or 0) if "profitableInvestorFlow" in latest_entry else None
                
                # Try to extract trader counts (adjust field names based on actual API response)
                trader_count = latest_entry.get("traderCount", latest_entry.get("smartTraderCount", 0))
                profitable_trader_count = latest_entry.get("profitableTraderCount", 0)
                
                # Format flow values
                if abs(netflow_usd) >= 1_000_000:
                    flow_str = f"${netflow_usd / 1_000_000:,.2f}M"
                elif abs(netflow_usd) >= 1_000:
                    flow_str = f"${netflow_usd / 1_000:,.2f}K"
                else:
                    flow_str = f"${netflow_usd:,.2f}"
                
                comprehensive_data[label] = {
                    "netflow_usd": netflow_usd,
                    "flow_str": flow_str,
                    "profitable_trader_flow": profitable_trader_flow,
                    "profitable_investor_flow": profitable_investor_flow,
                    "trader_count": trader_count,
                    "profitable_trader_count": profitable_trader_count,
                    "status": "success"
                }
            else:
                comprehensive_data[label] = {
                    "status": "error",
                    "result": "No data available for this timeframe"
                }
                
        except requests.exceptions.HTTPError as e:
            print(f"[DEBUG] Nansen API HTTP error for {label}: {e.response.status_code}")
            comprehensive_data[label] = {
                "status": "error",
                "result": f"API error: {e.response.status_code}"
            }
        except Exception as e:
            print(f"[DEBUG] Error fetching {label} data: {e}")
            comprehensive_data[label] = {
                "status": "error", 
                "result": f"Network error: {str(e)}"
            }
    
    # Generate comprehensive analysis
    analysis = generate_smart_money_analysis(comprehensive_data)
    
    return {
        "status": "success",
        "data": comprehensive_data,
        "analysis": analysis,
        "summary": format_smart_money_summary(comprehensive_data)
    }

def generate_smart_money_analysis(data: dict) -> dict:
    """
    Generates actionable insights from smart money flow data.
    """
    analysis = {
        "overall_sentiment": "neutral",
        "trend": "stable",
        "confidence": "low",
        "key_insights": [],
        "recommendation": ""
    }
    
    # Analyze 24h data for immediate sentiment
    if "24h" in data and data["24h"]["status"] == "success":
        netflow_24h = data["24h"]["netflow_usd"]
        if netflow_24h > 1000000:  # $1M+ inflow
            analysis["overall_sentiment"] = "very_bullish"
            analysis["key_insights"].append("Strong smart money accumulation in last 24h")
        elif netflow_24h > 100000:  # $100K+ inflow
            analysis["overall_sentiment"] = "bullish"
            analysis["key_insights"].append("Moderate smart money buying in last 24h")
        elif netflow_24h < -1000000:  # $1M+ outflow
            analysis["overall_sentiment"] = "very_bearish"
            analysis["key_insights"].append("Heavy smart money selling in last 24h")
        elif netflow_24h < -100000:  # $100K+ outflow
            analysis["overall_sentiment"] = "bearish"
            analysis["key_insights"].append("Smart money distributing in last 24h")
    
    # Analyze trend across timeframes
    if all(label in data and data[label]["status"] == "success" for label in ["24h", "7d", "30d"]):
        flows = [data[label]["netflow_usd"] for label in ["24h", "7d", "30d"]]
        
        # Check if flows are increasing (bullish trend)
        if flows[0] > flows[1] > flows[2]:  # 24h > 7d > 30d
            analysis["trend"] = "accelerating_bullish"
            analysis["key_insights"].append("Smart money accumulation accelerating")
        elif flows[0] > 0 and flows[1] > 0:  # Both 24h and 7d positive
            analysis["trend"] = "bullish"
            analysis["key_insights"].append("Consistent smart money buying")
        elif flows[0] < flows[1] < flows[2]:  # 24h < 7d < 30d
            analysis["trend"] = "accelerating_bearish"
            analysis["key_insights"].append("Smart money selling accelerating")
        elif flows[0] < 0 and flows[1] < 0:  # Both 24h and 7d negative
            analysis["trend"] = "bearish"
            analysis["key_insights"].append("Consistent smart money selling")
    
    # Generate recommendation
    if analysis["overall_sentiment"] == "very_bullish" and analysis["trend"] in ["bullish", "accelerating_bullish"]:
        analysis["recommendation"] = "Strong buy signal from smart money"
        analysis["confidence"] = "high"
    elif analysis["overall_sentiment"] == "bullish":
        analysis["recommendation"] = "Moderate buy signal from smart money"
        analysis["confidence"] = "medium"
    elif analysis["overall_sentiment"] == "very_bearish" and analysis["trend"] in ["bearish", "accelerating_bearish"]:
        analysis["recommendation"] = "Strong sell signal from smart money"
        analysis["confidence"] = "high"
    elif analysis["overall_sentiment"] == "bearish":
        analysis["recommendation"] = "Moderate sell signal from smart money"
        analysis["confidence"] = "medium"
    else:
        analysis["recommendation"] = "Neutral - monitor for clearer signals"
        analysis["confidence"] = "low"
    
    return analysis

def format_smart_money_summary(data: dict) -> str:
    """
    Formats smart money data into a readable summary string.
    """
    summary_parts = []
    
    for timeframe in ["24h", "7d", "30d"]:
        if timeframe in data and data[timeframe]["status"] == "success":
            flow_str = data[timeframe]["flow_str"]
            trader_count = data[timeframe].get("trader_count", "N/A")
            summary_parts.append(f"{timeframe}: {flow_str} ({trader_count} traders)")
        else:
            summary_parts.append(f"{timeframe}: Data unavailable")
    
    return " | ".join(summary_parts)

def get_token_smart_money_flow(chain: str, token_address: str) -> dict:
    """
    Fetches smart money flow data from Nansen for a specific TOKEN for 24h, 7d, 30d, and trading patterns.
    Adds actionable advice based on smart money and profitable trader/investor flows.
    """
    if not all([chain, token_address]):
        return {"status": "error", "result": "Missing chain or token address."}

    timeframes = {"24h": "1d", "7d": "7d", "30d": "30d"}
    flows = {}
    for label, tf in timeframes.items():
        flows[label] = _fetch_nansen_flow_intelligence(chain, token_address, tf)
    trading_patterns = _fetch_nansen_trading_patterns(chain, token_address)

    # Build summary
    summary = []
    for label in ["24h", "7d", "30d"]:
        if flows[label]["status"] == "success":
            summary.append(f"Net smart money flow ({label}): {flows[label]['result']}")
        else:
            summary.append(f"Net smart money flow ({label}): Error: {flows[label]['result']}")
    if trading_patterns["status"] == "success":
        summary.append(f"Trading patterns: {trading_patterns['result']}")
    else:
        summary.append(f"Trading patterns: Error: {trading_patterns['result']}")

    # Add actionable advice based on 24h flows (can be changed to 7d/30d or aggregate)
    netflow_usd = flows["24h"].get("netflow_usd")
    profitable_trader_flow = flows["24h"].get("profitable_trader_flow")
    profitable_investor_flow = flows["24h"].get("profitable_investor_flow")
    advice = get_smart_money_advice(netflow_usd, profitable_trader_flow, profitable_investor_flow)
    summary.append(f"Advice: {advice}")

    return {"status": "success", "result": "\n".join(summary), "flows": flows, "trading_patterns": trading_patterns, "advice": advice}

def get_native_asset_smart_money_flow(chain: str) -> dict:
    """
    Fetches smart money flow data from Nansen for a NATIVE asset (e.g., SOL, ETH).

    Args:
        chain: The blockchain name (e.g., 'solana', 'ethereum').

    Returns:
        A dictionary with a summary of smart money inflows/outflows for the chain.
    """
    if not chain:
        return {"status": "error", "result": "Missing chain name."}
        
    native_asset_addresses = {
        "solana": "So11111111111111111111111111111111111111112",
        "ethereum": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",
    }
    token_address = native_asset_addresses.get(chain.lower())
    if not token_address:
        return {"status": "error", "result": f"Smart money flow not supported for native asset on '{chain}'."}

    return _fetch_nansen_flow_intelligence(chain, token_address)

@tool
def get_smart_money_flow(symbol: str) -> dict:
    """
    Get smart money flow data for a specific cryptocurrency using Nansen API.
    
    Args:
        symbol: The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol')
        
    Returns:
        Dictionary containing smart money flow analysis
    """
    print(f"[DEBUG] Getting smart money flow for {symbol.upper()}")
    
    # Get token address and chain from CoinGecko
    chain, token_address = get_token_address_from_coingecko(symbol)
    
    if not chain:
        return {
            "status": "error",
            "message": f"Could not find {symbol.upper()} on CoinGecko or determine its chain.",
            "data": None
        }
    
    # Check if it's a native asset
    if not token_address:
        # Native asset (like SOL, ETH)
        print(f"[DEBUG] {symbol.upper()} is a native asset on {chain}")
        result = get_native_asset_smart_money_flow(chain)
        return {
            "status": result.get("status"),
            "symbol": symbol.upper(),
            "chain": chain,
            "message": result.get("result"),
            "data": result
        }
    else:
        # Token with contract address
        print(f"[DEBUG] {symbol.upper()} is a token on {chain} with address {token_address}")
        result = get_comprehensive_smart_money_flow(chain, token_address)
        return {
            "status": result.get("status"),
            "symbol": symbol.upper(),
            "chain": chain,
            "message": result.get("summary"),
            "data": result
        }

@tool
def get_onchain_analytics(symbol: str) -> dict:
    """
    Fetch comprehensive on-chain analytics and smart money data from Nansen.
    
    Args:
        symbol: The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol')
        
    Returns:
        Dictionary containing on-chain analytics and smart money insights
    """
    return get_smart_money_flow(symbol)

@tool
def get_whale_movements(symbol: str) -> dict:
    """
    Track whale movements for a specific cryptocurrency.
    
    Args:
        symbol: The cryptocurrency symbol
        
    Returns:
        Whale movement data
    """
    return get_smart_money_flow(symbol) 