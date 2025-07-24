"""
CoinGecko Tool Module
Provides functions for searching coin IDs, fetching coin details, and historical performance from the CoinGecko API, with retry logic and prioritization for Solana/Ethereum assets.
"""
import os
import requests
import time
import random
import re
from strands import tool
from dotenv import load_dotenv

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

@tool
def search_coin_id(query: str) -> str:
    """
    Purpose:
        Search CoinGecko for a coin ID, prioritizing exact symbol/name matches for top-level coins, then Solana/Ethereum chain coins, then exact name, then symbol, then fallback. Improved to handle ambiguous names like 'pump' by matching CoinGecko ID and common variants (e.g., 'pump-fun').
    Args:
        query (str): Coin name or symbol to search for.
    Returns:
        str: CoinGecko coin ID if found, otherwise None.
    Exceptions:
        Handles network, data parsing, system, and import errors. Returns None on error.
    """
    # Validate input parameter
    if not query or not query.strip():
        print("[DEBUG] Empty or invalid query provided to search_coin_id")
        return None
    
    # Validate query format (should be alphanumeric with spaces)
    if not re.match(r'^[a-zA-Z0-9\s\.\-]+$', query.strip()):
        print(f"[DEBUG] Invalid query format: {query}")
        return None
    
    api_key = os.getenv("COINGECKO_API_KEY")
    url = "https://pro-api.coingecko.com/api/v3/search" if api_key else "https://api.coingecko.com/api/v3/search"
    headers = {"x-cg-pro-api-key": api_key} if api_key else {}
    def make_request():
        response = requests.get(url, params={"query": query}, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    
    try:
        data = retry_api_call(make_request)
        if not data:
            print(f"[DEBUG] Failed to get data from CoinGecko after retries for '{query}'")
            return None
        
        coins = data.get("coins", [])
        if not coins:
            return None
        query_lower = query.lower()
        # 0. Prefer exact symbol or name match among all coins (case-insensitive)
        for coin in coins:
            if coin.get("symbol", "").lower() == query_lower or coin.get("name", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}' (exact symbol/name match): {coin.get('id')}")
                return coin.get("id")
        # 1. Exact name match (prioritize solana/eth chains)
        sol_eth_coins = []
        for coin in coins:
            platforms = coin.get("platforms", {})
            asset_platform_id = coin.get("asset_platform_id", "")
            if (
                ("solana" in platforms and platforms["solana"]) or
                ("ethereum" in platforms and platforms["ethereum"]) or
                asset_platform_id in ["solana", "ethereum"]
            ):
                sol_eth_coins.append(coin)
        # Try exact CoinGecko ID match among sol/eth coins
        for coin in sol_eth_coins:
            if coin.get("id", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth id match): {coin.get('id')}")
                return coin.get("id")
        # Try common variant (e.g., 'pump' -> 'pump-fun')
        for coin in sol_eth_coins:
            if query_lower in coin.get("id", "").lower() or query_lower.replace(".", "-") in coin.get("id", "").lower():
                print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth id variant match): {coin.get('id')}")
                return coin.get("id")
        # Try exact name match among sol/eth coins
        for coin in sol_eth_coins:
            if coin.get("name", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth name match): {coin.get('id')}")
                return coin.get("id")
        # Try exact symbol match among sol/eth coins
        for coin in sol_eth_coins:
            if coin.get("symbol", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth symbol match): {coin.get('id')}")
                return coin.get("id")
        # Fallback: first sol/eth coin
        if sol_eth_coins:
            print(f"[DEBUG] CoinGecko ID for '{query}' (sol/eth fallback): {sol_eth_coins[0].get('id')}")
            return sol_eth_coins[0].get("id")
        # 2. Exact CoinGecko ID match (all coins)
        for coin in coins:
            if coin.get("id", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}': {coin.get('id')}")
                return coin.get("id")
        # 3. Common variant (all coins)
        for coin in coins:
            if query_lower in coin.get("id", "").lower() or query_lower.replace(".", "-") in coin.get("id", "").lower():
                print(f"[DEBUG] CoinGecko ID for '{query}' (id variant match): {coin.get('id')}")
                return coin.get("id")
        # 4. Exact name match (all coins)
        for coin in coins:
            if coin.get("name", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}': {coin.get('id')}")
                return coin.get("id")
        # 5. Exact symbol match (all coins)
        for coin in coins:
            if coin.get("symbol", "").lower() == query_lower:
                print(f"[DEBUG] CoinGecko ID for '{query}': {coin.get('id')}")
                return coin.get("id")
        # 6. Fallback to first result
        print(f"[DEBUG] CoinGecko ID for '{query}': {coins[0].get('id')}")
        return coins[0].get("id")
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] Network error searching CoinGecko ID for '{query}': {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"[DEBUG] Data parsing error searching CoinGecko ID for '{query}': {e}")
        return None
    except (OSError, IOError) as e:
        print(f"[DEBUG] System error searching CoinGecko ID for '{query}': {e}")
        return None
    except ImportError as e:
        print(f"[DEBUG] Import error searching CoinGecko ID for '{query}': {e}")
        return None
    except Exception as e:
        print(f"[DEBUG] Unexpected error searching CoinGecko ID for '{query}': {e}")
        print(f"[DEBUG] Error type: {type(e).__name__}")
        return None

@tool
def get_coin_details(coin_id: str) -> dict:
    """
    Purpose:
        Fetch detailed cryptocurrency data from CoinGecko, including price, market cap, and performance.
    Args:
        coin_id (str): The CoinGecko coin ID.
    Returns:
        dict: Status, coin details, and summary or error message.
    Exceptions:
        Handles HTTP, timeout, connection, and request exceptions. Returns error dict on failure.
    """
    # Validate input parameter
    if not coin_id or not coin_id.strip():
        return {"status": "error", "result": "Coin ID is required and cannot be empty."}
    
    # Validate coin_id format (should be alphanumeric with hyphens)
    if not re.match(r'^[a-zA-Z0-9-]+$', coin_id.strip()):
        return {"status": "error", "result": f"Invalid coin ID format: {coin_id}"}
    api_key = os.getenv("COINGECKO_API_KEY")
    headers = {"x-cg-pro-api-key": api_key} if api_key else {}
    base_url = "https://pro-api.coingecko.com/api/v3" if api_key else "https://api.coingecko.com/api/v3"
    url = f"{base_url}/coins/{coin_id}"
    def make_request():
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.json()
    
    try:
        data = retry_api_call(make_request)
        if not data:
            print(f"[DEBUG] Failed to get coin details from CoinGecko after retries for '{coin_id}'")
            return {"status": "error", "result": "Failed to fetch coin data after retries"}
            
        print(f"[DEBUG] Raw CoinGecko data for '{coin_id}': {data}")
        market_data = data.get("market_data", {})
        current_price = market_data.get("current_price", {}).get("usd", None)
        if isinstance(current_price, (int, float)):
            current_price_fmt = f"{current_price:.6f}"
        else:
            current_price_fmt = "N/A"
        market_cap = market_data.get("market_cap", {}).get("usd", None)
        if isinstance(market_cap, (int, float)):
            market_cap_fmt = f"{market_cap:,.0f}"
        else:
            market_cap_fmt = "N/A"
        total_volume = market_data.get("total_volume", {}).get("usd", "N/A")
        high_24h = market_data.get("high_24h", {}).get("usd", "N/A")
        low_24h = market_data.get("low_24h", {}).get("usd", "N/A")
        price_change_1h = market_data.get("price_change_percentage_1h_in_currency", {}).get("usd", "N/A")
        price_change_24h = market_data.get("price_change_percentage_24h_in_currency", {}).get("usd", "N/A")
        price_change_7d = market_data.get("price_change_percentage_7d_in_currency", {}).get("usd", "N/A")
        price_change_30d = market_data.get("price_change_percentage_30d_in_currency", {}).get("usd", "N/A")
        asset_platform_id = data.get("asset_platform_id")
        is_native = not asset_platform_id and data.get("id") in ["solana", "ethereum", "binancecoin", "avalanche-2"]
        found_chain = data.get("id") if is_native else None
        contract_address = None
        if not is_native:
            supported_chains = ["solana", "ethereum", "arbitrum", "polygon", "avalanche", "base", "bnb"]
            platforms = data.get("platforms", {})
            for chain in supported_chains:
                if platforms.get(chain):
                    found_chain = chain
                    contract_address = platforms[chain]
                    break
        def format_percentage(value):
            if value == "N/A" or value is None:
                return "N/A"
            return f"{value:+.2f}%"
        performance_summary = []
        if price_change_1h != "N/A":
            performance_summary.append(f"1h: {format_percentage(price_change_1h)}")
        if price_change_24h != "N/A":
            performance_summary.append(f"24h: {format_percentage(price_change_24h)}")
        if price_change_7d != "N/A":
            performance_summary.append(f"7d: {format_percentage(price_change_7d)}")
        if price_change_30d != "N/A":
            performance_summary.append(f"30d: {format_percentage(price_change_30d)}")
        performance_text = " | ".join(performance_summary) if performance_summary else "No performance data available"
        result_summary = (
            f"Here's the tea on {data.get('name', 'this coin')}. "
            f"Current price: ${current_price_fmt}. "
            f"Market cap: ${market_cap_fmt}. "
            f"Performance: {performance_text}"
        )
        return {
            "status": "success",
            "coin_id": coin_id,
            "is_native_asset": is_native,
            "chain": found_chain,
            "contract_address": contract_address,
            "current_price": current_price_fmt,
            "market_cap": market_cap_fmt,
            "total_volume": total_volume,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "price_change_1h": price_change_1h,
            "price_change_24h": price_change_24h,
            "price_change_7d": price_change_7d,
            "price_change_30d": price_change_30d,
            "result": result_summary,
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        print(f"[DEBUG] CoinGecko API HTTP error: {status_code}")
        
        if status_code == 429:
            return {"status": "error", "result": "CoinGecko rate limit exceeded. Please try again later."}
        elif status_code == 404:
            return {"status": "error", "result": f"Coin '{coin_id}' not found on CoinGecko"}
        elif status_code == 403:
            return {"status": "error", "result": "CoinGecko API access denied. Check your API key."}
        elif status_code >= 500:
            return {"status": "error", "result": "CoinGecko server error. Please try again later."}
        else:
            return {"status": "error", "result": f"CoinGecko API error: {status_code}"}
    except requests.exceptions.Timeout as e:
        print(f"[DEBUG] CoinGecko API timeout: {e}")
        return {"status": "error", "result": "CoinGecko API request timed out. Please try again."}
    except requests.exceptions.ConnectionError as e:
        print(f"[DEBUG] CoinGecko API connection error: {e}")
        return {"status": "error", "result": "Cannot connect to CoinGecko. Check your internet connection."}
    except requests.exceptions.RequestException as e:
        print(f"[DEBUG] CoinGecko API request error: {e}")
        return {"status": "error", "result": f"CoinGecko API request failed: {str(e)}"}

@tool
def get_historical_performance(coin_id: str, timeframe: str = "all") -> dict:
    """
    Purpose:
        Fetch historical performance data for a coin for a specific timeframe or all timeframes.
    Args:
        coin_id (str): The CoinGecko coin ID.
        timeframe (str): Timeframe for performance data ('1h', '24h', '7d', '30d', or 'all').
    Returns:
        dict: Status, performance data, and summary or error message.
    Exceptions:
        Returns error dict if coin_id is missing, invalid, or if timeframe is invalid.
    """
    if not coin_id:
        return {"status": "error", "result": "Missing coin_id parameter."}
    coin_data = get_coin_details(coin_id)
    if coin_data["status"] != "success":
        return coin_data
    performance_data = {
        "1h": coin_data.get("price_change_1h", "N/A"),
        "24h": coin_data.get("price_change_24h", "N/A"),
        "7d": coin_data.get("price_change_7d", "N/A"),
        "30d": coin_data.get("price_change_30d", "N/A"),
    }
    def format_percentage(value):
        if value == "N/A" or value is None:
            return "N/A"
        return f"{value:+.2f}%"
    if timeframe == "all":
        summary = []
        for tf, value in performance_data.items():
            summary.append(f"{tf}: {format_percentage(value)}")
        result_summary = f"Performance breakdown for {coin_data.get('coin_id', 'this coin')}: {' | '.join(summary)}"
        return {
            "status": "success",
            "coin_id": coin_id,
            "performance_data": performance_data,
            "result": result_summary,
        }
    elif timeframe in performance_data:
        value = performance_data[timeframe]
        result_summary = f"Performance for {coin_data.get('coin_id', 'this coin')} over {timeframe}: {format_percentage(value)}"
        return {
            "status": "success",
            "coin_id": coin_id,
            "timeframe": timeframe,
            "performance": value,
            "result": result_summary,
        }
    else:
        return {
            "status": "error",
            "result": f"Invalid timeframe '{timeframe}'. Use '1h', '24h', '7d', '30d', or 'all'.",
        } 