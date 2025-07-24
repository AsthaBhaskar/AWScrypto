"""
Nansen Tool Module
Provides functions for fetching and analyzing smart money flow, on-chain analytics, and whale movements using the Nansen API, with integration to CoinGecko for token details.
"""
import os
import requests
import json
import time
import random
from strands import tool
from dotenv import load_dotenv
from coingecko_tool import search_coin_id, get_coin_details

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

def get_token_address_from_coingecko(symbol: str) -> tuple:
    """
    Purpose:
    Get the token contract address and chain from CoinGecko for a given symbol.
    Args:
        symbol (str): The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol').
    Returns:
        tuple: (chain, token_address) or (None, None) if not found or on error.
    Exceptions:
        Handles network, data parsing, and generic exceptions. Returns (None, None) on error.
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
                
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Network error getting token address from CoinGecko: {e}")
        return None, None
    except (ValueError, KeyError) as e:
        print(f"[DEBUG] Data parsing error getting token address from CoinGecko: {e}")
        return None, None
    except Exception as e:
        print(f"[DEBUG] Unexpected error getting token address from CoinGecko: {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        return None, None

# Nansen Tools
# ------------------------------------------------------------------------------
def _fetch_nansen_flow_intelligence(chain: str, token_address: str, timeframe: str = "1d") -> dict:
    """
    Purpose:
        Helper to fetch and process smart money flow from Nansen using flow-intelligence for a given timeframe.
    Args:
        chain (str): Blockchain name (e.g., 'ethereum', 'solana').
        token_address (str): Token contract address.
        timeframe (str): Timeframe for analysis (default: '1d').
    Returns:
        dict: Smart money flow data or error message.
    Exceptions:
        Handles HTTP, timeout, connection, request, data parsing, system, import, and generic exceptions. Returns error dict on failure.
    """
    # Validate required parameters
    if not chain or not chain.strip():
        return {"status": "error", "result": "Chain parameter is required and cannot be empty."}
    
    if not token_address or not token_address.strip():
        return {"status": "error", "result": "Token address parameter is required and cannot be empty."}
    
    # Validate chain format
    valid_chains = ["ethereum", "solana", "polygon", "arbitrum", "avalanche", "base", "bnb"]
    if chain.lower() not in valid_chains:
        return {"status": "error", "result": f"Unsupported chain '{chain}'. Supported chains: {', '.join(valid_chains)}"}
    
    # Validate token address format (basic check)
    if chain.lower() == "solana":
    # Solana addresses are base58, typically 32-44 chars, allow any non-empty string
        if not (isinstance(token_address, str) and 32 <= len(token_address) <= 44):
            return {"status": "error", "result": f"Invalid Solana token address format: {token_address}"}
    else:
    # EVM chains: must start with 0x and be 42 chars
        if not (isinstance(token_address, str) and token_address.startswith("0x") and len(token_address) == 42):
            return {"status": "error", "result": f"Invalid token address format: {token_address}"}
    
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

    def make_nansen_request():
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"[DEBUG] Nansen API status code: {response.status_code}")
        print(f"[DEBUG] Nansen API raw response: {response.text}")
        response.raise_for_status()
        return response.json()
    
    try:
        data = retry_api_call(make_nansen_request)
        if not data:
            print(f"[DEBUG] Failed to get Nansen data after retries for {chain}:{token_address}")
            return {"status": "error", "result": "Failed to fetch Nansen data after retries"}

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
        status_code = e.response.status_code
        print(f"[DEBUG] Nansen API HTTP error: {status_code} - {e.response.text}")
        
        if status_code == 404:
            return {"status": "error", "result": "Unsupported chain or token for Nansen smart money flow."}
        elif status_code == 401:
            return {"status": "error", "result": "Nansen API unauthorized - check your API key"}
        elif status_code == 403:
            return {"status": "error", "result": "Nansen API access forbidden - check API permissions"}
        elif status_code == 429:
            return {"status": "error", "result": "Nansen API rate limit exceeded - try again later"}
        elif status_code >= 500:
            return {"status": "error", "result": "Nansen server error - try again later"}
        else:
            return {"status": "error", "result": f"Nansen API error: {status_code}"}
    except requests.exceptions.Timeout as e:
        print(f"[DEBUG] Nansen API timeout: {e}")
        return {"status": "error", "result": "Nansen API request timed out - try again"}
    except requests.exceptions.ConnectionError as e:
        print(f"[DEBUG] Nansen API connection error: {e}")
        return {"status": "error", "result": "Cannot connect to Nansen API - check internet connection"}
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Nansen API request error: {e}")
        return {"status": "error", "result": f"Nansen API request failed: {str(e)}"}

def _fetch_nansen_trading_patterns(chain: str, token_address: str) -> dict:
    """
    Purpose:
        Fetch trading patterns for a token from Nansen (example endpoint, adjust as needed).
    Args:
        chain (str): Blockchain name.
        token_address (str): Token contract address.
    Returns:
        dict: Trading patterns data or error message.
    Exceptions:
        Handles HTTP, request, data parsing, system, import, and generic exceptions. Returns error dict on failure.
    """
    # Validate required parameters
    if not chain or not chain.strip():
        return {"status": "error", "result": "Chain parameter is required and cannot be empty."}
    
    if not token_address or not token_address.strip():
        return {"status": "error", "result": "Token address parameter is required and cannot be empty."}
    
    # Validate chain format
    valid_chains = ["ethereum", "solana", "polygon", "arbitrum", "avalanche", "base", "bnb"]
    if chain.lower() not in valid_chains:
        return {"status": "error", "result": f"Unsupported chain '{chain}'. Supported chains: {', '.join(valid_chains)}"}
    
    # Validate token address format (Solana: base58, 32-44 chars; EVM: 0x, 42 chars)
    if chain.lower() == "solana":
        if not (isinstance(token_address, str) and 32 <= len(token_address) <= 44):
            return {"status": "error", "result": f"Invalid Solana token address format: {token_address}"}
    else:
        if not (isinstance(token_address, str) and token_address.startswith("0x") and len(token_address) == 42):
            return {"status": "error", "result": f"Invalid token address format: {token_address}"}
    
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
    def make_trading_patterns_request():
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return response.json()
    
    try:
        data = retry_api_call(make_trading_patterns_request)
        if not data:
            print(f"[DEBUG] Failed to get Nansen trading patterns after retries for {chain}:{token_address}")
            return {"status": "error", "result": "Failed to fetch trading patterns after retries"}
            
        return {"status": "success", "result": data}
    except requests.exceptions.HTTPError as e:
        print(f"[DEBUG] Nansen trading patterns HTTP error: {e.response.status_code}")
        return {"status": "error", "result": f"API error: {e.response.status_code}"}
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Nansen trading patterns network error: {e}")
        return {"status": "error", "result": f"Network error: {str(e)}"}
    except (ValueError, KeyError) as e:
        print(f"[DEBUG] Nansen trading patterns data error: {e}")
        return {"status": "error", "result": f"Data parsing error: {str(e)}"}
    except (OSError, IOError) as e:
        print(f"[DEBUG] Nansen trading patterns system error: {e}")
        return {"status": "error", "result": f"System error: {str(e)}"}
    except ImportError as e:
        print(f"[DEBUG] Nansen trading patterns import error: {e}")
        return {"status": "error", "result": f"Import error: {str(e)}"}
    except Exception as e:
        print(f"[DEBUG] Nansen trading patterns unexpected error: {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        return {"status": "error", "result": f"Unexpected error: {str(e)}"}

def get_smart_money_advice(netflow_usd, profitable_trader_flow, profitable_investor_flow):
    """
    Purpose:
        Generate actionable advice based on smart money, profitable trader, and investor flows.
    Args:
        netflow_usd (float): Net smart money flow in USD.
        profitable_trader_flow (float): Net flow from profitable traders.
        profitable_investor_flow (float): Net flow from profitable investors.
    Returns:
        str: Actionable advice string.
    Exceptions:
        None
    """
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
    Purpose:
        Fetch comprehensive smart money flow data from Nansen for multiple timeframes and provide analytics.
    Args:
        chain (str): Blockchain name (e.g., 'ethereum', 'solana').
        token_address (str): Token contract address.
    Returns:
        dict: Comprehensive smart money analytics, summary, and analysis.
    Exceptions:
        Handles HTTP, request, data parsing, system, import, and generic exceptions. Returns error dict on failure.
    """
    # Validate required parameters
    if not chain or not chain.strip():
        return {"status": "error", "result": "Chain parameter is required and cannot be empty."}
    
    if not token_address or not token_address.strip():
        return {"status": "error", "result": "Token address parameter is required and cannot be empty."}
    
    # Validate chain format
    valid_chains = ["ethereum", "solana", "polygon", "arbitrum", "avalanche", "base", "bnb"]
    if chain.lower() not in valid_chains:
        return {"status": "error", "result": f"Unsupported chain '{chain}'. Supported chains: {', '.join(valid_chains)}"}
    
    # Validate token address format (basic check)
    if not token_address.startswith("0x") and not token_address.startswith("1") and not token_address.startswith("2"):
        return {"status": "error", "result": f"Invalid token address format: {token_address}"}

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

        def make_comprehensive_request():
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            return response.json()
        
        try:
            data = retry_api_call(make_comprehensive_request)
            if not data:
                print(f"[DEBUG] Failed to get comprehensive Nansen data after retries for {label}")
                comprehensive_data[label] = {
                    "status": "error",
                    "result": "Failed to fetch data after retries"
                }
                continue
            
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
        except requests.exceptions.RequestException as e:
            print(f"[DEBUG] Nansen API network error for {label}: {e}")
            comprehensive_data[label] = {
                "status": "error", 
                "result": f"Network error: {str(e)}"
            }
        except (ValueError, KeyError) as e:
            print(f"[DEBUG] Nansen API data parsing error for {label}: {e}")
            comprehensive_data[label] = {
                "status": "error", 
                "result": f"Data parsing error: {str(e)}"
            }
        except (OSError, IOError) as e:
            print(f"[DEBUG] Nansen API system error for {label}: {e}")
            comprehensive_data[label] = {
                "status": "error", 
                "result": f"System error: {str(e)}"
            }
        except ImportError as e:
            print(f"[DEBUG] Nansen API import error for {label}: {e}")
            comprehensive_data[label] = {
                "status": "error", 
                "result": f"Import error: {str(e)}"
            }
        except Exception as e:
            print(f"[DEBUG] Nansen API unexpected error for {label}: {e}")
            print(f"[DEBUG] Error type: {type(e).__name__}")
            comprehensive_data[label] = {
                "status": "error", 
                "result": f"Unexpected error: {str(e)}"
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
    Purpose:
        Generate actionable insights and recommendations from smart money flow data.
    Args:
        data (dict): Smart money flow data for multiple timeframes.
    Returns:
        dict: Analysis including sentiment, trend, confidence, key insights, and recommendation.
    Exceptions:
        None
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
    Purpose:
        Format smart money data into a readable summary string for reporting.
    Args:
        data (dict): Smart money flow data for multiple timeframes.
    Returns:
        str: Summary string for reporting.
    Exceptions:
        None
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
    Purpose:
        Fetch smart money flow data from Nansen for a specific token for 24h, 7d, 30d, and trading patterns. Adds actionable advice.
    Args:
        chain (str): Blockchain name.
        token_address (str): Token contract address.
    Returns:
        dict: Smart money flow data, trading patterns, and advice.
    Exceptions:
        Returns error dict if parameters are missing or invalid, or if API call fails.
    """
    # Validate required parameters
    if not chain or not chain.strip():
        return {"status": "error", "result": "Chain parameter is required and cannot be empty."}
    
    if not token_address or not token_address.strip():
        return {"status": "error", "result": "Token address parameter is required and cannot be empty."}
    
    # Validate chain format
    valid_chains = ["ethereum", "solana", "polygon", "arbitrum", "avalanche", "base", "bnb"]
    if chain.lower() not in valid_chains:
        return {"status": "error", "result": f"Unsupported chain '{chain}'. Supported chains: {', '.join(valid_chains)}"}
    
    # Validate token address format (Solana: base58, 32-44 chars; EVM: 0x, 42 chars)
    if chain.lower() == "solana":
        if not (isinstance(token_address, str) and 32 <= len(token_address) <= 44):
            return {"status": "error", "result": f"Invalid Solana token address format: {token_address}"}
    else:
        if not (isinstance(token_address, str) and token_address.startswith("0x") and len(token_address) == 42):
            return {"status": "error", "result": f"Invalid token address format: {token_address}"}

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
    Purpose:
        Fetch smart money flow data from Nansen for a native asset (e.g., SOL, ETH).
    Args:
        chain (str): Blockchain name (e.g., 'solana', 'ethereum').
    Returns:
        dict: Summary of smart money inflows/outflows for the chain.
    Exceptions:
        Returns error dict if parameters are missing or invalid, or if API call fails.
    """
    # Validate required parameters
    if not chain or not chain.strip():
        return {"status": "error", "result": "Chain parameter is required and cannot be empty."}
    
    # Validate chain format
    valid_chains = ["ethereum", "solana", "polygon", "arbitrum", "avalanche", "base", "bnb"]
    if chain.lower() not in valid_chains:
        return {"status": "error", "result": f"Unsupported chain '{chain}'. Supported chains: {', '.join(valid_chains)}"}
        
    # Native asset addresses for smart money flow tracking
    # These are the wrapped versions of native assets that Nansen tracks
    native_asset_addresses = {
        "solana": "So11111111111111111111111111111111111111112",  # Wrapped SOL
        "ethereum": "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # Wrapped ETH
        "polygon": "0x0d500b1d8e8ef31e21c99d1db9a6444d3adf1270",  # Wrapped MATIC
        "arbitrum": "0x82af49447d8a07e3bd95bd0d56f35241523fbab1",  # Wrapped ETH on Arbitrum
        "avalanche": "0xb31f66aa3c1e785363f0875a1b74e27b85fd66c7",  # Wrapped AVAX
        "base": "0x4200000000000000000000000000000000000006",  # Wrapped ETH on Base
        "bnb": "0xbb4cdb9cbd36b01bd1cbaef2af88c6b9364c9a4f",  # Wrapped BNB
    }
    
    token_address = native_asset_addresses.get(chain.lower())
    if not token_address:
        return get_alternative_native_asset_analytics(chain)

    # Try to get smart money flow data
    result = _fetch_nansen_flow_intelligence(chain, token_address)
    
    # If smart money flow fails, provide alternative native asset data
    if result.get("status") == "error":
        return get_alternative_native_asset_analytics(chain)
    
    return result

def get_alternative_native_asset_analytics(chain: str) -> dict:
    """
    Purpose:
        Provide alternative analytics for native assets when smart money flow is not available.
    Args:
        chain (str): Blockchain name.
    Returns:
        dict: Alternative analytics and suggestions.
    Exceptions:
        None
    """
    chain_analytics = {
        "ethereum": {
            "description": "Ethereum native asset (ETH) - focus on gas fees, DeFi TVL, and network activity",
            "key_metrics": ["Gas fees", "DeFi TVL", "Network transactions", "Staking yield"],
            "suggestions": ["Monitor gas fee trends", "Check DeFi protocol usage", "Track staking statistics"]
        },
        "solana": {
            "description": "Solana native asset (SOL) - focus on transaction speed, DeFi activity, and staking",
            "key_metrics": ["TPS (transactions per second)", "DeFi TVL", "Staking yield", "Network fees"],
            "suggestions": ["Monitor network performance", "Check DeFi protocol growth", "Track staking participation"]
        },
        "polygon": {
            "description": "Polygon native asset (MATIC) - focus on scaling solutions and DeFi adoption",
            "key_metrics": ["Bridge volume", "DeFi TVL", "Transaction count", "Staking yield"],
            "suggestions": ["Monitor bridge activity", "Check DeFi protocol usage", "Track staking rewards"]
        },
        "arbitrum": {
            "description": "Arbitrum native asset (ARB) - focus on L2 scaling and DeFi growth",
            "key_metrics": ["Bridge volume", "DeFi TVL", "Transaction count", "Gas savings"],
            "suggestions": ["Monitor bridge activity", "Check DeFi protocol growth", "Track gas savings vs L1"]
        },
        "avalanche": {
            "description": "Avalanche native asset (AVAX) - focus on subnet activity and DeFi ecosystem",
            "key_metrics": ["Subnet activity", "DeFi TVL", "Transaction count", "Staking yield"],
            "suggestions": ["Monitor subnet growth", "Check DeFi protocol usage", "Track staking participation"]
        },
        "base": {
            "description": "Base native asset - focus on Coinbase ecosystem and DeFi adoption",
            "key_metrics": ["Bridge volume", "DeFi TVL", "Transaction count", "Coinbase integration"],
            "suggestions": ["Monitor bridge activity", "Check DeFi protocol growth", "Track Coinbase ecosystem integration"]
        },
        "bnb": {
            "description": "BNB Chain native asset (BNB) - focus on BSC ecosystem and DeFi activity",
            "key_metrics": ["BSC transaction count", "DeFi TVL", "Staking yield", "Binance integration"],
            "suggestions": ["Monitor BSC activity", "Check DeFi protocol usage", "Track Binance ecosystem integration"]
        }
    }
    
    analytics = chain_analytics.get(chain.lower(), {
        "description": f"{chain.capitalize()} native asset - focus on network fundamentals and ecosystem growth",
        "key_metrics": ["Network activity", "Transaction volume", "Market cap", "Price action"],
        "suggestions": ["Monitor network fundamentals", "Check ecosystem growth", "Track price and volume patterns"]
    })
    
    return {
        "status": "success",
        "result": f"Smart money flow not available for {chain} native asset. {analytics['description']}",
        "fallback": True,
        "alternative_suggestions": analytics["suggestions"],
        "key_metrics": analytics["key_metrics"],
        "analytics_type": "alternative_native_asset"
    }

@tool
def get_smart_money_flow(symbol: str) -> dict:
    """
    Purpose:
    Get smart money flow data for a specific cryptocurrency using Nansen API.
    Args:
        symbol (str): The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol').
    Returns:
        dict: Smart money flow analysis and summary.
    Exceptions:
        Returns error dict if chain or token cannot be determined or if API call fails.
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
    Purpose:
    Fetch comprehensive on-chain analytics and smart money data from Nansen.
    Args:
        symbol (str): The cryptocurrency symbol (e.g., 'btc', 'eth', 'sol').
    Returns:
        dict: On-chain analytics and smart money insights.
    Exceptions:
        Returns error dict if API call fails.
    """
    return get_smart_money_flow(symbol)

@tool
def get_whale_movements(symbol: str) -> dict:
    """
    Purpose:
        Track whale movements for a specific cryptocurrency using Nansen API.
    Args:
        symbol (str): The cryptocurrency symbol.
    Returns:
        dict: Whale movement data.
    Exceptions:
        Returns error dict if API call fails.
    """
    return get_smart_money_flow(symbol) 